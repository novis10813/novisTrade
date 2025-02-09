# app/core/manager.py
import logging

from typing import List, Optional, Dict, Any

from schemas.strategy import StrategyMetadataCreate
from core.events import EventEmitter

logger = logging.getLogger(__name__)

class StrategyManager:
    def __init__(self):
        self.events = EventEmitter()

    async def create_strategy(self, strategy: StrategyMetadataCreate) -> str:
        """添加新策略
        Args:
            strategy_data (StrategyMetadataCreate): 策略資料
        
        Returns:
            strategy_id (str): 策略 ID
        """
        try:
            # 發送策略創建的事件
            # 接收方: storage.py
            storage_response = await self.events.emit("storage:createStrategy", strategy)
            logger.debug(f"Storage response: {storage_response}")
            if not storage_response.get("success"):
                logger.error(f"Failed to create strategy: {storage_response.get('message')}")
                raise ValueError(storage_response.get("message"))
            
            return storage_response.get("strategy_id")
        
        except Exception as e:
            logger.error(f"Error in create_strategy: {str(e)}")
            raise ValueError(f"Failed to create strategy: {str(e)}")
        
    async def delete_strategy(self, strategy_id: str) -> bool:
        try:
            storage_response = await self.events.emit("storage:deleteStrategy", {"strategy_id": strategy_id})
            logger.debug(f"Storage response: {storage_response}")
            if not storage_response.get("success"):
                logger.error(f"Failed to delete strategy: {storage_response.get('message')}")
                raise ValueError(storage_response.get("message"))
            
            return True
        except Exception as e:
            logger.error(f"Error in delete_strategy: {str(e)}")
            raise ValueError(f"Failed to delete strategy: {str(e)}")
        
    async def load_strategy(self, strategy_id: str):
        """載入策略到 Redis 中
        步驟 1. 先從 storage 中取得策略資料
        步驟 2. 將策略資料存到 Redis 中
        """
        storage_response = await self.events.emit("storage:loadStrategy", {"strategy_id": strategy_id})
        if not storage_response.get("success"):
            logger.error(f"Failed to load strategy: {storage_response.get('message')}")
            raise ValueError(storage_response.get("message"))
        
        strategy_to_load = storage_response.get("strategy")
        redis_response = await self.events.emit("redis:loadStrategy", {"strategy": strategy_to_load})
        if not redis_response.get("success"):
            logger.error(f"Failed to load strategy to Redis: {redis_response.get('message')}")
            raise ValueError(redis_response.get("message"))
        
            
    async def start_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """啟動策略"""
        # 發送訂閱交易對的事件
        # 接收方: redis_queue.py
        # TODO: 這邊我可能會需要寫一個對 MQ 的 interface，這樣就不用直接寫 redis 的東西
        # 但現在先直接用 redis 來寫即可
        
        # 這邊應該放到 "self.start_strategy"
        # data_keys = [dt.key() for dt in strategy.data.types]
        # subscribe_response = await self.events.emit("strategy:subscribed", data_keys)
        # subscribe_response = {
        #     "success": True,
        #     "message": "Subscribed successfully"
        # }
        # if subscribe_response.get("success") == False:
        #     raise Exception(subscribe_response.get("message"))
        pass

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