import uuid

from datetime import datetime
from pathlib import Path

from schemas.strategy import StrategyMetadataInDB, StrategyMetadataCreate
from app.core.repo import strategy_repository as storage
from app.settings.config import get_settings

settings = get_settings()
STORAGE_PATH: Path = settings.storage_path

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
    storage.save_strategy(db_strategy, STORAGE_PATH)
    return db_strategy.id

async def load_strategy(strategy_id: str) -> StrategyMetadataInDB:
    """
    從 yaml 文件加載策略到 Redis 內
    """
    return storage.load_strategy(strategy_id, STORAGE_PATH)

async def unload_strategy(strategy_id: str) -> bool:
    """
    從 Redis 中卸載策略
    """
    pass

async def delete_strategy(strategy_id: str) -> bool:
    """
    刪除策略
    """
    pass

