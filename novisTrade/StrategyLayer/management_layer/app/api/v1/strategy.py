# app/api/v1/strategies.py
import logging

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Query

from app.schemas.strategy import (
    StrategyMetadataCreate,
    StrategyMetadataCreateResponse,
    StrategyMetadataRuntimeSummary,
    StrategyMetadataRuntimeResponse,
    StrategyMetadataDBSummary,
    StrategyMetadataDBResponse,
    StrategyStatus
)
from app.core import manager

router = APIRouter(prefix="/strategies", tags=["strategies"])

logger = logging.getLogger(__name__)


@router.post(
    "/",
    response_model=StrategyMetadataCreateResponse,
    status_code=status.HTTP_201_CREATED,
    response_description="Create a new strategy"
)
async def create_strategy(
    strategy: StrategyMetadataCreate,
):
    try:
        # 呼叫 manager 來處理策略新增
        strategy_id = await manager.create_strategy(strategy)
        return StrategyMetadataCreateResponse(
            message="Strategy added successfully",
            id=strategy_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{str(e)}"
        )
    
# get runtime strategies
@router.get(
    "/runtime",
    response_model=List[StrategyMetadataRuntimeSummary],
    status_code=status.HTTP_202_ACCEPTED,
    response_description="Get strategies"
)
async def get_runtime_strategies(
    status: Optional[StrategyStatus] = Query(None, description="Status of the strategy")
):
    try:
        return await manager.get_runtime_strategies(status)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")
    
@router.get(
    "/runtime/{strategy_id}",
    response_model=StrategyMetadataRuntimeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    response_description="Get strategy"
)
async def get_runtime_strategy(strategy_id: str):
    try:
        return await manager.get_runtime_strategy(strategy_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")
    
@router.get(
    "/db",
    response_model=List[StrategyMetadataDBSummary],
    status_code=status.HTTP_202_ACCEPTED,
    response_description="Get strategies"
)
async def get_db_strategies():
    """
    列出在 db 中的所有策略
    TODO: 之後可以用 created_at 和 updated_at 來排序和 query
    """
    try:
        return await manager.get_db_strategies()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")
    
@router.get(
    "/db/{strategy_id}",
    response_model=StrategyMetadataDBResponse,
    status_code=status.HTTP_202_ACCEPTED,
    response_description="Get strategy"
)
async def get_db_strategy(strategy_id: str):
    try:
        return await manager.get_db_strategy(strategy_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")
        
# @router.get("/", response_model=List[StrategyMetadataWithId])
# def get_all_strategies(
#     manager: StrategyManager = Depends(get_strategy_manager),
# ):
#     return manager.get_all_strategies()

# @router.get("/{strategy_id}", response_model=StrategyMetadataWithId)
# def get_strategy(
#     strategy_id: str,
#     manager: StrategyManager = Depends(get_strategy_manager),
# ):
#     strategy = manager.get_strategy(strategy_id)
#     if not strategy:
#         raise HTTPException(status_code=404, detail="Strategy not found")
#     return strategy

# @router.patch("/{strategy_id}/pause", response_model=StrategyMetadataWithId)
# def pause_strategy(strategy_id: str):
#     strategy = manager.pause_strategy(strategy_id)
#     if not strategy:
#         raise HTTPException(status_code=404, detail="Strategy not found")
#     return strategy


# @router.patch("/{strategy_id}/resume", response_model=StrategyMetadataWithId)
# def resume_strategy(strategy_id: str):
#     strategy = manager.resume_strategy(strategy_id)
#     if not strategy:
#         raise HTTPException(status_code=404, detail="Strategy not found")
#     return strategy


# @router.put("/{strategy_id}", response_model=StrategyMetadataWithId)
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