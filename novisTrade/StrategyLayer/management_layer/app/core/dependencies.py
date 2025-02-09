# app/core/dependencies.py
"""Singleton pattern"""

from core.manager import StrategyManager
from core.strategy_store import StrategyStore


_redis_connector = None
_strategy_manager = None
_strategy_store = None

def get_strategy_manager() -> StrategyManager:
    global _strategy_manager
    if _strategy_manager is None:
        _strategy_manager = StrategyManager()
    return _strategy_manager

def get_strategy_store() -> StrategyStore:
    global _strategy_store
    if _strategy_store is None:
        _strategy_store = StrategyStore()
    return _strategy_store