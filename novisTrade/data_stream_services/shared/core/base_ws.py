import json
import asyncio
import logging

from redis.asyncio import Redis
from typing import List, Dict, Set
from abc import ABC, abstractmethod

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
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        logging_level: int = logging.INFO
    ):
        self.ws_manager = WebSocketManager()
        self.connections = {}
        self.subscriptions: Dict[str, Set] = {}
        
        self.redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        self.logging_level = logging_level
        
    def _init_logger(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(self.logging_level)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        
    async def _init_redis(self):
        """初始化 Redis 連接"""
        # 建立非同步的 Redis 連接
        self.redis_producer = await Redis.from_url(
            self.redis_url,
            decode_responses=True
        )
        self.redis_subscriber = await Redis.from_url(
            self.redis_url,
            decode_responses=True
        )
        self.pubsub = self.redis_subscriber.pubsub()
        
        channel = f"{self.__class__.__name__.lower()[:-9]}:control"
        await self.pubsub.subscribe(channel)
        self.logger.debug(f"Listening to control channel: {channel}")
        
    async def start(self):
        # 初始化 logger
        self._init_logger()
        
        # 初始化 Redis 連接
        await self._init_redis()
        
        # 啟動 WebSocket 管理器
        self.ws_manager.set_message_callback(self._handle_message)
        self.ws_manager.set_reconnect_callback(self._handle_reconnection)
        await self.ws_manager.start()
        
        # 啟動 Redis 訊息監聽
        try:
            redis_listener = asyncio.create_task(self.start_redis_listener())
            await redis_listener
        except asyncio.CancelledError:
            self.logger.info("Shutting down...")
            await self.close()
        except Exception as e:
            self.logger.error(f"Error occurred: {str(e)}")
            await self.close()
        finally:
            await self.close()
            
    async def close(self):
        """關閉 WebSocket 管理器"""
        await self.ws_manager.close()
        
        # 關閉 Redis 連接
        await self.pubsub.unsubscribe()
        await self.pubsub.close()
        await self.redis_subscriber.close()
        await self.redis_producer.close()
        
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
    
    async def start_redis_listener(self):
        """啟動 Redis 訊息監聽"""
        try:
            # 使用 aioredis 的 subscribe pattern
            async for message in self.pubsub.listen():
                if message and message["type"] == "message":
                    await self._on_redis_message(message["data"])
        except Exception as e:
            self.logger.error(f"Error in Redis listener: {str(e)}")
            # 重試機制
            await asyncio.sleep(1)
            
    async def _on_redis_message(self, event: str):
        """處理 Redis 訊息"""
        try:
            command = json.loads(event)
            action = command.get("action")
            symbols = command.get("symbols")
            stream_type = command.get("streamType")
            market_type = command.get("marketType")
            request_id = command.get("requestId")

            if action == "subscribe":
                success = await self.subscribe(
                    symbols=symbols,
                    stream_type=stream_type,
                    market_type=market_type,
                    request_id=request_id,
                )
                self.logger.info(
                    f"Subscribe {'success' if success else 'failed'} for {symbols}"
                )

            elif action == "unsubscribe":
                success = await self.unsubscribe(
                    symbols=symbols,
                    stream_type=stream_type,
                    market_type=market_type,
                    request_id=request_id,
                )
                self.logger.info(
                    f"Unsubscribe {'success' if success else 'failed'} for {symbols}"
                )
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding JSON: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error handling Redis command: {str(e)}")
