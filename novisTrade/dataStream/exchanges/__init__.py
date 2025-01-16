from .exchange_factory import ExchangeWebSocketFactory
from .binance_ws import BinanceWebSocket

ExchangeWebSocketFactory.register("binance", BinanceWebSocket)