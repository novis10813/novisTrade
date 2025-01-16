from typing import Dict, Type

from .base_ws import ExchangeWebSocket

class ExchangeWebSocketFactory:
    _registry: Dict[str, Type[ExchangeWebSocket]] = {}
    
    @classmethod
    def register(cls, exchange_name: str, exchange_ws: Type[ExchangeWebSocket]):
        cls._registry[exchange_name.lower()] = exchange_ws
        
    @classmethod
    def create(cls, exchange_name: str) -> ExchangeWebSocket:
        exchange_class = cls._registry.get(exchange_name.lower())
        if not exchange_class:
            raise ValueError(f"Exchange {exchange_name} not supported")
        return exchange_class()
    
    @classmethod
    def get_supported_exchanges(cls):
        return list(cls._registry.keys())