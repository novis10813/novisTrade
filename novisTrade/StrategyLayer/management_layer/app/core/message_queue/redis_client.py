from redis.asyncio import Redis

from ..events import EventEmitter


class RedisClient:
    def __init__(self, redis_host: str, redis_port: int, redis_db: int):
        self.redis = Redis.from_url(f"redis://{redis_host}:{redis_port}/{redis_db}")
        self.events = EventEmitter()
        
        # 這邊只負責把 StrategyMetadata 放在 redis 上
        # 其他的控制都交給其他層去處理
        self.events.on("redis:loadStrategy", self._load_strategy)
        self.events.on("redis:activateStrategy", self._activate_strategy)
        self.events.on("redis:deactivateStrategy", self._deactivate_strategy)
        pass
    
    async def _load_strategy(self, strategy_id: str):
        """
        Load Strategy to Redis
        """
        pass
    
    async def _activate_strategy(self, strategy_id: str):
        """
        Change Strategy Status to Active
        """
        pass
    
    async def _deactivate_strategy(self, strategy_id: str):
        """
        Change Strategy Status to Inactive
        """
        pass