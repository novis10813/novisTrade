import uuid
import logging

from datetime import datetime
from pathlib import Path

from app.settings.config import get_settings
from app.core.repo import strategy_repository as storage
from app.core.dependencies import get_redis_client
from schemas.strategy import StrategyMetadataInDB, StrategyMetadataCreate

settings = get_settings()
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
    storage.save_strategy(db_strategy, STORAGE_PATH)
    return db_strategy.id

async def load_strategy(strategy_id: str):
    """
    從 yaml 文件加載策略到 Redis 內
    """
    try:
        strategy: StrategyMetadataInDB = storage.load_strategy(strategy_id, STORAGE_PATH)
        # 透過 redis_client 把策略載入到 Redis 中
        redis_client = get_redis_client()
        await redis_client.load_strategy(strategy)
    except Exception:
        # 把底層的 exception 往上拋
        raise
