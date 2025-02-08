# app/core/strategy_store.py
import yaml
import logging

from threading import RLock
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from .events import EventEmitter
from ..schemas.strategies_pattern import StrategyMetadataWithId

logger = logging.getLogger(__name__)

class StrategyStore:
    """
    線程安全的策略存儲類
    使用 RLock 確保對策略數據的並發訪問安全
    """
    def __init__(self, storage_path: Path = Path("strategies")):
        self.events = EventEmitter()
        self._strategies: Dict[str, StrategyMetadataWithId] = {}
        self._storage_path = storage_path
        self._lock = RLock()
        
        self._load_strategies()
        # 註冊需要監聽的事件
        # self.events.on("strategy:get_all_strategies", self._get_all_strategies)
        # self.events.on("strategy:get_strategy", self._handle)
        self.events.on("strategy:create", self._create_strategy)
        # self.events.on("strategy:subscribed")

    def _load_strategies(self):
        """載入所有策略文件"""
        for strategy_file in self._storage_path.glob("*.yaml"):
            with strategy_file.open("r", encoding="utf-8") as f:
                strategy_data = yaml.safe_load(f)
                self._strategies[strategy_data["id"]] = StrategyMetadataWithId(**strategy_data)

    async def _create_strategy(self, event_data: Dict[str, Union[StrategyMetadataWithId, str]]) -> Dict[str, str]:
        """建立新策略
        Args:
            event_data (Dict[str, StrategyMetadataWithId]): 策略數據
        """
        response_event = event_data.get("response_event")
        logger.info(f"Creating strategy: {event_data}")
        with self._lock:
            try:
                strategy = event_data.get("data")
                self._strategies[strategy.id] = strategy
                await self._save_strategy(strategy)
                message = {
                    "success": True,
                    "message": "Strategy added successfully"
                }
            except Exception as e:
                message = {
                    "success": False,
                    "message": f"failed: {str(e)}"
                }
            await self.events.emit_response(response_event, message)
            
    async def _save_strategy(self, strategy: StrategyMetadataWithId) -> None:
        """保存策略到文件
        Args:
            strategy (StrategyMetadataWithId): 策略數據
        """
        strategy_path = self._storage_path / f"{strategy.id}.yaml"
        with strategy_path.open("w", encoding="utf-8") as f:
            yaml.dump(
                strategy.model_dump(),
                f,
                allow_unicode=True,
                default_flow_style=False
            )
        
    # async def _get_all_strategies(self, event_data: Dict[str, Any]):
    #     response_event = event_data.get("response_event")
    #     with self._lock:
    #         strategies = list(self._strategies.values())
    #     await self.events.emit(response_event, strategies)
    
    # def get_all(self) -> List[StrategyMetadataWithId]:
    #     with self._lock:
    #         return list(self._strategies.values())
    
    # def update(self, strategy_id: str, updates: Dict[str, Any]) -> Optional[StrategyMetadataWithId]:
    #     with self._lock:
    #         if strategy_id not in self._strategies:
    #             return None
    #         strategy = self._strategies[strategy_id]
    #         updated_data = strategy.model_dump(mode="json")
    #         updated_data.update(updates)
    #         updated_data["updated_at"] = datetime.now()
    #         updated_strategy = StrategyMetadataWithId(**updated_data)
    #         self._strategies[strategy_id] = updated_strategy
    #         return updated_strategy
    
    # def remove(self, strategy_id: str) -> bool:
    #     with self._lock:
    #         if strategy_id in self._strategies:
    #             del self._strategies[strategy_id]
    #             return True
    #         return False