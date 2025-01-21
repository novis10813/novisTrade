import json
import logging
import asyncio
import websockets

from abc import ABC, abstractmethod
from typing import List, Union, Optional

from .ws_manager import WebSocketManager

class ExchangeWebSocket(ABC):
    """
    交易所 WebSocket 的基礎類別，負責：
    - 定義交易所共用的介面和方法
    - 使用 WebSocketManager 來管理連線
    - 提供訂閱、取消訂閱等共用功能
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        
        self.ws_manager = WebSocketManager()
        self.connections = {}
        self.subscriptions = {}
        
    async def start(self):
        """啟動 WebSocket 管理器"""
        self.ws_manager.set_message_callback(self._handle_message)
        await self.ws_manager.start()
        
    @abstractmethod
    async def _handle_message(self, connection_id: str, message: str):
        raise NotImplementedError
    
    @abstractmethod
    async def subscribe(
        self,
        streams: Union[str, List[str]],
        market_type: str = "spot",
    ) -> bool:
        raise NotImplementedError
    
    @abstractmethod
    async def unsubscribe(
        self,
        streams: Union[str, List[str]],
        market_type: str = "spot",
    ) -> bool:
        raise NotImplementedError
    
    @abstractmethod
    async def _map_format(self, data: dict):
        raise NotImplementedError
    
    async def close(self):
        """關閉 WebSocket 管理器"""
        await self.ws_manager.close()