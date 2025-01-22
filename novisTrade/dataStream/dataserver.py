import json
import uuid
import redis
import logging
import asyncio
import websockets

from abc import abstractmethod, ABC
from typing import Any, Dict, List, Optional, Union, Tuple, Set

from .exchanges.base_ws import ExchangeWebSocket
from .exchanges.exchange_factory import ExchangeWebSocketFactory


class Subscriber(ABC):
    @abstractmethod
    def on_message(self, message: Dict[str, Any]) -> None:
        pass


class DataStreamServer:
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 8765,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        
        self.host = host
        self.port = port
        self.server = None
        self.logger = None
        self.config = config or {}
        
        # subscription for exchange api
        self.exchange_connections: Dict[str, ExchangeWebSocket] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
        self.redis_consumer = redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True
        )
        self.pubsub = self.redis_consumer.pubsub()
        
        # subscription for client
        self.subscriptions : Dict[Tuple[str, str, str], Set] = {}
        self.client_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        
        # async state tracks
        self.is_listening = False
        
    async def start(self):
        self.server = await websockets.serve(
            self._handle_client_connection,
            self.host,
            self.port
        )
        
        # init logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        
        self.logger.info(f"Server started at `{self.host}` port {self.port}")
        
        # tasks
        await asyncio.gather(
            self.listen_to_redis(),
            self.server.wait_closed()
        )

    def close(self):
        """關閉服務器"""
        if self.server:
            self.server.close()
        self.logger.info("Server closed")
    
    async def _handle_exchange_connection(self, websocket: websockets.WebSocketServerProtocol, path: str):
        pass
    
    async def subscribe_to_redis(self, channel: str):
        self.pubsub.subscribe(channel)
        
    async def unsubscribe_from_redis(self, channel: str):
        self.pubsub.unsubscribe(channel)
        
    async def listen_to_redis(self):
        while True:
            message = self.pubsub.get_message()
            if message and message['type'] == 'message':
                data = json.loads(message['data'])
                topic = message['channel']
                
                exchange, market_type, symbol, stream_type = topic.split(':')
                await self.broadcast(exchange, symbol, stream_type, data)
            await asyncio.sleep(0.001) #TODO: 透過 aioredis 寫成非同步的方式，不要用 sleep
                
    def get_exchange_connection(self, exchange_name: str) -> ExchangeWebSocket:
        """獲取或創建交易所連接"""
        if exchange_name not in self.exchange_connections:
            try:
                self.exchange_connections[exchange_name] = ExchangeWebSocketFactory.create(exchange_name)
            except ValueError as e:
                self.logger.error(f"Failed to create exchange connection: {e}")
                raise
        return self.exchange_connections[exchange_name]
    
    async def _handle_client_connection(self, websocket: websockets.WebSocketServerProtocol, path: str = '/'):
        """處理和 client 端的連線以及訊息"""
        try:
            client_id = str(uuid.uuid4())
            self.client_connections[client_id] = websocket
            
            async for message in websocket:
                request = json.loads(message)
                request['client_id'] = client_id
                response = await self._handle_request(request)
                await websocket.send(json.dumps(response))
                
        except websockets.exceptions.ConnectionClosed:
            if client_id in self.client_connections:
                del self.client_connections[client_id]
            self.logger.info("Client connection closed")
            
            for key in list(self.subscriptions.keys()):
                if client_id in self.subscriptions[key]:
                    self.subscriptions[key].discard(client_id)
                    if not self.subscriptions[key]:
                        del self.subscriptions[key]
            
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                'success': False,
                'message': 'Invalid JSON format'
            }))
            
        except Exception as e:
            await websocket.send(json.dumps({
                'success': False,
                'message': f'Error processing request: {str(e)}'
            }))
    
    async def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """處理來自 client 的請求
        Args:
            request (dict): 請求內容,包含:
                - action: 動作類型 (subscribe/unsubscribe/query)
                - exchange: 交易所名稱
                - symbol: 交易對名稱
                - client_id: 客戶端 ID
                
        Returns:
            dict: 回應內容,包含:
                - success: 是否成功
                - message: 訊息
                - data: 回應資料 (選填)
        """
        try:
            # 驗證請求格式
            if not self._validate_request(request):
                return {
                    'success': False,  
                    'message': 'Invalid request format'
                }
                
            # TODO: 我覺得這邊可以改成在交易所 websocket 裡面直接實作對應的 method
            # 像 Binance 就有 subscribe, unsubscribe, get_property, set_property 等 method
            action = request.get('action')
            if action == 'subscribe':
                return await self._handle_subscribe(request)
            elif action == 'unsubscribe': 
                return await self._handle_unsubscribe(request)
            elif action == 'query':
                return await self._handle_query(request)
            else:
                return {
                    'success': False,
                    'message': f'Unknown action: {action}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Error processing request: {str(e)}'
            }
            
    def _validate_request(self, request: Dict[str, Any]) -> bool:
        return True
    
    async def _handle_exchange_message(self, exchange: str, ws: ExchangeWebSocket):
        try:
            while True:
                await ws.on_messages()
        except Exception as e:
            self.logger.error(f"Error handling messages for {exchange}: {str(e)}")
            if exchange in self.running_tasks:
                del self.running_tasks[exchange]
            raise
        
    async def _ensure_ws_task(self, exchange: str, ws: ExchangeWebSocket):
        """確保交易所 websocket 任務正在運行"""
        if exchange not in self.running_tasks:
            task = self.running_tasks[exchange]
            if not task.done():
                return
            del self.running_tasks[exchange]
            
        task = asyncio.create_task(self._handle_exchange_message(exchange, ws))
        self.running_tasks[exchange] = task
    
    async def _handle_subscribe(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        TODO: request 中的 symbol 和 stream_type 要不要直接傳入 stream?
        """
        try:
            if not all(k in request for k in ['exchange', 'symbol', 'market_type', 'client_id']):
                return {
                    'success': False,
                    'message': 'Missing required fields'
                }
                
            #TODO symbol 可能是一個 list
            exchange = request['exchange']
            symbol = request['symbol']
            market_type = request.get('market_type', 'spot')
            stream_type = request.get('stream_type', 'trade')
            client_id = request['client_id']
            
            # 獲取交易所連接
            try:
                exchange_ws = self.get_exchange_connection(exchange)
                await exchange_ws.subscribe(symbol, stream_type, market_type)
                await self._ensure_ws_task(exchange, exchange_ws)
                # TODO: 這邊如果 client 有兩個以上，就會出錯
                
            except Exception as e:
                return {
                    'success': False,
                    'message': f"Failed to subscribe to {exchange}: {str(e)}"
                }
            
            # 訂閱相關的 redis channel
            channel = f"{exchange}:{market_type}:{symbol}:{stream_type}"
            await self.subscribe_to_redis(channel)
            
            subscription_key = (exchange, symbol, stream_type)
            if subscription_key not in self.subscriptions:
                self.subscriptions[subscription_key] = set()
            self.subscriptions[subscription_key].add(client_id)
            
            return {
                'success': True,
                'message': f"Subscribed to {exchange} {symbol}@{stream_type}"
            }
        
        except Exception as e:
            self.logger.error(f"Error in `_handle_subscribe`: {str(e)}")
            return {
                'success': False,
                'message': f"Error processing request: {str(e)}"
            }
    
    async def _handle_unsubscribe(self, request: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def _handle_query(self, request: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def _format_message(self, message: Dict[str, Any]) -> str:
        pass
    
    def add_subscription(self, exchange: str, symbol: str, data_type: str, subscriber: Subscriber) -> None:
        key = (exchange, symbol, data_type)
        if key not in self.subscriptions:
            self.subscriptions[key] = set()
        self.subscriptions[key].add(subscriber)
        
    def remove_subscription(self, exchange: str, symbol: str, data_type: str, subscriber: Subscriber) -> None:
        key = (exchange, symbol, data_type)
        if key in self.subscriptions:
            self.subscriptions[key].discard(subscriber)
            
    def get_subscribers(self, exchange: str, symbol: str, data_type: str) -> Set:
        key = (exchange, symbol, data_type)
        return self.subscriptions.get(key, set())
    
    async def broadcast(self, exchange: str, symbol: str, stream_type: str, data: Dict[str, Any]):
        # TODO: 更有效率的 broadcast
        subscriptions_key = (exchange, symbol, stream_type)
        if subscriptions_key in self.subscriptions:
            for client_id in self.subscriptions[subscriptions_key]:
                try:
                    if client_id in self.client_connections:
                        await self.client_connections[client_id].send(json.dumps(data))
                except Exception as e:
                    self.logger.error(f"Failed to send to client {client_id}: {str(e)}")