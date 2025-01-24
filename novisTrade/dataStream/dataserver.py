import json
import uuid
import asyncio
import logging
import asyncio
import websockets
import websockets.asyncio.client
import websockets.asyncio.server

from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from .exchanges.base_ws import ExchangeWebSocket
from .exchanges.exchange_factory import ExchangeWebSocketFactory

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
                
        # 紀錄每個 client 訂閱了哪些交易所的哪些交易對有多少人訂閱
        self.client_subscriptions: Dict[str, Set[str]] = {}
        # 保存每個 client 的連線
        self.client_connections: Dict[str, websockets.asyncio.client.ClientConnection] = {}
        
        # setup logger
        self._setup_logger(level=self.config.get('log_level', logging.INFO))
        
    async def start(self):
        self.server = await websockets.serve(
            self._handle_client_connection,
            self.host,
            self.port
        )
        
        self.logger.info(f"Server started at `{self.host}` port {self.port}")
        
        # tasks
        try:
            await self.server.wait_closed()
        except (asyncio.CancelledError, KeyboardInterrupt):
            self.logger.info("Shutting down server...")
            await self.close()
            
    def _setup_logger(self, level: int = logging.INFO):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)

    async def close(self):
        """清理所有資源"""
        # 關閉所有客戶端連接
        # 先複製一份字典的條目
        self.logger.info("Now closing all client connections...")
        client_connections = list(self.client_connections.items())
        # 關閉所有客戶端連接
        for client_id, websocket in client_connections:
            await websocket.close()
        
        self.logger.info("Now closing all exchange connections...")
        # 關閉所有交易所連接
        for exchange_ws in self.exchange_connections.values():
            await exchange_ws.close()
        
        # 關閉 server
        self.logger.info("Now closing server...")
        if self.server:
            self.server.close()
            
        self.logger.info("All resources cleaned up")
            
    async def _handle_client_connection(self, websocket: websockets.asyncio.server.ServerConnection, path: str = '/'):
        """WebSocket Server 的 Entry Point
        這邊主要有三個邏輯:
        1. 新的 client 連線時要處理的東西
        2. 處理來自 client 的請求
        3. client 斷線時要處理的東西
        """
        try:
            client_id = await self.__new_client_connection(websocket)
            
            async for message in websocket:
                await self.__handle_request(client_id, message)
        
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Client connection closed: {client_id}")
            
        except Exception as e:
            self.logger.error(f"Error in client connection: {str(e)}")
            
        finally:
            if client_id:
                await self.__handle_disconnection(client_id)
                    
    async def __new_client_connection(self, websocket: websockets.asyncio.client.ClientConnection) -> str:
        """有新的 client 連線時要處理的東西
        1. 處理 client_id
        2. 紀錄 client 連線
        # THINK: 我連線的時候能夠直接指定 client_id 嗎？
        """
        client_id = str(uuid.uuid4())
        self.client_connections[client_id] = websocket
        
        await websocket.send(json.dumps({
            "type": "connection",
            "client_id": client_id
        }))
        
        self.logger.info(f"New client connected: {client_id}")
        return client_id
    
    async def __handle_request(self, client_id: str, message: Dict[str, Any]):
        """處理來自 client 的請求
        Args:
            client_id (str): 客戶端 ID
            message (dict): 請求內容，包含:
                - action: 請求類型 (subscribe/unsubscribe/query...)
        """
        try:
            parsed_message = self._validate_message(message)
            action = parsed_message.get('action')
            if action == 'subscribe':
                response = await self._handle_subscribe(parsed_message)
            elif action == 'unsubscribe':
                response = await self._handle_unsubscribe(parsed_message)
            else:
                response = {
                    'success': False,
                    'message': f'Unknown action: {action}'
                }
                self.logger.warning(f"Unknown action from client {client_id}: {action}")
                await self.client_connections[client_id].send(json.dumps(response))
                
        except json.JSONDecodeError:
            response = {
                'success': False,
                'message': 'Invalid JSON format'
            }
            self.logger.warning(f"Invalid JSON format from client {client_id}: {message}")
            await self.client_connections[client_id].send(json.dumps(response))
            
        except Exception as e:
            response = {
                'success': False,
                'message': f'Error processing request: {str(e)}'
            }
            self.logger.error(f"Error processing request from client {client_id}: {str(e)}")
            await self.client_connections[client_id].send(response)
        
    async def __handle_disconnection(self, client_id: str):
        # 移除 client 連線
        if client_id in self.client_connections:
            await self.client_connections[client_id].close()
            del self.client_connections[client_id]
        
        # 移除 client 的訂閱 key,按 exchange 和 stream_type 分組
        unsubscribe_tasks = {}
        for key in list(self.client_subscriptions.keys()):
            if client_id in self.client_subscriptions[key]:
                # 先移除這個 client 的訂閱紀錄
                self.client_subscriptions[key].remove(client_id)
                
                # 只有當沒有其他 client 訂閱時,才進行 unsubscribe
                if not self.client_subscriptions[key]:
                    exchange, market_type, symbol, stream_type = key.split(':') 
                    group_key = (exchange, market_type)
                    if group_key not in unsubscribe_tasks:
                        unsubscribe_tasks[group_key] = []
                    unsubscribe_tasks[group_key].append((symbol, stream_type))
                    del self.client_subscriptions[key]
        
        # 對每個 exchange 批次執行 unsubscribe
        for (exchange, market_type), tasks in unsubscribe_tasks.items():
            exchange_ws = await self._get_exchange_connection(exchange)
            symbols = [t[0] for t in tasks]
            stream_type = tasks[0][1]  # 同一組的 market_type 應該相同
            await exchange_ws.unsubscribe(symbols, stream_type, market_type, client_id)
            
        self.logger.info(f"Client disconnected: {client_id}, cleaning up completed")
            
    def _validate_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """驗證來自 client 的請求
        
        Args:
            message (dict): 請求內容
            
        Returns:
            解析後的請求內容
            
        Raises:
            json.JSONDecodeError: 無法解析錯誤
            ValueError: 格式錯誤
        """
        data = json.loads(message)
        
        require_fieds = ['action', 'params', 'client_id']
        missing_fields = [f for f in require_fieds if f not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        return data
            
    async def _handle_subscribe(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """處理訂閱請求
        處理步驟:
        1. 解析 request (應該放在交易所端處理即可)
        2. 獲取交易所連接
        3. 如果成功，建立聽取交易所 websocket.on_messages 的 task
        4. 紀錄是誰訂閱、這個交易對有多少人訂閱
        """
        # 解析 request
        parsed_requests = self._parse_subscription_request(request["params"])
        client_id = request.get('client_id')
        for parsed_request in parsed_requests:
            try:
                exchange = parsed_request['exchange']
                market_type = parsed_request['market_type']
                stream_type = parsed_request['stream_type']
                symbols = parsed_request['symbol']
                request_id = parsed_request.get('request_id', client_id)
                
                # 獲取交易所連接
                exchange_ws = await self._get_exchange_connection(exchange)
                # 把 symbols 分成已經訂閱的和沒有訂閱的
                # 如果有沒有訂閱的，就訂閱
                
                # 檢查該交易所是否已經訂閱，回傳沒有訂閱的 symbol
                not_sub_symbols = exchange_ws.is_subscribed(symbols, stream_type, market_type)
                # 如果沒有未訂閱的 symbol，就不用訂閱
                if not not_sub_symbols:
                    continue
                
                # 反之，就訂閱
                is_success = await exchange_ws.subscribe(not_sub_symbols, stream_type, market_type, request_id)
                # 如果成功，就在 client_subscriptions 裡面記錄
                if is_success:
                    for symbol in symbols:
                        if symbol not in self.client_subscriptions:
                            key = f"{exchange}:{market_type}:{symbol}:{stream_type}"
                            self.client_subscriptions[key] = set()
                        self.client_subscriptions[key].add(client_id)
                # 這個時候 redis 的 producer 就已經有資料進來了，所以 consumer 應該放在 client 端，而不是 server 端
                # 所以訂閱 redis consumer 的部分應該放在 client 端
                else:
                    return {
                        'success': False,
                        'message': f"Failed to subscribe to {exchange}: {str(e)}"
                    }
            except Exception as e:
                return {
                    'success': False,
                    'message': f"Failed to subscribe to {exchange}: {str(e)}"
                }
        
        return {
            'success': True,
            'message': 'Successfully subscribed'
        }
            
    def _parse_subscription_request(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析訂閱請求
        
        訂閱請求應該包含以下欄位:
        - exchange (str): 交易所名稱
        - streams (list): 訂閱的串流類型
        - market_type (str): 市場類型
        """
        # 使用巢狀的 defaultdict 來組織數據
        grouped_data = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(list)
            )
        )

        for param in params:
            parts = param.split(':')
            if len(parts) < 4:
                continue
            
            exchange = parts[0]
            market_type = parts[1]
            symbol = parts[2]
            stream_type = parts[3]
            
            # 將 symbol 加入到對應的分類中
            grouped_data[exchange][market_type][stream_type].append(symbol)

        # 轉換成最終格式
        result = []
        for exchange, market_types in grouped_data.items():
            for market_type, stream_types in market_types.items():
                for stream_type, symbols in stream_types.items():
                    result.append({
                        'exchange': exchange,
                        'market_type': market_type,
                        'stream_type': stream_type,
                        'symbol': symbols
                    })
                
        return result
    
    async def _get_exchange_connection(self, exchange_name: str) -> ExchangeWebSocket:
        """獲取或創建交易所連接"""
        if exchange_name not in self.exchange_connections:
            try:
                exchange_ws = ExchangeWebSocketFactory.create(exchange_name)
                await exchange_ws.start()
                self.exchange_connections[exchange_name] = exchange_ws
            except ValueError as e:
                self.logger.error(f"Failed to create exchange connection: {e}")
                raise
        return self.exchange_connections[exchange_name]
    
    async def _handle_unsubscribe(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """處理取消訂閱請求
        處理步驟:
        1. 解析 request
        2. 獲取交易所連接
        3. 如果成功，取消訂閱
        4. 更新 client_subscriptions
        """
        # 格式和訂閱請求一樣
        parsed_requests = self._parse_subscription_request(request["params"])
        client_id = request.get('client_id')
        
        for parsed_request in parsed_requests:
            try:
                exchange = parsed_request['exchange']
                market_type = parsed_request['market_type']
                stream_type = parsed_request['stream_type']
                symbols = parsed_request['symbol']
                request_id = parsed_request.get('request_id', client_id)
                
                # 獲取交易所連接
                exchange_ws = await self._get_exchange_connection(exchange)
                
                # 取消訂閱只發生在 self.client_subscriptions 的最後一個 client 取消訂閱的時候
                not_sub_symbols = exchange_ws.is_subscribed(symbols, stream_type, market_type)
                # 實際上要取消訂閱的 symbol
                sub_symbols = list(set(symbols) - set(not_sub_symbols))
                for symbol in sub_symbols:
                    key = f"{exchange}:{market_type}:{symbol}:{stream_type}"
                    self.client_subscriptions[key].remove(client_id)
                    # 如果沒有人訂閱了，就取消訂閱
                    if not self.client_subscriptions[key]:
                        await exchange_ws.unsubscribe([symbols], stream_type, market_type, request_id)
                        del self.client_subscriptions[key]
                        
            except Exception as e:
                return {
                    'success': False,
                    'message': f"Failed to unsubscribe to {exchange}: {str(e)}"
                }
                
        return {
            'success': True,
            'message': 'Successfully unsubscribed'
        }