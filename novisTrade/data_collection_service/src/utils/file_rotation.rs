// utils/file_rotation.rs
use anyhow::Result;
use chrono::{NaiveDate, Utc, TimeZone};
use std::path::PathBuf;
use std::fs::{OpenOptions, File};
use tracing::info;
use tokio::fs::create_dir_all;

#[derive(Debug)]
pub struct FileRotator {
    base_path: PathBuf,
    current_file: Option<File>,
    current_date: NaiveDate,
}

impl FileRotator {
    pub async fn new(base_path: PathBuf) -> Result<Self> {
        if !base_path.exists() {
            create_dir_all(&base_path).await?;
        }

        Ok(Self {
            base_path,
            current_file: None,
            current_date: Utc::now().date_naive(),
        })
    }

    pub async fn get_current_file(&mut self, timestamp: i64) -> Result<&mut File> {
        let date = Utc.timestamp_millis_opt(timestamp)
            .unwrap()
            .date_naive();
        if self.current_file.is_none() || date != self.current_date {
            self.create_new_file(date).await?;
        }

        Ok(self.current_file.as_mut().unwrap())
    }

    async fn create_new_file(&mut self, date: NaiveDate) -> Result<()> {
        let filename = self.generate_filename(date);
        let filepath = self.base_path.join(filename);

        info!("Creating new file: {:?}", filepath);

        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&filepath)?;

        self.current_file = Some(file);
        self.current_date = date;

        Ok(())
    }

    fn generate_filename(&self, date: NaiveDate) -> String {
        format!("{}.jsonl", date.format("%Y%m%d"))
    }
}