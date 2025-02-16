# app/core/repo/strategy_repository.py
import yaml
import logging

from pathlib import Path
from typing import List, Optional

from schemas.strategy import StrategyMetadataInDB
# 如果之後使用 DB，可以在 dependencies.py 中定義一個 DB 的 connector，然後在這邊使用

logger = logging.getLogger(__name__)


def create(strategy: StrategyMetadataInDB, storage_path: Path) -> None:
    """保存策略到文件
    Args:
        strategy (StrategyMetadataInDB): 策略數據
        storage_path (Path): 策略存儲路徑
    """
    storage_path.mkdir(parents=True, exist_ok=True)
    strategy_path = storage_path / f"{strategy.id}.yaml"
    with strategy_path.open("w", encoding="utf-8") as f:
        yaml.dump(
            strategy.model_dump(mode="json"),
            f,
            allow_unicode=True,
            default_flow_style=False
        )

def get(strategy_id: Optional[str], storage_path: Path) -> List[StrategyMetadataInDB]:
    """從文件加載策略
    Args:
        strategy_id (str): 策略ID
        storage_path (Path): 策略存儲路徑
    Returns:
        StrategyMetadataInDB: 策略數據
    """
    if strategy_id is None:
        strategies = []
        for strategy_path in storage_path.glob("*.yaml"):
            with strategy_path.open("r", encoding="utf-8") as f:
                strategy_data = yaml.safe_load(f)
                strategies.append(StrategyMetadataInDB(**strategy_data))
        return strategies
    else:
        strategy_path = storage_path / f"{strategy_id}.yaml"
        with strategy_path.open("r", encoding="utf-8") as f:
            strategy_data = yaml.safe_load(f)
            return [StrategyMetadataInDB(**strategy_data)]

def delete(strategy_id: str, storage_path: Path) -> None:
    """刪除策略
    Args:
        strategy_id (str): 策略ID
        storage_path (Path): 策略存儲路徑   
    """
    strategy_path = storage_path / f"{strategy_id}.yaml"
    if strategy_path.exists():
        strategy_path.unlink()
    else:
        raise ValueError(f"Strategy {strategy_id} not found in {storage_path}")