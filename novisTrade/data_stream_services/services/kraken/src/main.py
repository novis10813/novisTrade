import os
import time
import json
import asyncio

from datetime import datetime
from typing import List, Union, Any, Optional

from shared.core.base_ws import ExchangeWebSocket
from shared.utils import map_logging_level


class KrakenWebSocket(ExchangeWebSocket):
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        logging_level: str = "INFO"
    ):
        super().__init__(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            logging_level=logging_level
        )
        
    def _get_topic_name(self, symbol: str, stream_type: str, market_type: str = "spot") -> str:
        return f"kraken:{market_type}:{symbol}:{stream_type}"
    
    def _get_base_url(self, market_type="spot"):
        urls = {
            "spot": "wss://ws.kraken.com/v2",
            "user": "wss://ws-auth.kraken.com/v2",
            "perp": "wss://futures.kraken.com/ws/v1",
        }
        return urls.get(market_type, urls["spot"])
        
    async def _handle_message(self, connection_id: str, message: str):
        try:
            data = json.loads(message)
            market_type = connection_id.split(":")[0]
            
            # 無視 snapshot
            if self._is_snapshot(market_type, data):
                return
            
            # 無視 heartbeat
            if data.get("channel", None) == "heartbeat":
                return
            
            if data.get("channel", None) == "status":
                return
            
            # 無視訂閱/取消訂閱確認訊息
            if data.get("event", None) == "subscribed":
                return
            if "result" in data:
                return
            
            topic, mapped_data = self._map_format(market_type, data)
            
            # 發送到 Redis
            await self.redis_producer.publish(topic, json.dumps(mapped_data))
            
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            
    async def _handle_reconnection(self, connection_id: str):
        try:
            market_type = connection_id.split(":")[0]
            streams = list(self.subscriptions.get(market_type, set()))
            # 把 streams 拆成 symbol 和 stream_type
            symbols = [stream.split("@")[0] for stream in streams]
            stream_type = streams[0].split("@")[1]
            # 獲得訂閱訊息
            subscribe_message = self._map_subscribe_message("subscribe", symbols, stream_type, market_type)
            # 重新訂閱
            await self.ws_manager.send_message(
                connection_id,
                json.dumps(subscribe_message)
            )
            self.logger.info(f"Restore {len(symbols)} subscriptions for {market_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to restore subscriptions: {str(e)}")
            
    def _map_subscribe_message(
        self,
        method: str,
        symbols: List[str], 
        stream_type: str, 
        market_type: str = "spot"
    ) -> Union[str, Any]:
        """
        heartbeat 不用回應
        """
        if market_type == "spot":
            # using v2 API
            return {
                "method": method,
                "params": {
                    "channel": stream_type,
                    "symbol": symbols
                }
            }
            
        elif market_type == "perp":
            return {
                "event": method,
                "feed": stream_type,
                "product_ids": symbols
            }
            
    async def subscribe(
        self,
        symbols: List[str],
        stream_type: str,
        market_type: str = "spot",
        request_id: Optional[int] = None
    ) -> bool:
        """訂閱市場數據
        這邊傳進來的東西一定會是在同一個 market_type 下的
        但是會有不同的 stream type。
        """ 
        if request_id is None:
            request_id = int(time.time() * 1000)
            
        streams = [f"{symbol}@{stream_type}" for symbol in symbols]
        
        connection_id = f"{market_type}:main"
        
        if connection_id not in self.ws_manager.connections:
            try:
                url = f"{self._get_base_url(market_type)}"
                await self.ws_manager.add_connection(url, connection_id)
            except Exception as e:
                self.logger.error(f"Error adding connection: {str(e)}")
                return False
            
        subscribe_message = self._map_subscribe_message("subscribe", symbols, stream_type, market_type)
        
        try:
            await self.ws_manager.send_message(
                connection_id,
                json.dumps(subscribe_message)
            )
            
            if market_type not in self.subscriptions:
                self.subscriptions[market_type] = set()
            for stream in streams:
                self.subscriptions[market_type].add(stream)
            self.logger.info(f"Successfully subscribed to {market_type}: {streams}")
            return True
        
        except Exception as e:
            self.logger.error(f"Subscription failed: {str(e)}")
            return False
        
    async def unsubscribe(
        self,
        symbols: List[str],
        stream_type: str,
        market_type: str = "spot",
        request_id: Optional[int] = None
    ):
        """取消訂閱市場數據"""
        if request_id is None:
            request_id = int(time.time() * 1000)
            
        streams = [f"{symbol}@{stream_type}" for symbol in symbols]
        connection_id = f"{market_type}:main"
        
        unsubscribe_message = self._map_subscribe_message("unsubscribe", symbols, stream_type, market_type)
        
        try:
            await self.ws_manager.send_message(
                connection_id,
                json.dumps(unsubscribe_message)
            )
            
            if market_type not in self.subscriptions:
                self.subscriptions[market_type] = set()
            self.subscriptions[market_type].difference_update(streams)
            
            self.logger.info(f"Successfully unsubscribed from {market_type}: {streams}")
            return True

        except Exception as e:
            self.logger.error(f"Unsubscription failed: {str(e)}")
            return False
        
    def _is_snapshot(self, market_type: str, data: dict) -> bool:
        """
        判斷是否為快照
        """
        if market_type == "spot":
            return data.get("type") == "snapshot"
        
        elif market_type == "perp":
            return "snapshot" in data.get("feed")
        
    def _map_format(self, market_type: str, data: dict):
        """
        v1 API (future) 的格式特點
        - heartbeat 要自行訂閱
        - 會先傳送 feed = "xxx_snapshot" 的資料，之後才更新 feed = "xxx"，xxx 為 stream type
        
        Received Snapshot Format
        ------------------------
        {
            "feed": "trade_snapshot",
            "product_id": "PI_XBTUSD",
            "trades": [
                {
                    "feed": "trade",
                    "product_id": "PI_XBTUSD",
                    "uid": "caa9c653-420b-4c24-a9f1-462a054d86f1",
                    "side": "sell",
                    "type": "fill",
                    "seq": 655508,
                    "time": 1612269657781,
                    "qty": 440,
                    "price": 34893
                },
                {
                    "feed": "trade",
                    "product_id": "PI_XBTUSD",
                    "uid": "45ee9737-1877-4682-bc68-e4ef818ef88a",
                    "side": "sell",
                    "type": "fill",
                    "seq": 655507,
                    "time": 1612269656839,
                    "qty": 9643,
                    "price": 34891
                }
            ]
        }
        
        Received Delta Format
        ---------------------
        {
            "feed": "trade",
            "product_id": "PI_XBTUSD",
            "uid": "05af78ac-a774-478c-a50c-8b9c234e071e",
            "side": "sell",
            "type": "fill",
            "seq": 653355,
            "time": 1612266317519,
            "qty": 15000,
            "price": 34969.5
        }
        
        欄位說明:
        product_id: 交易對， PI 指的是永續合約， FI 則是普通合約 (最後會加到期日期)
        side: 成交時 taker 單發生的方向
        type: 成交的類型，有 fill, liquidation, termination 和 block。 (最後兩種不太確定)
        time: 成交時間，應該是 Unix timestamp (milliseconds)
        
        v2 API (spot) 的格式特點
        - heartbeat 每秒傳送一次
        - 會先傳送 type = "snapshot" 的資料，之後才更新 type = "update"
        
        Received Snapshot Format
        ------------------------
        {
            "channel": "trade",
            "type": "snapshot",
            "data": [
                {
                    "symbol": "MATIC/USD",
                    "side": "buy",
                    "price": 0.5147,
                    "qty": 6423.46326,
                    "ord_type": "limit",
                    "trade_id": 4665846,
                    "timestamp": "2023-09-25T07:48:36.925533Z"
                },
                {
                    "symbol": "MATIC/USD",
                    "side": "buy",
                    "price": 0.5147,
                    "qty": 1136.19677815,
                    "ord_type": "limit",
                    "trade_id": 4665847,
                    "timestamp": "2023-09-25T07:49:36.925603Z"
                }
            ]
        }
        
        Received Delta Format
        ---------------------
        {
            "channel": "trade",
            "type": "update",
            "data": [
                {
                    "symbol": "MATIC/USD",
                    "side": "sell",
                    "price": 0.5117,
                    "qty": 40.0,
                    "ord_type": "market",
                    "trade_id": 4665906,
                    "timestamp": "2023-09-25T07:49:37.708706Z"
                }
            ]
        }
        
        欄位說明:
        symbol: 交易對，中間有 "/" 分隔
        side: 成交時 taker 單發生的方向
        ord_type: taker order 的類型，有 limit 和 market。taker 會有 limit 的原因是掛的價格會直接吃到 orderbook
        timestamp: ISO 8601
        
        共同點
        - heartbeat 不需要回應
        """
        # 透過 market_type 來判斷是哪一種 API
        if market_type == "spot":
            event_type = data.get("channel")
            symbol = data["data"][0].get("symbol")
            topic = self._get_topic_name(symbol, event_type, market_type)
            
            v2_format_map = {
                "trade": self._format_v2_trade
            }
            handler = v2_format_map.get(event_type)
            
        elif market_type == "perp":
            event_type = data.get("feed")
            symbol = data.get("product_id")
            topic = self._get_topic_name(symbol, event_type, market_type)
            
            v1_format_map = {
                "trade": self._format_v1_trade
            }
            handler = v1_format_map.get(event_type)
            
        if handler:
            return topic, handler(data, topic)
        else:
            self.logger.warning(f"Not implemented event type: {event_type}")
            return topic, data
            
    def _format_v1_trade(self, data: dict, topic: str):
        return {
            "topic": topic,
            "exchTimestamp": data["time"],
            "localTimestamp": int(time.time() * 1000),
            "price": data["price"],
            "quantity": data["qty"],
            "side": data["side"],
            "tradeId": data["seq"]
        }
        
    def _format_v2_trade(self, data: dict, topic: str):
        return {
            "topic": topic,
            "exchTimestamp": int(datetime.fromisoformat(data["data"][0]["timestamp"].replace('Z', '+00:00')).timestamp() * 1000),
            "localTimestamp": int(time.time() * 1000),
            "price": data["data"][0]["price"],
            "quantity": data["data"][0]["qty"],
            "side": data["data"][0]["side"],
            "tradeId": data["data"][0]["trade_id"]
        }
        
async def main():
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv("REDIS_DB", 0))
    logging_level = os.getenv("LOGGING_LEVEL", "INFO")
    
    ws_client = KrakenWebSocket(
        redis_host=redis_host,
        redis_port=redis_port,
        redis_db=redis_db,
        logging_level=map_logging_level(logging_level)
    )
    
    await ws_client.start()

if __name__ == "__main__":
    asyncio.run(main())