import time
import json
import logging

from typing import List, Optional, Set, Dict

from shared.core.base_ws import ExchangeWebSocket

logger = logging.getLogger(__name__)

class BinanceWebSocket(ExchangeWebSocket):
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
    ):
        super().__init__(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
        )

    def _get_topic_name(
        self, symbol: str, stream_type: str, market_type: str = "spot"
    ) -> str:
        return f"binance:{market_type}:{symbol}:{stream_type}"

    def _get_base_url(self, market_type="spot"):
        urls = {
            "spot": "wss://stream.binance.com:9443/ws",
            "perp": "wss://fstream.binance.com/ws",
            "coin-m": "wss://dstream.binance.com/ws",
            "user": "wss://stream.binance.com:9443/ws",
        }
        return urls.get(market_type, urls["spot"])

    async def _handle_message(self, connection_id: str, message: str):
        """處理接收到的 WebSocket 訊息"""
        try:
            data = json.loads(message)
            market_type = connection_id.split(":")[0]

            # 處理心跳訊息
            if "ping" in data:
                await self.ws_manager.send_message(
                    connection_id, json.dumps({"pong": data["ping"]})
                )
                return

            # 處理訂閱/取消訂閱確認訊息
            if "result" in data and "id" in data:
                logger.debug(f"Received subscription confirmation: {data}")
                return

            # 處理市場數據
            topic, mapped_data = self._map_format(market_type, data)

            # 發送到 Redis
            await self.redis_producer.publish(topic, json.dumps(mapped_data))

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")

    async def _handle_reconnection(self, connection_id: str):
        """處理重新連接"""
        market_type = connection_id.split(":")[0]
        streams = list(self.subscriptions.get(market_type, set()))

        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": int(time.time() * 1000),
        }

        try:
            await self.ws_manager.send_message(
                connection_id, json.dumps(subscribe_message)
            )

        except Exception as e:
            logger.error(f"Failed to restore subscriptions: {str(e)}")

    async def subscribe(
        self,
        symbols: List[str],
        stream_type: str,
        market_type: str = "spot",
        request_id: Optional[int] = None,
    ) -> bool:
        """訂閱指定市場的串流"""
        if request_id is None:
            request_id = int(time.time() * 1000)
        streams = [f"{symbol}@{stream_type}" for symbol in symbols]

        # 建立連接 ID
        connection_id = f"{market_type}:main"

        # 如果尚未建立連接
        if connection_id not in self.ws_manager.connections:
            try:
                url = f"{self._get_base_url(market_type)}"
                await self.ws_manager.add_connection(url, connection_id)
            except Exception as e:
                logger.error(f"Failed to establish connection: {str(e)}")
                return False

        # 發送訂閱訊息
        subscribe_message = {"method": "SUBSCRIBE", "params": streams, "id": request_id}

        try:
            logger.debug(f"Subscribing to {streams}")
            await self.ws_manager.send_message(
                connection_id, json.dumps(subscribe_message)
            )
            logger.debug(f"Subscribed to {streams}")
            # 更新訂閱記錄
            logger.debug(f" Adding subscription with market_type: {market_type}")
            self.add_subscription(streams, market_type)
            logger.debug(f"Subscriptions: {dict(self.subscriptions)}")
            return True

        except Exception as e:
            logger.error(f"Subscription failed: {str(e)}")
            return False

    async def unsubscribe(
        self,
        symbols: List[str],
        stream_type: str,
        market_type: str = "spot",
        request_id: Optional[int] = None,
    ):
        """取消訂閱一個或多個串流"""
        if request_id is None:
            request_id = int(time.time() * 1000)

        streams = [f"{symbol}@{stream_type}" for symbol in symbols]
        connection_id = f"{market_type}:main"

        # 先移除訂閱記錄
        self.remove_subscription(streams, market_type)
        
        # 如果沒有人訂閱了，就取消訂閱
        removing_streams = self.get_zero_sub_streams(market_type)
        logger.debug(f"Removing streams: {removing_streams}")
        
        # TODO 好像有點危險，因為 remove subscription 後 unsubscribe 失敗，可能會造成訂閱記錄不一致
        
        unsubscribe_message = {
            "method": "UNSUBSCRIBE",
            "params": removing_streams,
            "id": request_id,
        }

        try:
            await self.ws_manager.send_message(
                connection_id, json.dumps(unsubscribe_message)
            )
            return True

        except Exception as e:
            logger.error(f"Unsubscription failed: {str(e)}")
            return False

    def _map_format(self, market_type: str, data: dict):
        # 原有的資料格式轉換邏輯保持不變
        event_type = data.get("e")
        symbol = data.get("s").lower()
        stream_type = data.get("e")
        topic = self._get_topic_name(symbol, stream_type, market_type)

        format_map = {
            "aggTrade": self._format_agg_trade,
            "trade": self._format_trade,
        }

        handler = format_map.get(event_type)
        if handler:
            return topic, handler(data, topic)
        else:
            logger.warning(f"Not implemented event type: {event_type}")
            return topic, data

    def _format_agg_trade(self, data: dict, topic: str):
        return {
            "topic": topic,
            "exchTimestamp": data["T"],
            "localTimestamp": int(time.time() * 1000),
            "price": data["p"],
            "quantity": data["q"],
            "side": "sell" if data["m"] else "buy",
            "firstTradeId": data["f"],
            "lastTradeId": data["l"],
            "aggTradeId": data["a"],
        }

    def _format_trade(self, data: dict, topic: str):
        return {
            "topic": topic,
            "exchTimestamp": data["T"],
            "localTimestamp": int(time.time() * 1000),
            "price": data["p"],
            "quantity": data["q"],
            "side": "sell" if data["m"] else "buy",
            "tradeId": data["t"],
        }