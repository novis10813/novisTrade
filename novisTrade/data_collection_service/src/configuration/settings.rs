// configuration/settings.rs
use serde::Deserialize;
use config::{Config, ConfigError, Environment};

// derive 類似於 python 的 decorator
// 但他實際在做的事情是給原有的 class 加上更多行為
#[derive(Debug, Deserialize, Clone)]
pub struct Settings {
    pub redis_url: String,
    pub exchange_name: String,
    pub symbols: Vec<String>,
    pub market_type: String,
    pub stream_type: String,
    pub log_directory: String,
}

impl Settings {
    // 讀取 .env 檔案並設定預設值
    pub fn new() -> Result<Self, ConfigError> {
        let config: Config = Config::builder()
            // 設定預設值
            .set_default("redis_url", "redis://127.0.0.1:6379")?
            .set_default("exchange_name", "binance")?
            .set_default("symbols", vec!["btcusdt".to_string()])?
            .set_default("market_type", "spot")?
            .set_default("stream_type", "aggTrade")?
            .set_default("log_directory", "./logs")?
            // 從環境變數讀取
            .add_source(Environment::default())
            .build()?;

        config.try_deserialize()
    }
}