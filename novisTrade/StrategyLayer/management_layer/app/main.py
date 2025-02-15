# app/main.py
import logging

from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.v1.strategy import strategies
from settings.config import get_settings

settings = get_settings()

log_level_map = {
    'DEBUG': logging.DEBUG,       # 10
    'INFO': logging.INFO,        # 20
    'WARNING': logging.WARNING,  # 30
    'ERROR': logging.ERROR,      # 40
    'CRITICAL': logging.CRITICAL # 50
}

logging.basicConfig(
    level=log_level_map[settings.log_level],
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('strategy_server.log')
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    啟動事件
    """
    # 需要初始化的服務都在這邊調用
    yield


app = FastAPI(
    title=settings.app_name,
    description="API for managing trading strategies",
    version="0.1",
    lifespan=lifespan
)


app.include_router(
    strategies,
    prefix="/api/v1"
)

@app.get("/infor")
def get_infor():
    settings = get_settings()
    return {
        "app_name": settings.app_name,
    }