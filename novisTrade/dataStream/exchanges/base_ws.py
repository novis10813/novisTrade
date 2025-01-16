import json
import logging
import asyncio
import websockets

from abc import ABC, abstractmethod
from typing import List, Union, Optional

class ExchangeWebSocket(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        
        self.connections = {}
        self.subscriptions = {}
        
    @abstractmethod
    async def _connect(self):
        raise NotImplementedError
    
    @abstractmethod
    async def reconnect(self, market_type: str):
        raise NotImplementedError
        
    @abstractmethod
    async def subscribe(
        self,
        symbol: Union[str, List[str]],
        stream_type: str,
        market_type: str = "spot",
        request_id: Optional[int] = None
    ) -> bool:
        """統一的訂閱接口
        
        Args:
            symbol (Union[str, List[str]]): 訂閱的交易對
            stream_type (str): 串流類型
            market_type (str, optional): 市場類型. Defaults to "spot".
            request_id (Optional[int], optional): 請求 ID. Defaults to None.
            
        Returns:
            bool: 訂閱是否成功
        """
        
    @abstractmethod
    async def on_messages(self):
        raise NotImplementedError
    
    @abstractmethod
    async def _map_format(self, data: dict):
        raise NotImplementedError
    
    # async def _receive_all(self):
    #     """所有訂閱串流 generator"""
        
    #     tasks = []
    #     for market_type, websocket in self.connections.items():
    #         gen = self._recv_from_connection(market_type, websocket)
    #         task = asyncio.create_task(gen.__anext__())
    #         tasks.append((gen, task))
        
    #     while True:
    #         # 等待任一數據到達
    #         done, _ = await asyncio.wait(
    #             [task for _, task in tasks],
    #             return_when=asyncio.FIRST_COMPLETED
    #         )
            
    #         # 更新任務列表並返回數據
    #         for done_task in done:
    #             for i, (gen, task) in enumerate(tasks):
    #                 if task == done_task:
    #                     try:
    #                         yield await done_task
    #                         # 創建新的任務繼續接收
    #                         tasks[i] = (gen, asyncio.create_task(gen.__anext__()))
    #                     except StopAsyncIteration:
    #                         continue
    
    async def _receive_all(self):
        """所有訂閱串流 generator"""
        while True:
            if not self.connections:
                await asyncio.sleep(1)
                continue

            # 為每個連接創建一個 generator
            generators = {
                market_type: self._recv_from_connection(market_type, ws)
                for market_type, ws in self.connections.items()
            }

            # 為每個 generator 創建初始任務
            pending = {
                asyncio.create_task(gen.__anext__()): (market_type, gen)
                for market_type, gen in generators.items()
            }

            while pending:
                try:
                    # 等待任一任務完成
                    done, _ = await asyncio.wait(
                        pending.keys(),
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    for task in done:
                        market_type, gen = pending.pop(task)
                        try:
                            result = await task
                            if result:  # 如果有數據則 yield
                                yield result
                            # 為這個 generator 創建新的任務
                            pending[asyncio.create_task(gen.__anext__())] = (market_type, gen)
                        except StopAsyncIteration:
                            # generator 結束
                            self.logger.info(f"Generator for {market_type} completed")
                            continue
                        except Exception as e:
                            # 處理其他錯誤
                            self.logger.error(f"Error in {market_type} generator: {str(e)}")
                            # 可以選擇是否要重新添加這個 generator
                            try:
                                pending[asyncio.create_task(gen.__anext__())] = (market_type, gen)
                            except Exception:
                                self.logger.error(f"Failed to restart {market_type} generator")

                except Exception as e:
                    self.logger.error(f"Error in main loop: {str(e)}")
                    await asyncio.sleep(1)  # 避免在錯誤情況下過度循環

        
               
    # async def _receive_all(self):
    #     """所有訂閱串流 generator"""
    #     while True:
    #         if not self.connections:
    #             continue
                
    #         # 為每個連接創建接收協程
    #         receivers = [
    #             self._recv_from_connection(market_type, ws)
    #             for market_type, ws in self.connections.items()
    #         ]
            
    #         try:
    #             # 同時等待所有接收器
    #             async for message in self._merge_generators(receivers):
    #                 yield message
    #         except Exception as e:
    #             self.logger.error(f"Error in _receive_all: {str(e)}")
                        
    # async def _merge_generators(self, generators):
    #     """合併多個異步生成器"""
    #     # 追蹤每個生成器的下一個值
    #     pending = {
    #         asyncio.create_task(gen.__anext__()): gen
    #         for gen in generators
    #     }
        
    #     while pending:
    #         done, _ = await asyncio.wait(
    #             pending.keys(),
    #             return_when=asyncio.FIRST_COMPLETED
    #         )
            
    #         for done_task in done:
    #             gen = pending.pop(done_task)
    #             try:
    #                 result = await done_task
    #                 yield result
    #                 # 為這個生成器創建新的任務
    #                 pending[asyncio.create_task(gen.__anext__())] = gen
    #             except StopAsyncIteration:
    #                 continue
    #             except Exception as e:
    #                 self.logger.error(f"Error in generator: {str(e)}")
    #                 # 如果發生錯誤，嘗試重新添加生成器
    #                 try:
    #                     pending[asyncio.create_task(gen.__anext__())] = gen
    #                 except Exception:
    #                     pass
                        
    async def _send_pong(self, websocket, data):
        pong_message = {"pong": data["ping"]}
        await websocket.send(json.dumps(pong_message))
        self.logger.debug(f"Responded to ping")
                        
    async def _recv_from_connection(self, market_type: str, websocket):
            while True:
                try:
                    while True:
                        try:
                            message = await websocket.recv()
                            data = json.loads(message)
                            if data.get("ping"):
                                await self._send_pong(websocket, data)
                                
                            yield data
                            
                        except websockets.exceptions.ConnectionClosed:
                            self.logger.error(f"{market_type} connection closed")
                            break
                            
                except Exception as e:
                    self.logger.error(f"Error in {market_type} connection: {str(e)}")
                    
                self.logger.info(f"Attempting to reconnect to {market_type}")
                
                if await self.reconnect(market_type):
                    websocket = self.connections[market_type]
                else:
                    self.logger.error(f"Failed to reconnect to {market_type}")