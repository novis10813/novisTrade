import json
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
        
        # subscription
        self.exchange_connections: Dict[str, ExchangeWebSocket] = {}
        self.subscriptions : Dict[Tuple[str, str, str], Set] = {}
        
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
        await self.server.wait_closed()

    def close(self):
        """關閉服務器"""
        if self.server:
            self.server.close()
        self.logger.info("Server closed")
    
    async def _handle_exchange_connection(self, websocket: websockets.WebSocketServerProtocol, path: str):
        pass
    
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
            async for message in websocket:
                request = json.loads(message)
                response = await self._handle_request(request)
                await websocket.send(json.dumps(response))
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("Client connection closed")
            
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
                
            #TODO symbol 需要根據交易所的格式進行處理
            # 所以在這邊，我傳進來的格式應該是統一的格式，而不是交易所的格式
            # 然後在每個交易所的 websocket 類裡面，再進行格式轉換
            exchange = request['exchange']
            symbol = request['symbol'] # 會是一個 list，裡面會有不同的幣對
            market_type = request.get('market_type', 'spot')
            stream_type = request.get('stream_type', 'trade')
            client_id = request['client_id']
            
            # 獲取交易所連接
            try:
                exchange_ws = self.get_exchange_connection(exchange)
                # TODO: 格式轉換，且 subscribe 的方法應該是統一的 (exchange_ws 的是 subscribe(self, symbol: str, stream_type: str), binance 是 subscribe(self, params: Union[str, List[str]], market_type: str = "spot", request_id: int = 1))
                await exchange_ws.subscribe(symbol, stream_type, market_type)
            except Exception as e:
                return {
                    'success': False,
                    'message': f"Failed to subscribe to {exchange}: {str(e)}"
                }
                
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