import os
import asyncio
import logging

from shared.utils import map_logging_level
from binance_ws import BinanceWebSocket

def init_logger(logging_level: int):
    # 設定 root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging_level)
    
    # 清除現有的 handlers 以避免重複
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # 新增 handler 和 formatter
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(handler)
    
    # 也可以設定當前模組的 logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging_level)
    return logger

async def main():
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv("REDIS_DB", 0))
    logging_level = os.getenv("LOGGING_LEVEL", "INFO")
    logger = init_logger(map_logging_level(logging_level))

    logger.debug("Starting Binance WebSocket client...")
    ws_client = BinanceWebSocket(
        redis_host=redis_host,
        redis_port=redis_port,
        redis_db=redis_db,
    )

    await ws_client.start()


if __name__ == "__main__":
    asyncio.run(main())
