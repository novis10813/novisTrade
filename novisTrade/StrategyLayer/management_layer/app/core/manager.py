# app/core/manager.py
import logging

from typing import Optional, Dict, Any, List

from schemas.strategy import (
    StrategyMetadataCreate,
    StrategyMetadataRuntimeResponse,
    StrategyMetadataDBResponse,
    StrategyStatus,
    StrategyMetadataPatch
)
from app.core.services import strategy_service as services

logger = logging.getLogger(__name__)


async def create_strategy(strategy: StrategyMetadataCreate) -> str:
    """添加新策略
    Args:
        strategy_data (StrategyMetadataCreate): 策略資料
        
    Returns:
        strategy_id (str): 策略 ID
    """
    try:
        # 建立策略並存到 storage 中
        strategy_id = await services.create_strategy(strategy)
    except Exception as e: # TODO: 針對自定義的 exception 進行處理
        raise ValueError(f"Failed to create strategy: {str(e)}")
    
    try:
        # 把建立好的策略載入到 Redis 中
        await services.load_strategy(strategy_id)
    except Exception as e: # TODO: 針對自定義的 exception 進行處理
        # 如果載入策略失敗，則刪除剛剛建立的策略
        try:
            await services.delete_strategy(strategy_id)
        except Exception as e:
            raise ValueError(f"Failed to delete strategy: {str(e)}")
        raise ValueError(f"Failed to load strategy: {str(e)}")
    
    return strategy_id

async def load_strategy(strategy_id: str) -> None:
    """載入策略到 Redis 中
    Args:
        strategy_id (str): 策略 ID
    """
    try:
        await services.load_strategy(strategy_id)
    except Exception as e: # TODO: 針對自定義的 exception 進行處理
        raise ValueError(f"Failed to load strategy: {str(e)}")
    
async def unload_strategy(strategy_id: str) -> None:
    """
    從 Redis 中卸載策略
    Args:
        strategy_id (str): 策略 ID
    """
    try:
        await services.unload_strategy(strategy_id)
    except Exception as e: # TODO: 針對自定義的 exception 進行處理
        raise ValueError(f"Failed to unload strategy: {str(e)}")
        
async def delete_strategy(strategy_id: str) -> bool:
    """刪除策略"""
    try:
        await services.delete_strategy(strategy_id)
    except Exception as e: # TODO: 針對自定義的 exception 進行處理
        raise ValueError(f"Failed to delete strategy: {str(e)}")
    
async def get_runtime_strategies(status: Optional[StrategyStatus] = None) -> List[StrategyMetadataRuntimeResponse]:
    """列出策略
    Args:
        status (StrategyStatus): 策略狀態
        
    Returns:
        List[StrategyMetadataRuntimeResponse]: 策略列表
        
    說明:
        - 如果 status 為 None ，則只會列出所有策略
        - 如果 status 不為 None ，則只會列出符合狀態的策略
    """
    try:
        return await services.get_runtime_strategies(status)
    except Exception as e: # TODO: 針對自定羙的 exception 進行處理
        raise ValueError(f"Failed to list strategies: {str(e)}")
    
async def get_runtime_strategy(strategy_id: str) -> StrategyMetadataRuntimeResponse:
    """列出策略
    Args:
        strategy_id (str): 策略 ID
    """
    try:
        return await services.get_runtime_strategy(strategy_id)
    except Exception as e: # TODO: 針對自定羙的 exception 進行處理
        raise ValueError(f"Failed to list strategy: {str(e)}")
    
async def get_db_strategies() -> List[StrategyMetadataDBResponse]:
    """列出策略
    """
    try:
        return await services.get_db_strategies()
    except Exception as e: # TODO: 針對自定羙的 exception 進行處理
        raise ValueError(f"Failed to list strategies: {str(e)}")
    
async def get_db_strategy(strategy_id: str) -> StrategyMetadataDBResponse:
    """列出策略
    """
    try:
        return await services.get_db_strategy(strategy_id)
    except Exception as e: # TODO: 針對自定羙的 exception 進行處理
        raise ValueError(f"Failed to list strategy: {str(e)}")

async def update_strategy(strategy_id: str, patch_data: StrategyMetadataPatch) -> StrategyMetadataRuntimeResponse:
    """更新策略狀態"""
    try:
        return await services.update_strategy(strategy_id, patch_data)
    except Exception as e: # TODO: 針對自定羙的 exception 進行處理
        raise ValueError(f"Failed to update strategy status: {str(e)}")