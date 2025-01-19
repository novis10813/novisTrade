import json
import redis
import websockets


from typing import List, Union

from .base_ws import ExchangeWebSocket


class BinanceWebSocket(ExchangeWebSocket):
    def __init__(self):
        super().__init__()
        self.base_url = self._get_base_url()
        self.websocket = None
        self.is_connected = False
        self.subscriptions = {}
        
        self.redis_producer = redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True
        )
        
    def _get_topic_name(self, symbol: str, stream_type: str, market_type: str = "spot") -> str:
        # 產生 topic 名稱
        return f"binance:{market_type}:{symbol}:{stream_type}"
        
    def _get_base_url(self, market_type="spot"):
        urls = {
            "spot": "wss://stream.binance.com:9443/ws",
            "usd_futures": "wss://fstream.binance.com/ws",
            "coin_futures": "wss://dstream.binance.com/ws"
        }
        return urls.get(market_type, urls["spot"])
    
    async def _connect(self, stream: str, market_type: str = "spot"):
        url = f"{self._get_base_url(market_type)}/{stream}"
        
        try:
            websocket = await websockets.connect(url)
            self.connections[market_type] = websocket
            self.subscriptions[market_type] = set()
            self.logger.info(f"Connected to {url}")
            return True
        except Exception as e:
            self.logger.error(f"Connection failed: {str(e)}")
            return False
        
    async def reconnect(self, market_type: str):
        """
        重新連接指定市場
        """
        # 獲取該市場的訂閱列表
        subscriptions = list(self.subscriptions.get(market_type, set()))
        
        if not subscriptions:
            self.logger.warning(f"No subscriptions found for {market_type}")
            return False

        # 使用第一個訂閱來重新建立連接
        initial_stream = subscriptions[0]
        success = await self._connect(initial_stream, market_type)
        
        if success:
            # 重新訂閱所有串流
            for stream in subscriptions:
                symbol, stream_type = stream.split("@")
                await self.subscribe(symbol, stream_type, market_type)
            self.logger.info(f"Successfully reconnected to {market_type} and resubscribed")
            return True
        return False
    
    async def _wait_for_response(self, market_type: str, request_id: int):
        websocket = self.connections[market_type]
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            
            if isinstance(data, dict) and "id" in data:
                if data["id"] == request_id:
                    return data
            elif "e" in data:
                continue
    
    async def subscribe(
        self,
        symbol: str,
        stream_type: str,
        market_type: str = "spot",
        request_id: int = 1
    ):
        """
        訂閱指定市場的串流
        """
        stream = f"{symbol.lower()}@{stream_type}"
        
        if market_type not in self.connections:
            # 如果該市場尚未連接，先建立連接
            success = await self._connect(stream, market_type)
            if not success:
                return
        
        websocket = self.connections[market_type]
        
        if isinstance(stream, str):
            stream = [stream]
            
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": stream,
            "id": request_id
        }
        
        await websocket.send(json.dumps(subscribe_message))
        response = await self._wait_for_response(market_type, request_id)
        
        if response.get("result") is None:
            self.subscriptions[market_type].update(stream)
            self.logger.info(f"Successfully subscribed to {market_type}: {symbol}")
        else:
            self.logger.error(f"Subscription failed: {response}")
            
    async def unsubscribe(self, params: Union[str, List[str]], request_id: int = 312):
        """
        取消訂閱一個或多個串流
        """
        if not self.is_connected:
            self.logger.warning("No connection established")
            return
            
        if isinstance(params, str):
            params = [params]
            
        unsubscribe_message = {
            "method": "UNSUBSCRIBE",
            "params": params,
            "id": request_id
        }
        
        await self.websocket.send(json.dumps(unsubscribe_message))
        response = await self._wait_for_response(request_id)
        
        self.subscriptions.difference_update(params)
        if response.get("result") is None:
            self.logger.info(f"Successfully unsubscribed from: {params}")
        else:
            self.logger.error(f"Unsubscription failed: {response}")
    
    async def list_subscriptions(self):
        """
        列出所有市場的訂閱
        """
        for market_type, subs in self.subscriptions.items():
            self.logger.info(f"Streams subscribed for {market_type}: {list(subs)}")
            
    async def set_property(self, property_name: str, value: any, request_id: int = 5):
        """
        設置 WebSocket 屬性
        """
        if not self.is_connected:
            self.logger.warning("No connection established")
            return
            
        set_property_message = {
            "method": "SET_PROPERTY",
            "params": [property_name, value],
            "id": request_id
        }
        
        await self.websocket.send(json.dumps(set_property_message))
        response = await self._wait_for_response(request_id)
        self.logger.info(f"Property setting result: {response}")
    
    async def get_property(self, property_name: str, request_id: int = 2):
        """
        獲取 WebSocket 屬性
        """
        if not self.is_connected:
            self.logger.warning("No connection established")
            return
            
        get_property_message = {
            "method": "GET_PROPERTY",
            "params": [property_name],
            "id": request_id
        }
        
        await self.websocket.send(json.dumps(get_property_message))
        response = await self._wait_for_response(request_id)
        
        if "result" in response:
            self.logger.info(f"Property value: {response['result']}")
            return response['result']
        else:
            self.logger.error(f"Failed to get property: {response}")
            
    def _map_format(self, market_type: str, data: dict):
        """
        將數據映射成統一格式
        """
        
        event_type = data.get("e")
        symbol = data.get("s").lower()
        stream_type = data.get("e").lower()
        topic = self._get_topic_name(symbol, stream_type, market_type)
        
        format_map = {
            "aggTrade": self._format_agg_trade,
            "trade": self._format_trade,
            # "kline": self._format_kline,
            # "depth": self._format_depth
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

    async def on_messages(self) -> None:
        """
        同時接收所有市場的訊息，並發送到 Kafka
        """
        if not self.connections:
            self.logger.warning("No connections established")
            return
        
        async for market_type, data in self._receive_all():
            topic, mapped_data = self._map_format(market_type, data)
            self.redis_producer.publish(topic, json.dumps(mapped_data))
            
    def __del__(self):
        """
        清理資源
        """
        self.redis_producer.close()