# app/core/strategy_store.py
import yaml
import uuid
import logging

from threading import RLock
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from core.events import EventEmitter
from schemas.strategy import StrategyMetadataInDB, StrategyMetadataCreate

logger = logging.getLogger(__name__)

class StrategyStore:
    """
    線程安全的策略存儲類
    使用 RLock 確保對策略數據的並發訪問安全
    """
    def __init__(self, storage_path: Path = Path("strategies")):
        self.events = EventEmitter()
        self._strategies: Dict[str, StrategyMetadataInDB] = {}
        self._storage_path = storage_path
        self._lock = RLock()
        
        # 註冊需要監聽的事件
        # self.events.on("strategy:get_all_strategies", self._get_all_strategies)
        # self.events.on("strategy:get_strategy", self._handle)
        self.events.on("storage:createStrategy", self._create_strategy)
        self.events.on("storage:loadStrategy", self._load_strategy)
        # self.events.on("strategy:subscribed")

    # def _load_strategies(self):
    #     """載入所有策略文件"""
    #     self._storage_path.mkdir(parents=True, exist_ok=True)
    #     for strategy_file in self._storage_path.glob("*.yaml"):
    #         with strategy_file.open("r", encoding="utf-8") as f:
    #             strategy_data = yaml.safe_load(f)
    #             self._strategies[strategy_data["id"]] = StrategyMetadataInDB(**strategy_data)

    async def _create_strategy(self, event_data: Dict[str, Union[StrategyMetadataCreate, str]]) -> None:
        """建立新策略
        Args:
            event_data (Dict[str, StrategyMetadataWithId]): 策略數據
        """
        response_event = event_data.get("response_event")
        logger.debug(f"Creating strategy: {event_data}")
        with self._lock:
            try:
                self._storage_path.mkdir(parents=True, exist_ok=True)
                strategy = event_data.get("data")
                db_strategy = StrategyMetadataInDB(
                    **strategy.model_dump(),
                    id=str(uuid.uuid4()),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self._strategies[db_strategy.id] = db_strategy
                await self._save_strategy(db_strategy)
                message = {
                    "success": True,
                    "strategy_id": db_strategy.id,
                    "message": "Strategy added successfully"
                }
            except Exception as e:
                message = {
                    "success": False,
                    "message": f"{str(e)}"
                }
            await self.events.emit_response(response_event, message)
            
    async def _load_strategy(self, event_data: Dict[str, str]) -> None:
        """
        從檔案讀取策略，並把策略載入到 Redis 中
        """
        response_event = event_data.get("response_event")
        try:
            strategy_id = event_data.get("strategy_id")
            strategy_path = self._storage_path / f"{strategy_id}.yaml"
            if not strategy_path.exists():
                await self.events.emit_response(response_event, {"success": False, "message": "Strategy not found"})
                return
            
            with strategy_path.open("r", encoding="utf-8") as f:
                strategy_data = yaml.safe_load(f)
                strategy = StrategyMetadataInDB(**strategy_data)
                await self.events.emit_response(response_event, {"success": True, "strategy": strategy.model_dump()})

        except Exception as e:
            await self.events.emit_response(response_event, {"success": False, "message": f"{str(e)}"})
            
    async def _save_strategy(self, strategy: StrategyMetadataInDB) -> None:
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
    
    # def update(self, id: str, updates: Dict[str, Any]) -> Optional[StrategyMetadataWithId]:
    #     with self._lock:
    #         if id not in self._strategies:
    #             return None
    #         strategy = self._strategies[id]
    #         updated_data = strategy.model_dump(mode="json")
    #         updated_data.update(updates)
    #         updated_data["updated_at"] = datetime.now()
    #         updated_strategy = StrategyMetadataWithId(**updated_data)
    #         self._strategies[id] = updated_strategy
    #         return updated_strategy
    
    # def remove(self, id: str) -> bool:
    #     with self._lock:
    #         if id in self._strategies:
    #             del self._strategies[id]
    #             return True
    #         return False