# DataStream Module

這個模組主要用於處理即時市場數據的串流，採用 WebSocket 連接來接收交易所的即時數據，並透過 Redis 進行數據的分發。

## 資料夾結構
```
dataStream/
├── __init__.py
├── README.md
├── client/
│   ├── __init__.py
│   └── dataclient.py
├── server/
│   ├── __init__.py
│   └── dataserver.py
├── exchanges/
│   ├── __init__.py
│   ├── base_ws.py
│   ├── binance_ws.py
│   ├── kraken_ws.py
│   └── exchange_factory.py
└── core/
    ├── __init__.py
    ├── ws_manager.py
    └── exceptions.py
```


## 檔案說明

### 核心檔案
- `dataclient.py`: 客戶端實現，負責訂閱數據並從 Redis 接收數據
- `dataserver.py`: 伺服器端實現，負責管理 WebSocket 連接和處理客戶端請求

### exchanges 資料夾
- `base_ws.py`: 定義交易所 WebSocket 的基礎類別和介面
- `binance_ws.py`: 幣安交易所的具體實現
- `kraken_ws.py`: Kraken 交易所的具體實現
- `exchange_factory.py`: 工廠模式，用於創建不同交易所的 WebSocket 實例
- `ws_manager.py`: WebSocket 連接管理器，處理連接的建立、維護和重連

## 主要功能

### 1. 多交易所支援
- 支援多個交易所的 WebSocket 連接（目前支援 Binance 和 Kraken）
- 透過工廠模式實現交易所的擴展性
- 統一的資料格式轉換，方便後續處理

### 2. 連接管理
- 自動重連機制
- 連接狀態監控
- 錯誤處理和日誌記錄
- 支援多客戶端訂閱管理

### 3. 資料分發
- 使用 Redis pub/sub 機制進行資料分發
- 支援多種市場數據類型（如 trade、aggTrade 等）
- 支援不同市場類型（現貨、永續合約等）

### 4. 客戶端功能
- 簡單的訂閱/取消訂閱介面
- 非阻塞的異步數據處理
- 自動重連和錯誤處理

## 使用範例

### 1. 啟動服務端
```python
from dataStream.server.dataserver import DataStreamServer

async def main():
    server = DataStreamServer(host='localhost', port=8765)
    await server.start()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 2. 客戶端訂閱數據
```python
from dataStream.client.dataclient import DataStreamClient

async def main():
    # 建立客戶端連接
    client = DataStreamClient()
    
    try:
        # 建立連接
        if await client.connect():
            # 訂閱特定交易對的數據
            channels = [
                "binance:spot:btcusdt:aggTrade",
                "binance:spot:ethusdt:trade"
            ]
            await client.subscribe(channels)
            
            # 接收和處理數據
            async for message in client.on_messages():
                print(f"Received message: {message}")
                
    except KeyboardInterrupt:
        print("Shutting down...")
        await client.close()
        
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 3. 新增交易所支援
```python
from dataStream.exchanges.base_ws import ExchangeWebSocket
from dataStream.exchanges.exchange_factory import ExchangeWebSocketFactory

# 實現新的交易所類別
class NewExchangeWebSocket(ExchangeWebSocket):
    # 實現必要的方法
    pass

# 註冊新的交易所
ExchangeWebSocketFactory.register("new_exchange", NewExchangeWebSocket)
```