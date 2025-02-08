# app/api/v1/strategies.py
import logging

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends

from app.core.manager import StrategyManager
from app.schemas.strategies_pattern import StrategyMetadataWithId, StrategyMetadata
from app.core.dependencies import get_strategy_manager

# app = FastAPI()
router = APIRouter(prefix="/strategies", tags=["strategies"])
manager = StrategyManager()

logger = logging.getLogger(__name__)


@router.post("/")
async def add_strategy(
    strategy: StrategyMetadata,
    manager: StrategyManager = Depends(get_strategy_manager),
) -> Dict[str, Any]:
    logger.debug(f"Received request at /strategies")
    # 生成唯一 ID
    strategy_with_id = StrategyMetadataWithId(**strategy.model_dump())
    strategy_id = strategy_with_id.id

    # 呼叫 manager 來處理策略新增
    result = await manager.create_strategy(strategy_with_id)
    if result == "success":
        return {"message": "Strategy added successfully", "strategy_id": strategy_id}

    # 回傳結果
    return {"message": f"{result}"}


@router.get("/", response_model=List[StrategyMetadataWithId])
def get_all_strategies(
    manager: StrategyManager = Depends(get_strategy_manager),
):
    return manager.get_all_strategies()

@router.get("/{strategy_id}", response_model=StrategyMetadataWithId)
def get_strategy(
    strategy_id: str,
    manager: StrategyManager = Depends(get_strategy_manager),
):
    strategy = manager.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy

@router.patch("/{strategy_id}/pause", response_model=StrategyMetadataWithId)
def pause_strategy(strategy_id: str):
    strategy = manager.pause_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.patch("/{strategy_id}/resume", response_model=StrategyMetadataWithId)
def resume_strategy(strategy_id: str):
    strategy = manager.resume_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.put("/{strategy_id}", response_model=StrategyMetadataWithId)
# def modify_strategy(strategy_id: str, strategy: StrategyUpdate):
#     updated = manager.update_strategy(
#         strategy_id, strategy.model_dump(exclude_unset=True)
#     )
#     if not updated:
#         raise HTTPException(status_code=404, detail="Strategy not found")
#     return updated


@router.delete("/{strategy_id}")
def remove_strategy(strategy_id: str):
    if not manager.remove_strategy(strategy_id):
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"message": "Strategy removed successfully"}

strategies = router