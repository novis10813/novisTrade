# app/core/dependencies.py
"""Singleton pattern"""

from app.core.cache.redis_client import RedisClient
from app.settings.config import get_settings

_settings = get_settings()
_redis_client = None

def get_redis_client() -> RedisClient:
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient(
            redis_host=_settings.redis_host,
            redis_port=_settings.redis_port,
            redis_db=_settings.redis_db
        )
    return _redis_client