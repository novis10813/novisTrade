# import sys
# import os
# sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

import json
import asyncio
import aiofiles
import argparse

from pathlib import Path
from datetime import datetime
from collections import defaultdict

from novisTrade.dataStream import DataStreamClient

class DataCollector:
    def __init__(self, data_dir="Data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.file_handlers = {}
        self.buffers = defaultdict(list)
        self.buffer_size = 50  # 每1000筆資料寫入一次
        self.current_dates = {}
        
    def _get_filename(self, channel, timestamp):
        dt = datetime.fromtimestamp(timestamp / 1000)
        date_str = dt.date().isoformat()
        exchange, market, symbol, datatype = channel.split(':')
        
        # 建立結構目錄
        dir_path = self.data_dir / exchange / market / datatype / symbol
        dir_path.mkdir(parents=True, exist_ok=True)
        
        return dir_path / f"{date_str}.jsonl"
        
    async def get_file(self, channel, timestamp):
        filepath = self._get_filename(channel, timestamp)
        
        if channel not in self.file_handlers:
            self.file_handlers[channel] = await aiofiles.open(filepath, mode='a')
            self.buffers[channel] = []
            
        return self.file_handlers[channel]
        
    async def write(self, message):
        try:
            data = json.loads(message["data"])
            channel = message["channel"]
            timestamp = data["localTimestamp"]
            
            current_date = datetime.fromtimestamp(timestamp / 1000).date()
            if channel in self.current_dates and self.current_dates[channel] != current_date:
                # 日期改變的話，將現有的 buffer 寫入檔案
                await self.flush(channel, timestamp)
                # 關閉舊的檔案
                if channel in self.file_handlers:
                    await self.file_handlers[channel].close()
                    del self.file_handlers[channel]
                # 更新日期
                self.current_dates[channel] = current_date
            
            json_str = json.dumps(data) + '\n'
            self.buffers[channel].append(json_str)
            
            if len(self.buffers[channel]) >= self.buffer_size:
                await self.flush(channel, timestamp)
                
        except Exception as e:
            print(f"Error writing data: {e}")
            
    async def flush(self, channel, timestamp):
        if not self.buffers.get(channel):
            return
            
        file = await self.get_file(channel, timestamp)
        await file.write(''.join(self.buffers[channel]))
        await file.flush()
        self.buffers[channel].clear()
        
    async def close(self):
        for channel in list(self.file_handlers.keys()):
            if self.buffers.get(channel):
                # 使用最後一筆資料的時間戳記
                last_message = json.loads(self.buffers[channel][-1])
                last_data = json.loads(last_message["data"])
                await self.flush(channel, last_data["localTimestamp"])
            await self.file_handlers[channel].close()
        self.file_handlers.clear()


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="Data")
    parser.add_argument("--ws_uri", type=str, default="ws://localhost:8766")
    parser.add_argument("--channels", type=str, nargs="+", default=["binance:perp:btcusdt:aggTrade"])
    return parser.parse_args()

async def main():
    args = parse_arguments()
    logger = DataCollector(data_dir=args.data_dir)
    client = DataStreamClient(ws_uri=args.ws_uri)
    
    try:
        if await client.connect():
            await client.subscribe(args.channels)
            
            async for message in client.on_messages():
                if isinstance(message["data"], int):
                    continue
                await logger.write(message)
                
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("Shutting down...")
        await logger.close()
        await client.close()
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        await logger.close()
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())