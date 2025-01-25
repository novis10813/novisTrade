import logging

from abc import ABC, abstractmethod
from typing import List, Dict, Set

from .ws_manager import WebSocketManager

class ExchangeWebSocket(ABC):
    """
    交易所 WebSocket 的基礎類別，負責：
    - 定義交易所共用的介面和方法
    - 使用 WebSocketManager 來管理連線
    - 提供訂閱、取消訂閱等共用功能
    
    TODO:
    - _handle_delay: 利用 heartbeat 來統計延遲的 callback 介面
    - parse_subscription_message: 把通用格式轉換成交易所的指定格式
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        
        self.ws_manager = WebSocketManager()
        self.connections = {}
        self.subscriptions: Dict[str, Set] = {}
        
    async def start(self):
        """啟動 WebSocket 管理器"""
        self.ws_manager.set_message_callback(self._handle_message)
        self.ws_manager.set_reconnect_callback(self._handle_reconnection)
        await self.ws_manager.start()
        
    @abstractmethod
    async def _handle_message(self, connection_id: str, message: str):
        raise NotImplementedError
    
    @abstractmethod
    async def _handle_reconnection(self, connection_id: str):
        raise NotImplementedError
    
    @abstractmethod
    async def subscribe(
        self,
        symbols: List[str],
        stream_type: str,
        market_type: str = "spot",
        request_id: str = "1"
    ) -> bool:
        raise NotImplementedError
    
    @abstractmethod
    async def unsubscribe(
        self,
        symbols: List[str],
        stream_type: str,
        market_type: str = "spot",
        request_id: str = "1"
    ) -> bool:
        raise NotImplementedError
    
    @abstractmethod
    async def _map_format(self, data: dict):
        raise NotImplementedError
    
    async def close(self):
        """關閉 WebSocket 管理器"""
        await self.ws_manager.close()
        
    def is_subscribed(self, symbols, stream_type, market_type) -> List[str]:
        """回傳沒有訂閱的 symbols
        subscriptions 的格式如下:
        self.subscriptions[market_type].add(f"{symbol}@{stream_type}")
        1. 透過 subscriptions 取得已經訂閱的 symbols
        2. 如果 symbols 沒有對應的 stream_type，則回傳該 symbol
        """
        not_subscribed = []
        if market_type not in self.subscriptions:
            return symbols
        
        for symbol in symbols:
            if f"{symbol}@{stream_type}" not in self.subscriptions.get(market_type, set()):
                not_subscribed.append(symbol)
        
        return not_subscribed