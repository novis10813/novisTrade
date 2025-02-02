// models/market_data.rs
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct SubscriptionRequest {
    pub action: String,
    pub symbols: Vec<String>,
    #[serde(rename = "streamType")]
    pub stream_type: String,
    #[serde(rename = "marketType")]
    pub market_type: String,
    #[serde(rename = "requestId")]
    pub request_id: u64,
}

impl SubscriptionRequest {
    pub fn new(action: String, symbols: Vec<String>, stream_type: String, market_type: String) -> Self {
        Self {
            action,
            symbols,
            stream_type,
            market_type,
            request_id: chrono::Utc::now().timestamp_millis() as u64,
        }
    }

    pub fn get_channels(&self, exchange: &str) -> Vec<String> {
        self.symbols.iter().map(|symbol| {
            format!("{}:{}:{}:{}", exchange, self.market_type, symbol, self.stream_type)
        }).collect()
    }
}

// 保持收到的原始資料格式，所以直接使用 Value 類型
use serde_json::Value;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct MarketData(pub Value);