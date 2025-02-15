import logging

from datetime import datetime
from redis.asyncio import Redis
from app.schemas.strategy import StrategyMetadataInDB, StrategyStatus, StrategyMetadataPatch

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self, redis_host: str, redis_port: int, redis_db: int):
        self.redis = Redis.from_url(f"redis://{redis_host}:{redis_port}/{redis_db}")
        
    
    async def load_strategy(self, strategy: StrategyMetadataInDB) -> None:
        """
        Load Strategy to Redis
        """
        #TODO: 需要自定義 exception
        try:
            key = f"strategy:{strategy.id}"
            
            strategy.status = StrategyStatus.created
            strategy.updated_at = datetime.now()
            await self.redis.set(key, strategy.model_dump_json())
        except Exception as e:
            raise e
        
