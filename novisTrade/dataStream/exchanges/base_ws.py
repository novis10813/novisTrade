from abc import ABC, abstractmethod

class ExchangeWebSocket(ABC):
    @abstractmethod
    async def connect(self):
        pass
        
    # @abstractmethod
    # async def disconnect(self):
    #     pass
        
    @abstractmethod
    async def subscribe(self, symbol: str, stream_type: str):
        pass
        
    @abstractmethod
    async def receive_messages(self):
        pass