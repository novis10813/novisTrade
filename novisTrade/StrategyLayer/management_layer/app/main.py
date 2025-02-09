# app/main.py
import uvicorn
import logging
import argparse

from dotenv import load_dotenv
from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.v1.strategy import strategies
from core.dependencies import get_strategy_store
from settings.config import get_settings

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    啟動事件
    """
    # 需要初始化的服務都在這邊調用
    get_strategy_store()
    yield

settings = get_settings()

logger.debug(f"Settings: {settings}")
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