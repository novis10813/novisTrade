# strategy_store.py
from datetime import datetime
from typing import Dict, List, Optional, Any


from threading import RLock
from models import StrategyMetadata

class StrategyStore:
    """
    線程安全的策略存儲類
    使用 RLock 確保對策略數據的並發訪問安全
    """
    def __init__(self):
        self._strategies: Dict[str, StrategyMetadata] = {}
        self._lock = RLock()
    
    def add(self, strategy: StrategyMetadata) -> None:
        with self._lock:
            if strategy.id in self._strategies:
                raise ValueError(f"Strategy with id {strategy.id} already exists")
            self._strategies[strategy.id] = strategy
    
    def get(self, strategy_id: str) -> Optional[StrategyMetadata]:
        with self._lock:
            return self._strategies.get(strategy_id)
    
    def list_all(self) -> List[StrategyMetadata]:
        with self._lock:
            return list(self._strategies.values())
    
    def update(self, strategy_id: str, updates: Dict[str, Any]) -> Optional[StrategyMetadata]:
        with self._lock:
            if strategy_id not in self._strategies:
                return None
            strategy = self._strategies[strategy_id]
            updated_data = strategy.model_dump(mode="json")
            updated_data.update(updates)
            updated_data["updated_at"] = datetime.now()
            updated_strategy = StrategyMetadata(**updated_data)
            self._strategies[strategy_id] = updated_strategy
            return updated_strategy
    
    def remove(self, strategy_id: str) -> bool:
        with self._lock:
            if strategy_id in self._strategies:
                del self._strategies[strategy_id]
                return True
            return False