import os
import uvicorn
import logging
import argparse

from dotenv import load_dotenv

log_level_map = {
    'DEBUG': logging.DEBUG,       # 10
    'INFO': logging.INFO,        # 20
    'WARNING': logging.WARNING,  # 30
    'ERROR': logging.ERROR,      # 40
    'CRITICAL': logging.CRITICAL # 50
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the server in different modes.")
    parser.add_argument("--prod",action="store_true", help="Run the server in production mode.")
    parser.add_argument("--test",action="store_true", help="Run the server in test mode.")
    parser.add_argument("--dev",action="store_true", help="Run the server in development mode.")
    
    args = parser.parse_args()
    
    if args.prod:
        load_dotenv("app/settings/.env.prod")
    elif args.test:
        load_dotenv("app/settings/.env.test")
    else:
        load_dotenv("app/settings/.env.dev")
        
    log_level = os.getenv("LOG_LEVEL")
        
    logging.basicConfig(
        level=log_level_map[log_level],
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # 輸出到控制台
            logging.FileHandler('strategy_server.log')  # 輸出到文件
        ]
    )
    
    logger = logging.getLogger(__name__)
    uvicorn_log_level = log_level.lower()
    
        
    uvicorn.run(
            app="main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT")),
            reload=bool(os.getenv("RELOAD")),  # 開發模式啟用熱重載
            reload_dirs=["app"],  # 監聽的目錄
            log_level=uvicorn_log_level
        )