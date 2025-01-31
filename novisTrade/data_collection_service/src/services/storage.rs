use anyhow::Result;
use serde_json::to_string;
use std::path::PathBuf;
use tracing::{info, error};
use crate::{
    configuration::Settings,
    models::MarketData,
    utils::file_rotation::FileRotator,
};

pub struct StorageService {
    file_rotator: FileRotator,
}

impl StorageService {
    pub async fn new(settings: Settings) -> Result<Self> {
        let base_path = PathBuf::from(&settings.log_directory);
        let file_rotator = FileRotator::new(base_path).await?;

        Ok(Self { file_rotator })
    }

    pub async fn store(&mut self, data: MarketData) -> Result<()> {
        let jsonl = self.serialize_to_jsonl(&data)?;
        
        // 使用 timestamp 來決定檔案
        let file = self.file_rotator
            .get_current_file(data.exchTimestamp.as_i64().unwrap_or_else(|| data.localTimestamp.as_i64().unwrap()))
            .await?;

        // 寫入資料並確保換行
        use std::io::Write;
        writeln!(file, "{}", jsonl)?;
        file.flush()?;

        Ok(())
    }

    fn serialize_to_jsonl(&self, data: &MarketData) -> Result<String> {
        Ok(to_string(data)?)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use tempfile::tempdir;

    #[tokio::test]
    async fn test_storage_service() -> Result<()> {
        // Create temporary directory for testing
        let temp_dir = tempdir()?;
        
        // Create test settings
        let mut settings = Settings::default();
        settings.storage_path = temp_dir.path().to_str().unwrap().to_string();

        // Initialize storage service
        let mut storage = StorageService::new(settings).await?;

        // Create test market data
        let market_data = MarketData {
            exchTimestamp: json!(1738310064660),
            localTimestamp: json!(1738310064677),
            topic: json!("binance:spot:btcusdt:aggTrade"),
            price: json!("104024.83000000"),
            quantity: json!("0.00010000"),
            side: json!("sell"),
            aggTradeId: json!(3408663770),
            firstTradeId: json!(4492339738),
            lastTradeId: json!(4492339738),
        };

        // Store the data
        storage.store(market_data).await?;

        // Verify file exists and contains data
        let files = std::fs::read_dir(temp_dir.path())?;
        assert_eq!(files.count(), 1);

        Ok(())
    }
}