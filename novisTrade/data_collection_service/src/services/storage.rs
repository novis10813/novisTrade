use anyhow::{Result, anyhow};
use serde_json::{Value, to_string};
use std::path::PathBuf;
// use tracing::{info, error};
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

        let timestamp = self.extract_timestamp(&data.0)?;
        
        // 使用 timestamp 來決定檔案
        let file = self.file_rotator
            .get_current_file(timestamp)
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

    fn extract_timestamp(&self, value: &Value) -> Result<i64> {
        if let Some(timestamp) = value.get("exchTimestamp")
            .and_then(|v| v.as_i64()) {
            return Ok(timestamp);
        }

        if let Some(timestamp) = value.get("localTimestamp")
            .and_then(|v| v.as_i64()) {
            return Ok(timestamp);
        }

        Err(anyhow!("No timestamp found in data"))
    }
}