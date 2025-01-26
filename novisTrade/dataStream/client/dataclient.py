import json
import asyncio
import logging
import websockets
import redis.asyncio as redis
from typing import List, Dict, Any



# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataStreamClient:
    def __init__(
        self,
        ws_uri: str = "ws://localhost:8765",
        redis_host: str = "localhost",
        redis_port: int = 6379
    ):
        self.ws_uri = ws_uri
        self.redis_host = redis_host 
        self.redis_port = redis_port
        
        self.client_id = None
        self.websocket = None
        self.redis_client = None
        self.pubsub = None
        
    async def connect(self):
        """建立初始連線"""
        # 建立 Redis 連線
        self.redis_client = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            db=0,
            decode_responses=True
        )
        self.pubsub = self.redis_client.pubsub()
        
        # 建立 websocket 連線
        try:
            self.websocket = await websockets.connect(self.ws_uri)
            response = await self.websocket.recv()
            connection_info = json.loads(response)
            self.client_id = connection_info["client_id"]
            logger.info(f"Connected to server with client id: {self.client_id}")
            return True
        
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            await self.close()
            return False
            
    async def subscribe(self, channels: List[str]):
        """訂閱指定的頻道"""
        if not self.websocket or not self.client_id:
            raise RuntimeError("Not connected to server")
            
        request = {
            "action": "subscribe",
            "params": channels,
            "client_id": self.client_id
        }
        
        await self.websocket.send(json.dumps(request))
        
        # 訂閱對應的 Redis 頻道
        await self.pubsub.subscribe(*channels)
        
    async def close(self):
        """清理資源"""
        if self.websocket:
            await self.websocket.close()
        
        if self.redis_client:
            await self.redis_client.close()
            
        logger.info("Client closed")
            
    async def on_messages(self):
        """處理來自 Redis 的訊息"""
        try:
            async for message in self.pubsub.listen():
                yield message
                # if message["type"] == "message":
                #     # channel = message["channel"]
                #     data = json.loads(message["data"])
                #     yield data
                    
        except Exception as e:
            logger.error(f"ZeroMQ error: {str(e)}")
            await self.close()

async def main():
    # 建立客戶端
    client = DataStreamClient()
    
    try:
        # 先建立連線
        if await client.connect():
            # 訂閱頻道
            channels = [
                "binance:spot:btcusdt:aggTrade",
                "binance:spot:ethusdt:trade"
            ]
            await client.subscribe(channels)
            
            # 開始監聽
            async for message in client.on_messages():
                print(f"Received message: {message}")
            
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down...")
        await client.close()
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())