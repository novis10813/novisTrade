// configuration/settings.rs
use serde::Deserialize;
use config::{Config, ConfigError, Environment};
use dotenv::dotenv;

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
    pub fn new() -> Result<Self, ConfigError> {
        // 載入 .env 文件
        dotenv().ok();

        match std::env::var("REDIS_URL") {
            Ok(url) => {
                println!("Using REDIS_URL from environment: {}", url);
            }
            Err(_) => {
                println!("REDIS_URL not found in environment, using default");
            }
        }

        let config = Config::builder()
            // 從 config.toml 讀取基本配置
            .add_source(config::File::with_name("config"))
            // 從環境變數讀取 REDIS_URL
            .add_source(Environment::default())
            // 設定預設值
            .set_default("redis_url", "redis://127.0.0.1:6379")?
            .set_default("exchange_name", "binance")?
            .set_default("symbols", vec!["btcusdt".to_string()])?
            .set_default("market_type", "spot")?
            .set_default("stream_type", "aggTrade")?
            .set_default("log_directory", "./Data")?
            .build()?;

        let settings = config.try_deserialize()?;
        println!("Settings: {:?}", settings);

        Ok(settings)
    }
}