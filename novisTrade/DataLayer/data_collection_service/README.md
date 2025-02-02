```prompt
你現在要協助我完成以下的 rust 專案，並且要以資深工程師的角度出發，先討論該有的程式架構後，才開始寫程式。
討論程式架構的時候，可以先從已有的程式和檔案層級開始探討。

請記住，每份檔案應該要 well structured，如果需要使用到還沒寫到的部分，就請你透過 TODO 等方式預留介面。
在說明的底下，我會附上我們已經完成的部分
```

# Data Collector

說明:

這份程式能夠透過訂閱 Redis ，獲得指定交易所的交易對資料。並且以日為單位記錄不同的資料

## File Structure

```
src/
├── main.rs
├── configuration/
│   ├── mod.rs
│   └── settings.rs      // 配置管理
├── models/
│   ├── mod.rs
│   └── receivers.rs   // 資料結構定義
├── services/
│   ├── mod.rs
│   ├── redis.rs         // Redis 訂閱服務
│   └── storage.rs       // 檔案儲存服務
└── utils/
    ├── mod.rs
    └── file_rotation.rs // 檔案輪替邏輯
```
## 檔案說明

main.rs:
- 使用 config::Settings 加載設定
- 使用 services::redis::RedisService 訂閱資料
- 使用 services::storage::StorageService 處理儲存
- 負責整體流程控制和錯誤處理

configuration/settings.rs:
- 被 main.rs 使用來加載設定
- 被 services 模組使用來取得設定值
- 提供統一的設定介面

models/receivers.rs:
- 被 services/redis.rs 用於解析訂閱資料
- 被 services/storage.rs 用於序列化儲存
- 定義核心資料結構


services/redis.rs:
- 使用 config::Settings 取得 Redis 設定
- 使用 models::MarketData 處理資料
- 將處理好的資料傳給 storage.rs

services/storage.rs:
- 使用 models::MarketData 處理資料
- 使用 utils::file_rotation 進行檔案管理
- 負責資料持久化

utils/file_rotation.rs:
- 被 services/storage.rs 使用
- 提供檔案輪替功能

各個目錄下的 mod.rs:
- 組織和導出模組內容
- 控制模組的可見性

## Roadmap

- [ ] 設定檔能夠一次訂閱多間交易所的資料
- [ ] 自動存入 PostgreSQL 資料庫

## Dependencies
```
tokio = { version = "1.43.0", features = ["full"] }
redis = { version = "0.28.2", features = ["tokio-comp"] }
serde = { version = "1.0.217", features = ["derive"] }
serde_json = "1.0.138"
dotenv = "0.15.0"
tracing = "0.1.41"
tracing-subscriber = { version = "0.3.19", features = ["env-filter"] }
tracing-appender = "0.2.3"
chrono = "0.4.39"
config = "0.15.7"
anyhow = "1.0.95"
thiserror = "2.0.11"
tokio-stream = "0.1.17"
futures = "0.3.19"
metrics = "0.20"
metrics-exporter-prometheus = "0.16.1"
```