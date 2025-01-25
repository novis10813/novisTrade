from .exchange_factory import ExchangeWebSocketFactory
from .binance_ws import BinanceWebSocket
from .kraken_ws import KrakenWebSocket

ExchangeWebSocketFactory.register("binance", BinanceWebSocket)
ExchangeWebSocketFactory.register("kraken", KrakenWebSocket)