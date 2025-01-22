import json
import redis
from typing import List, Union
from .base_ws import ExchangeWebSocket

class BinanceWebSocket(ExchangeWebSocket):
    def __init__(self):
        super().__init__()
        self.redis_producer = redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True
        )
        
    def _get_topic_name(self, symbol: str, stream_type: str, market_type: str = "spot") -> str:
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
            
            # 處理心跳訊息
            if "ping" in data:
                await self.ws_manager.send_message(
                    connection_id,
                    json.dumps({"pong": data["ping"]})
                )
                return
                
            # 處理訂閱確認訊息
            if "result" in data:
                self.logger.info(f"Subscription confirmed for {connection_id}")
                return
                
            # 處理市場數據
            market_type = connection_id.split(":")[0]  
            topic, mapped_data = self._map_format(market_type, data)
            
            # 發送到 Redis
            self.redis_producer.publish(topic, json.dumps(mapped_data))
            
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            
    async def subscribe(
        self,
        streams: Union[str, List[str]],
        market_type: str = "spot",
        request_id: int = 1
    ) -> bool:
        """訂閱指定市場的串流"""
        if isinstance(streams, str):
            streams = [streams]
            
        # 建立連接 ID
        connection_id = f"{market_type}:main"
        
        # 如果尚未建立連接
        if connection_id not in self.ws_manager.connections:
            try:
                url = f"{self._get_base_url(market_type)}/{streams[0]}"
                await self.ws_manager.add_connection(url, connection_id)
            except Exception as e:
                self.logger.error(f"Failed to establish connection: {str(e)}")
                return False
                
        # 發送訂閱訊息
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": request_id
        }
        
        try:
            await self.ws_manager.send_message(
                connection_id,
                json.dumps(subscribe_message)
            )
            
            # 更新訂閱記錄
            if market_type not in self.subscriptions:
                self.subscriptions[market_type] = set()
            self.subscriptions[market_type].update(streams)
            
            self.logger.info(f"Successfully subscribed to {market_type}: {streams}")
            return True
            
        except Exception as e:
            self.logger.error(f"Subscription failed: {str(e)}")
            return False
        
    async def unsubscribe(
        self,
        streams: Union[str, List[str]],
        market_type: str = "spot",
        request_id: int = 312
    ):
        """取消訂閱一個或多個串流"""
        if isinstance(streams, str):
            streams = [streams]
            
        connection_id = f"{market_type}:main"
        
        if connection_id not in self.ws_manager.connections:
            self.logger.warning(f"No connection found for {connection_id}")
            return
            
        unsubscribe_message = {
            "method": "UNSUBSCRIBE",
            "params": streams,
            "id": request_id
        }
        
        try:
            await self.ws_manager.send_message(
                connection_id,
                json.dumps(unsubscribe_message)
            )
            
            # 更新訂閱記錄
            if market_type not in self.subscriptions:
                self.subscriptions[market_type] = set()
            self.subscriptions[market_type].difference_update(streams)
            
            self.logger.info(f"Successfully unsubscribed from {market_type}: {streams}")
            return True
            
        except Exception as e:
            self.logger.error(f"Unsubscription failed: {str(e)}")
            return False
            
    async def reconnect(self, market_type: str):
        """重新連接指定市場"""
        connection_id = f"{market_type}:main"
        
        # 先移除現有連接
        if connection_id in self.ws_manager.connections:
            await self.ws_manager.remove_connection(connection_id)
            
        # 取得該市場的訂閱列表
        subscriptions = list(self.subscriptions.get(market_type, set()))
        
        if not subscriptions:
            self.logger.warning(f"No subscriptions found for {market_type}")
            return False
            
        # 重新訂閱
        return await self.subscribe(subscriptions[0], market_type)
        
    def _map_format(self, market_type: str, data: dict):
        # 原有的資料格式轉換邏輯保持不變
        event_type = data.get("e")
        symbol = data.get("s").lower()
        stream_type = data.get("e").lower()
        topic = self._get_topic_name(symbol, stream_type, market_type)
        
        format_map = {
            "aggTrade": self._format_agg_trade,
            "trade": self._format_trade,
        }
        
        handler = format_map.get(event_type)
        if handler:
            return topic, handler(data, topic)
        else:
            self.logger.warning(f"Not implemented event type: {event_type}")
            return topic, data
        
    def _format_agg_trade(self, data: dict, topic: str):
        return {
            "topic": topic,
            "exchTimestamp": data["T"],
            "localTimestamp": data["E"],
            "price": data["p"],
            "quantity": data["q"],
            "side": "sell" if data["m"] else "buy",
            "firstTradeId": data["f"],
            "lastTradeId": data["l"],
            "aggTradeId": data["a"]
        }
        
    def _format_trade(self, data: dict, topic: str):
        return {
            "topic": topic,
            "exchTimestamp": data["T"],
            "localTimestamp": data["E"],
            "price": data["p"],
            "quantity": data["q"],
            "side": "sell" if data["m"] else "buy",
            "tradeId": data["t"]
        }
            
    async def close(self):
        """關閉所有連接"""
        await super().close()
        
        # 關閉 Redis 連接
        self.redis_producer.close()