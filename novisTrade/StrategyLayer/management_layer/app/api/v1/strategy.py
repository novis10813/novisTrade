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
    StrategyStatus,
    StrategyMetadataPatch
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
    strategy_status: Optional[StrategyStatus] = Query(None, description="Status of the strategy")
):
    try:
        return await manager.get_runtime_strategies(strategy_status)
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
    "/",
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
    "/{strategy_id}",
    response_model=StrategyMetadataDBResponse,
    status_code=status.HTTP_202_ACCEPTED,
    response_description="Get strategy"
)
async def get_db_strategy(strategy_id: str):
    try:
        return await manager.get_db_strategy(strategy_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")
    
# unload strategy from redis
@router.post(
    "/{strategy_id}/unload",
    status_code=status.HTTP_202_ACCEPTED,
    response_description="Unload strategy"
)
async def unload_strategy(strategy_id: str):
    try:
        return await manager.unload_strategy(strategy_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")

@router.delete(
    "/{strategy_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_description="Delete strategy"
)
async def delete_strategy(strategy_id: str):
    try:
        return await manager.delete_strategy(strategy_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")

@router.patch(
    "/{strategy_id}",
    response_model=StrategyMetadataRuntimeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    response_description="Update strategy"
)
async def update_strategy(strategy_id: str, patch_data: StrategyMetadataPatch):
    try:
        return await manager.update_strategy(strategy_id, patch_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")
    
@router.patch(
    "/{strategy_id}/activate",
    response_model=StrategyMetadataRuntimeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    response_description="activate strategy"
)
async def activate_strategy(strategy_id: str):
    try:
        patch_data = StrategyMetadataPatch(status=StrategyStatus.active)
        return await manager.update_strategy(strategy_id, patch_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")

@router.patch(
    "/{strategy_id}/pause",
    response_model=StrategyMetadataRuntimeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    response_description="pause strategy"
)
async def pause_strategy(strategy_id: str):
    try:
        patch_data = StrategyMetadataPatch(status=StrategyStatus.paused)
        return await manager.update_strategy(strategy_id, patch_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")

@router.patch(
    "/{strategy_id}/resume",
    response_model=StrategyMetadataRuntimeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    response_description="resume strategy"
)
async def resume_strategy(strategy_id: str):
    try:
        patch_data = StrategyMetadataPatch(status=StrategyStatus.active)
        return await manager.update_strategy(strategy_id, patch_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")

@router.patch(
    "/{strategy_id}/deactivate",
    response_model=StrategyMetadataRuntimeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    response_description="deactivate strategy"
)
async def deactivate_strategy(strategy_id: str):
    try:
        patch_data = StrategyMetadataPatch(status=StrategyStatus.inactive)
        return await manager.update_strategy(strategy_id, patch_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")


strategies = router