import uuid
import logging

from typing import List, Optional
from pathlib import Path
from datetime import datetime

from app.settings.config import get_settings
from app.core.dependencies import get_redis_client
from app.core.repo import strategy_repository as storage
from schemas.strategy import (
    StrategyMetadataInDB,
    StrategyMetadataCreate,
    StrategyMetadataRuntimeResponse,
    StrategyMetadataDBResponse,
    StrategyStatus,
    StrategyMetadataPatch
)

settings = get_settings()
redis_client = get_redis_client()
STORAGE_PATH: Path = settings.storage_path

logger = logging.getLogger(__name__)

async def create_strategy(strategy: StrategyMetadataCreate) -> str:
    """
    創建新策略
    """
    db_strategy = StrategyMetadataInDB(
        **strategy.model_dump(),
        id=str(uuid.uuid4()),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    storage.create(db_strategy, STORAGE_PATH)
    return db_strategy.id

async def load_strategy(strategy_id: str):
    """
    從 yaml 文件加載策略到 Redis 內
    """
    try:
        strategy = storage.get(strategy_id, STORAGE_PATH)
        if len(strategy) == 0:
            raise ValueError("策略不存在")
        # 透過 redis_client 把策略載入到 Redis 中
        await redis_client.create(strategy[0])
    except Exception:
        # 把底層的 exception 往上拋
        raise
    
async def unload_strategy(strategy_id: str) -> bool:
    """
    從 Redis 中移除策略
    """
    try:
        await redis_client.delete(strategy_id)
    except Exception:
        raise

async def delete_strategy(strategy_id: str) -> bool:
    """
    刪除策略
    """
    try:
        storage.delete(strategy_id, STORAGE_PATH)
    except Exception:
        raise
    
async def get_runtime_strategies(status: Optional[StrategyStatus] = None) -> List[StrategyMetadataRuntimeResponse]:
    """
    列出在 Redis 中的所有策略
    """
    try:
        strategies = await redis_client.get(status=status)
        return [StrategyMetadataRuntimeResponse(**strategy.model_dump()) for strategy in strategies]
    except Exception:
        raise
    
async def get_runtime_strategy(strategy_id: str) -> StrategyMetadataRuntimeResponse:
    """
    列出 Redis 中的指定策略
    """
    try:
        strategy_list = await redis_client.get(strategy_id=strategy_id)
        if len(strategy_list) == 0:
            raise ValueError("策略不存在")
        strategy = strategy_list[0]
        return StrategyMetadataRuntimeResponse(**strategy.model_dump())
    except Exception:
        raise
    
async def get_db_strategies() -> List[StrategyMetadataDBResponse]:
    """
    列出在 db 中的所有策略
    """
    try:
        strategies = storage.get(None, STORAGE_PATH)
        return [StrategyMetadataDBResponse(**strategy.model_dump()) for strategy in strategies]
    except Exception:
        raise
    
async def get_db_strategy(strategy_id: str) -> StrategyMetadataDBResponse:
    """
    列出 db 中的指定策略
    """
    try:
        strategy = storage.get(strategy_id, STORAGE_PATH)
        if len(strategy) == 0:
            raise ValueError("策略不存在")
        return StrategyMetadataDBResponse(**strategy[0].model_dump())
    except Exception:
        raise
    
async def update_strategy(strategy_id: str, patch_data: StrategyMetadataPatch) -> StrategyMetadataRuntimeResponse:
    """
    更新策略
    """
    try:
        await redis_client.update(strategy_id, patch=patch_data)
        updated_strategy = await redis_client.get(strategy_id=strategy_id)
        return StrategyMetadataRuntimeResponse(**updated_strategy[0].model_dump())
    except Exception:
        raise