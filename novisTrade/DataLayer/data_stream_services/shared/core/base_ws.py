import json
import asyncio
import logging

from redis.asyncio import Redis
from typing import List, Dict, Set
from collections import defaultdict
from abc import ABC, abstractmethod

from .ws_manager import WebSocketManager

logger = logging.getLogger(__name__)

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
    ):
        self.ws_manager = WebSocketManager()
        self.subscriptions = defaultdict(lambda: defaultdict(int))
        
        self.redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        
    async def _init_redis(self):
        """初始化 Redis 連接"""
        logger.debug("Initializing Redis connection...")
        
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
        logger.debug(f"Listening to control channel: {channel}")
        
    async def start(self):
        
        # 初始化 Redis 連接
        await self._init_redis()
        
        # 啟動 WebSocket 管理器
        self.ws_manager.set_message_callback(self._handle_message)
        self.ws_manager.set_reconnect_callback(self._handle_reconnection)
        await self.ws_manager.start()
        
        # 啟動 Redis 訊息監聽
        try:
            logger.debug("Starting Redis listener...")
            redis_listener = asyncio.create_task(self.start_redis_listener())
            await redis_listener
        except asyncio.CancelledError:
            logger.info("Shutting down...")
            await self.close()
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            await self.close()
        finally:
            await self.close()
            
    async def close(self):
        """關閉 WebSocket 管理器"""
        logger.info("Closing Server...")
        logger.debug("Closing WebSocket connection...")
        await self.ws_manager.close()
        
        # 關閉 Redis 連接
        logger.debug("Closing Redis connection...")
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
    
    def add_subscription(self, streams: List[str], market_type: str) -> None:
        """紀錄每個 market type 的每個 stream 有多少人訂閱"""
        logger.debug(f"subscriptions before: {dict(self.subscriptions)}")
        for stream in streams:
            self.subscriptions[market_type][stream] += 1
            logger.debug(f"Add {stream} to {market_type}, count: {self.subscriptions[market_type][stream]}")
        logger.debug(f"subscriptions after: {dict(self.subscriptions)}")
        return
    
    @abstractmethod
    async def unsubscribe(
        self,
        symbols: List[str],
        stream_type: str,
        market_type: str = "spot",
        request_id: str = "1"
    ) -> bool:
        raise NotImplementedError
    
    def remove_subscription(self, streams: List[str], market_type: str) -> None:
        """紀錄每個 market type 的每個 stream 有多少人訂閱"""
        for stream in streams:
            self.subscriptions[market_type][stream] -= 1
        return
    
    def get_sub_count(self, stream: str, market_type: str) -> int:
        """取得特定 stream 的訂閱數"""
        return self.subscriptions[market_type][stream]
    
    def get_zero_sub_streams(self, market_type: str) -> List[str]:
        """取得沒有訂閱的 stream"""
        return [stream for stream, count in self.subscriptions[market_type].items() if count == 0]
    
    @abstractmethod
    async def _map_format(self, data: dict):
        raise NotImplementedError
    
    async def start_redis_listener(self):
        """啟動 Redis 訊息監聽"""
        try:
            # 使用 aioredis 的 subscribe pattern
            async for message in self.pubsub.listen():
                if message and message["type"] == "message":
                    logger.info(f"Received message: {message}")
                    await self._on_redis_message(message["data"])
        except Exception as e:
            logger.error(f"Error in Redis listener: {str(e)}")
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
                logger.info(
                    f"Subscribe {'success' if success else 'failed'} for {symbols}"
                )

            elif action == "unsubscribe":
                success = await self.unsubscribe(
                    symbols=symbols,
                    stream_type=stream_type,
                    market_type=market_type,
                    request_id=request_id,
                )
                logger.info(
                    f"Unsubscribe {'success' if success else 'failed'} for {symbols}"
                )
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error handling Redis command: {str(e)}")
