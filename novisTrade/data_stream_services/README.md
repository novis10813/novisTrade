# DataStream Module

這個模組主要用於處理即時市場數據的串流，採用 WebSocket 連接來接收交易所的即時數據，並透過 Redis 進行數據的分發。

## For 我健忘的小腦袋

先在根目錄啟動 Redis
```bash
docker compose up -d
```

只啟動特定交易所:
```bash
docker compose up binance -d
```

在已經啟動的情況下再啟動其他間交易所:
```bash
docker compose up -d kraken
```

## 資料夾說明
```
data_stream_services
├── docker-compose.yml
├── README.md
├── requirements.txt
├── .env
├── services
│  ├── binance
│  │  ├── Dockerfile
│  │  └── src
│  │     └── main.py
│  ├── kraken
│  │  ├── Dockerfile
│  │  └── src
│  │     └── main.py
└── shared
   └── core
      ├── __init__.py
      ├── base_ws.py
      └── ws_manager.py
```

## 使用說明

這邊基本上每間交易所都是一個微服務，所以可以自由新增刪減交易所

然後，送給交易所的 Event 是