# main.py
import uvicorn
import logging
import sys
from api import app
from pathlib import Path

# 添加專案根目錄到 Python 路徑
# ROOT_DIR = str(Path(__file__).parent.parent)
# sys.path.append(ROOT_DIR)

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
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
        
        # 啟動伺服器
        uvicorn.run(
            app="api:app",
            host="0.0.0.0",
            port=5000,
            reload=True,  # 開發模式啟用熱重載
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        raise

if __name__ == "__main__":
    main()