# app/main.py
import uvicorn
import logging

from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.v1.strategies import strategies
from app.core.dependencies import get_strategy_store

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    啟動事件
    """
    # 需要初始化的服務都在這邊調用
    get_strategy_store()
    yield
    
    
app = FastAPI(
    title="Strategy Management API",
    description="API for managing trading strategies",
    version="0.1",
    lifespan=lifespan
)


app.include_router(
    strategies,
    prefix="/api/v1"
)

# 配置日誌

LOG_LEVEL = logging.DEBUG

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 輸出到控制台
        logging.FileHandler('strategy_server.log')  # 輸出到文件
    ]
)

logger = logging.getLogger(__name__)

def main():
    """
    應用程式主入口點
    """
    try:
        logger.info("Starting Strategy Management Server...")
        uvicorn_log_level = logging.getLevelName(LOG_LEVEL).lower()
        # 啟動伺服器
        uvicorn.run(
            app=app,
            host="0.0.0.0",
            port=5000,
            reload=True,  # 開發模式啟用熱重載
            log_level=uvicorn_log_level
        )
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        raise

if __name__ == "__main__":
    main()