# manager.py
from typing import List, Optional, Dict, Any
from models import StrategyMetadata, StrategyStatus, StrategyCreate, StrategyUpdate
from strategy_store import StrategyStore
from datetime import datetime

class StrategyManager:
    def __init__(self):
        self._store = StrategyStore()
    
    def add_strategy(self, strategy_data: Dict[str, Any]) -> StrategyMetadata:
        """添加新策略"""
        strategy = StrategyMetadata(**strategy_data)
        self._store.add(strategy)
        return strategy
    
    def list_strategies(self) -> List[StrategyMetadata]:
        """列出所有策略"""
        return self._store.list_all()
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategyMetadata]:
        """獲取特定策略"""
        return self._store.get(strategy_id)
    
    def update_strategy(self, strategy_id: str, updates: Dict[str, Any]) -> Optional[StrategyMetadata]:
        """更新策略參數"""
        return self._store.update(strategy_id, updates)
    
    def pause_strategy(self, strategy_id: str) -> Optional[StrategyMetadata]:
        """暫停策略"""
        return self._store.update(strategy_id, {"status": StrategyStatus.PAUSED})
    
    def resume_strategy(self, strategy_id: str) -> Optional[StrategyMetadata]:
        """恢復策略"""
        return self._store.update(strategy_id, {"status": StrategyStatus.ACTIVE})
    
    def remove_strategy(self, strategy_id: str) -> bool:
        """移除策略"""
        return self._store.remove(strategy_id)