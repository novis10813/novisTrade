import os
from functools import lru_cache

from dotenv import load_dotenv

class Settings():
    app_name: str = "Strategy Management API"
    app_mode = os.getenv("MODE")
    
    redis_host: str = os.getenv("REDIS_HOST")
    redis_port: int = os.getenv("REDIS_PORT")
    redis_db: int = os.getenv("REDIS_DB")
    
    reload: bool = bool(os.getenv("RELOAD"))
    port: int = int(os.getenv("PORT"))

@lru_cache()
def get_settings():
    load_dotenv(f".env.{os.getenv("MODE")}")
    return Settings()