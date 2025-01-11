import time
import json
import logging
import asyncio
import websockets

from typing import Callable, Optional, List, Union

from .base_ws import ExchangeWebSocket

# Configure logger
logger = logging.getLogger('BinanceWebSocket')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class BinanceWebSocket(ExchangeWebSocket):
    def __init__(self):
        self.connections = {}  # 儲存不同市場的 WebSocket 連接
        self.subscriptions = {}  # 儲存每個市場的訂閱
        self.base_url = self._get_base_url()
        self.websocket = None
        self.is_connected = False
        
    def _get_base_url(self, market_type="spot"):
        urls = {
            "spot": "wss://stream.binance.com:9443/ws",
            "usd_futures": "wss://fstream.binance.com/ws",
            "coin_futures": "wss://dstream.binance.com/ws"
        }
        return urls.get(market_type, urls["spot"])
    
    async def connect(self, symbol: str, stream_type: str = "trade", market_type: str = "spot"):
        stream = f"{symbol.lower()}@{stream_type}"
        url = f"{self._get_base_url(market_type)}/{stream}"
        
        try:
            websocket = await websockets.connect(url)
            self.connections[market_type] = websocket
            self.subscriptions[market_type] = set()
            logger.info(f"Connected to {url}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            return False
        
    async def reconnect(self, market_type: str):
        """
        重新連接指定市場
        """
        # 獲取該市場的訂閱列表
        subscriptions = list(self.subscriptions.get(market_type, set()))
        if not subscriptions:
            logger.warning(f"No subscriptions found for {market_type}")
            return False

        # 使用第一個訂閱來重新建立連接
        initial_stream = subscriptions[0]
        symbol, stream_type = initial_stream.split('@')
        success = await self.connect(symbol, stream_type, market_type)
        
        if success:
            # 重新訂閱所有串流
            await self.subscribe(subscriptions, market_type)
            logger.info(f"Successfully reconnected to {market_type} and resubscribed")
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
    
    async def subscribe(self, params: Union[str, List[str]], market_type: str = "spot", request_id: int = 1):
        """
        訂閱指定市場的串流
        """
        if market_type not in self.connections:
            # 如果該市場尚未連接，先建立連接
            initial_stream = params[0] if isinstance(params, list) else params
            symbol, stream_type = initial_stream.split('@')
            success = await self.connect(symbol, stream_type, market_type)
            if not success:
                return

        websocket = self.connections[market_type]
        
        if isinstance(params, str):
            params = [params]
            
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": params,
            "id": request_id
        }
        
        await websocket.send(json.dumps(subscribe_message))
        response = await self._wait_for_response(market_type, request_id)
        
        if response.get("result") is None:
            self.subscriptions[market_type].update(params)
            logger.info(f"Successfully subscribed to {market_type}: {params}")
        else:
            logger.error(f"Subscription failed: {response}")
            
    async def unsubscribe(self, params: Union[str, List[str]], request_id: int = 312):
        """
        取消訂閱一個或多個串流
        """
        if not self.is_connected:
            logger.warning("No connection established")
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
            logger.info(f"Successfully unsubscribed from: {params}")
        else:
            logger.error(f"Unsubscription failed: {response}")
    
    async def list_subscriptions(self):
        """
        列出所有市場的訂閱
        """
        for market_type, subs in self.subscriptions.items():
            logger.info(f"Streams subscribed for {market_type}: {list(subs)}")
            
    async def set_property(self, property_name: str, value: any, request_id: int = 5):
        """
        設置 WebSocket 屬性
        """
        if not self.is_connected:
            logger.warning("No connection established")
            return
            
        set_property_message = {
            "method": "SET_PROPERTY",
            "params": [property_name, value],
            "id": request_id
        }
        
        await self.websocket.send(json.dumps(set_property_message))
        response = await self._wait_for_response(request_id)
        logger.info(f"Property setting result: {response}")
    
    async def get_property(self, property_name: str, request_id: int = 2):
        """
        獲取 WebSocket 屬性
        """
        if not self.is_connected:
            logger.warning("No connection established")
            return
            
        get_property_message = {
            "method": "GET_PROPERTY",
            "params": [property_name],
            "id": request_id
        }
        
        await self.websocket.send(json.dumps(get_property_message))
        response = await self._wait_for_response(request_id)
        
        if "result" in response:
            logger.info(f"Property value: {response['result']}")
            return response['result']
        else:
            logger.error(f"Failed to get property: {response}")

    async def receive_messages(self, callback: Optional[Callable] = None):
        """
        同時接收所有市場的訊息
        """
        if not self.connections:
            logger.warning("No connections established")
            return
            
        # 對每個市場創建generator
        async def receive_all():
            tasks = []
            for market_type, websocket in self.connections.items():
                gen = self._receive_market_messages(market_type, websocket, callback)
                task = asyncio.create_task(gen.__anext__())
                tasks.append((gen, task))
            
            while True:
                # 等待任一數據到達
                done, pending = await asyncio.wait(
                    [task for _, task in tasks],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # 更新任務列表並返回數據
                for done_task in done:
                    for i, (gen, task) in enumerate(tasks):
                        if task == done_task:
                            try:
                                yield await done_task
                                # 創建新的任務繼續接收
                                tasks[i] = (gen, asyncio.create_task(gen.__anext__()))
                            except StopAsyncIteration:
                                continue
        
        async for data in receive_all():
            yield data
        
    async def _receive_market_messages(self, market_type: str, websocket, callback: Optional[Callable] = None):
            while True:
                try:
                    while True:
                        try:
                            message = await websocket.recv()
                            data = json.loads(message)

                            if isinstance(data, dict):
                                if data.get("ping"):
                                    pong_message = {"pong": data["ping"]}
                                    await websocket.send(json.dumps(pong_message))
                                    logger.debug(f"Responded to ping from {market_type}")
                                    continue
                                elif "id" in data:
                                    continue

                            if callback:
                                await callback(market_type, data)
                                
                            yield data  # 直接yield數據
                            
                        except websockets.exceptions.ConnectionClosed:
                            logger.error(f"{market_type} connection closed")
                            break
                            
                except Exception as e:
                    logger.error(f"Error in {market_type} connection: {str(e)}")
                    
                logger.info(f"Attempting to reconnect to {market_type}")
                
                if await self.reconnect(market_type):
                    websocket = self.connections[market_type]
                else:
                    logger.error(f"Failed to reconnect to {market_type}")
