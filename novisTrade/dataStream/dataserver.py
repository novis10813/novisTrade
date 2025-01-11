import json
import logging
import asyncio
import websockets

from abc import abstractmethod, ABC
from typing import Any, Dict, List, Optional, Union, Tuple, Set


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
        
        # TODO: 不應該分成多個 class，直接在 DataStreamServer 裡面實作即可
        self.subscription_manager = SubscriptionManager()
        
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
    
    def close(self):
        pass
    
    async def _handle_client_connection(self, websocket: websockets.WebSocketServerProtocol, path: str):
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
        pass
    
    async def _handle_subscribe(self, request: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def _handle_unsubscribe(self, request: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def _handle_query(self, request: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def _format_message(self, message: Dict[str, Any]) -> str:
        pass
    
class Subscriber(ABC):
    @abstractmethod
    def on_message(self, message: Dict[str, Any]) -> None:
        pass


class SubscriptionManager:
    def __init__(self):
        self.subscriptions: Dict[Tuple[str, str, str], Set] = {}
        
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