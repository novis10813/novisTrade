// main.rs
use anyhow::Result;
use tracing::{debug, error, info};
use tracing_subscriber;
use tokio_stream::StreamExt;

mod utils;
mod models;
mod services;
mod configuration;

use configuration::Settings;
use services::{receiver::RedisService, storage::StorageService};


#[tokio::main]
async fn main() -> Result<()> {
    // 初始化日誌
    tracing_subscriber::fmt::init();

    // 載入設定
    let settings: Settings = Settings::new()?;
    info!("Configuration loaded: {:?}", settings);

    // TODO: 設定 tracing
    let mut storage_service = StorageService::new(settings.clone()).await?;

    
    // 初始化 Redis 服務
    let redis_service = RedisService::new(settings.clone()).await?;

    // 啟動 Redis 訂閱
    debug!("Subscribing to topics");
    let mut stream = redis_service.subscribe().await?;

    // 開始監聽
    while let Some(market_data) = stream.next().await {
        // TODO: 儲存接收到的數據
        if let Err(e) = storage_service.store(market_data).await {
            error!("Storage error: {}", e);
        }
    }

    Ok(())
}