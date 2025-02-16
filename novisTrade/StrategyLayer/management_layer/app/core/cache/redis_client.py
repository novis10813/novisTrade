import logging
from typing import List, Optional
from datetime import datetime
from redis.asyncio import Redis
from app.schemas.strategy import StrategyMetadataInDB, StrategyStatus, StrategyMetadataPatch, StrategyMetadataRuntime

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self, redis_host: str, redis_port: int, redis_db: int):
        self.redis = Redis.from_url(f"redis://{redis_host}:{redis_port}/{redis_db}")
        
    
    async def create(self, strategy: StrategyMetadataInDB) -> None:
        """
        載入策略到 Redis
        """
        #TODO: 需要自定義 exception
        try:
            key = f"strategy:{strategy.id}"
            strategy_runtime = StrategyMetadataRuntime(
                **strategy.model_dump(),
                status=StrategyStatus.inactive
            )
            await self.redis.set(key, strategy_runtime.model_dump_json())
        except Exception as e:
            raise e
        
    async def delete(self, strategy_id: str) -> None:
        """
        從 Redis 中移除策略
        """
        try:
            key = f"strategy:{strategy_id}"
            await self.redis.delete(key)
        except Exception as e:
            raise e
        
    async def update(self, strategy_id: str, patch: StrategyMetadataPatch) -> None:
        """
        更新策略
        """
        try:
            key = f"strategy:{strategy_id}"
            raw_data = await self.redis.get(key)
            if raw_data is None:
                raise ValueError(f"Strategy {strategy_id} not found")
            
            strategy = StrategyMetadataRuntime.model_validate_json(raw_data)
            
            update_strategy = strategy.model_copy(
                update=patch.model_dump(exclude_unset=True)
            )
            await self.redis.set(key, update_strategy.model_dump_json())
        except Exception as e:
            raise e
    
    async def get(self, status: Optional[StrategyStatus] = None, strategy_id: Optional[str] = None) -> List[StrategyMetadataRuntime]:
        """
        列出所有策略
        Args:
            status (StrategyStatus): 策略狀態，預設為 None
            
        TODO: 除了 status 以外應該還可以有其他的 query key
        """
        try:
            keys = await self.redis.keys("strategy:*")
            # 先把 Redis 中的所有策略列出來
            strategies = [StrategyMetadataRuntime.model_validate_json(await self.redis.get(key)) for key in keys]
            if strategy_id:
                strategies = [strategy for strategy in strategies if strategy.id == strategy_id]
            elif status:
                strategies = [strategy for strategy in strategies if strategy.status == status]
            return strategies
        except Exception as e:
            raise e
