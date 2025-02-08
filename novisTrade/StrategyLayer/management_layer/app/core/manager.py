# app/core/manager.py
import logging

from typing import List, Optional, Dict, Any

from ..schemas.strategies_pattern import StrategyMetadata, StrategyMetadataWithId
from .events import EventEmitter

logger = logging.getLogger(__name__)

class StrategyManager:
    def __init__(self):
        self.events = EventEmitter()
        
        # 註冊需要回應的事件
        # self.events.on("")
        # self.events.on("storage:get_all_strategies", self._handle_get_all_strategies)
        # self.events.on("storage:get_strategy", self._handle_get_strategy)

    async def create_strategy(self, strategy: StrategyMetadataWithId) -> Dict[str, str]:
        """添加新策略
        Args:
            strategy_data (Dict[str, Any]): 策略資料
        
        Returns:
            {
                "message": "Strategy added successfully",
                "strategy_id": "strategy_id"
            }
        """
        try:
            # 發送策略創建的事件
            # 接收方: storage.py
            storage_response = await self.events.emit("strategy:create", strategy)
            logger.info(f"Storage response: {storage_response}")
            if storage_response.get("success") == False:
                logger.debug(f"Failed to create strategy: {storage_response.get('message')}")
                raise Exception(storage_response.get("message"))
            
            # 發送訂閱交易對的事件
            # 接收方: redis.py
            # TODO: 這邊我可能會需要寫一個對 MQ 的 interface，這樣就不用直接寫 redis 的東西
            data_keys = [dt.key() for dt in strategy.data.types]
            # subscribe_response = await self.events.emit("strategy:subscribed", data_keys)
            subscribe_response = {
                "success": True,
                "message": "Subscribed successfully"
            }
            if subscribe_response.get("success") == False:
                raise Exception(subscribe_response.get("message"))
            
            return {
                "message": "Strategy added successfully",
                "strategy_id": strategy.id
            }
        except Exception as e:
            return {
                "message": f"failed: {str(e)}",
                "strategy_id": ""
            }

    # async def get_all_strategies(self) -> List[StrategyMetadataWithId]:
    #     """列出所有策略"""
    #     return await self.events.emit("strategy:get_all_strategies", {}, wait_response=True)
    
    # async def _handle_get_all_strategies(self, response_data: Dict[str, Any]) -> List[StrategyMetadataWithId]:
    #     strategies = response_data.get("data", [])
    #     return strategies

    # async def get_strategy(self, strategy_id: str) -> Optional[StrategyMetadataWithId]:
    #     """獲取特定策略"""
    #     strategy = await self.events.emit("strategy:get_strategy", {"strategy_id": strategy_id}, wait_response=True)
    #     return strategy
    
    # async def _handle_get_strategy(self, response_data: Dict[str, Any]) -> Optional[StrategyMetadataWithId]:
    #     strategy = response_data.get("data")
    #     return strategy

    # def update_strategy(
    #     self, strategy_id: str, updates: Dict[str, Any]
    # ) -> Optional[StrategyMetadataWithId]:
    #     """更新策略參數"""
    #     pass

    # def pause_strategy(self, strategy_id: str) -> Optional[StrategyMetadata]:
    #     """暫停策略"""
    #     pass

    # def resume_strategy(self, strategy_id: str) -> Optional[StrategyMetadata]:
    #     """恢復策略"""
    #     # return self._store.update(strategy_id, {"status": StrategyStatus.ACTIVE})
    #     pass

    # def remove_strategy(self, strategy_id: str) -> bool:
    #     """移除策略"""
    #     # return self._store.remove(strategy_id)
    #     pass