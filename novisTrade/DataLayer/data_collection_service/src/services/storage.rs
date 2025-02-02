use anyhow::{Result, anyhow};
use serde_json::{Value, to_string};
use std::path::PathBuf;
use std::collections::HashMap;
// use tracing::{info, error};
use crate::{
    configuration::Settings,
    models::MarketData,
    utils::file_rotation::FileRotator,
};

pub struct StorageService {
    base_path: PathBuf,
    file_rotators: HashMap<String, FileRotator>,
}

impl StorageService {
    pub async fn new(settings: Settings) -> Result<Self> {
        let base_path = PathBuf::from(&settings.log_directory);
        Ok(Self {
            base_path,
            file_rotators: HashMap::new(),
        })
    }

    pub async fn store(&mut self, data: MarketData) -> Result<()> {
        let jsonl = self.serialize_to_jsonl(&data)?;
        let timestamp = self.extract_timestamp(&data.0)?;
        
        // 根據 topic 解析路徑
        let topic = data.0.get("topic")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("No topic found in data"))?;

        // 根據獲取的資訊，建立對應的 FileRotator
        let rotator = self.get_or_create_rotator(topic).await?;
        
        // 使用 timestamp 來決定檔案
        let file = rotator.get_current_file(timestamp).await?;

        // 寫入資料並確保換行
        use std::io::Write;
        writeln!(file, "{}", jsonl)?;
        file.flush()?;

        Ok(())
    }

    async fn get_or_create_rotator(&mut self, topic: &str) -> Result<&mut FileRotator> {
        if !self.file_rotators.contains_key(topic) {
            let segments: Vec<&str> = topic.split(':').collect();
            if segments.len() != 4 {
                return Err(anyhow!("Invalid topic format"));
            }

            let path = self.base_path
                .join(segments[0])
                .join(segments[1])
                .join(segments[2])
                .join(segments[3]);

            let rotator = FileRotator::new(path).await?;
            self.file_rotators.insert(topic.to_string(), rotator);
        }

        Ok(self.file_rotators.get_mut(topic).unwrap())
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