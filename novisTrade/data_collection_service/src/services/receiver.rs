// services/redis.rs
use tokio::sync::mpsc;
use tokio_stream::{Stream, StreamExt};

use anyhow::{Result, Context};
use tracing::{info, error};

use redis::{AsyncCommands};
use redis::aio::MultiplexedConnection;

use crate::configuration::Settings;
use crate::models::{MarketData, SubscriptionRequest};

#[derive(Clone)]
pub struct RedisService {
    client: redis::Client,
    settings: Settings,
}

impl RedisService {
    pub async fn new(settings: Settings) -> Result<Self> {
        let client: redis::Client = redis::Client::open(settings.redis_url.clone())
            .context("Failed to create Redis client")?;
        Ok(Self { client, settings })
    }

    pub async fn cleanup(&self) {
        let settings = self.settings.clone();
        let client = self.client.clone();

        if let Ok(mut conn) = client.get_multiplexed_async_connection().await {
            let request = SubscriptionRequest::new(
                "unsubscribe".to_string(),
                settings.symbols.clone(),
                settings.stream_type.clone(),
                settings.market_type.clone(),
            );

            let channel = format!("{}:control", settings.exchange_name);
            let message = serde_json::to_string(&request).unwrap();

            let result: redis::RedisResult<i64> = conn.publish(&channel, message).await;
            match result {
                Ok(receivers) => {
                    info!("Unsubscribed from {} ({} receivers)", channel, receivers);
                }
                Err(e) => {
                    error!("Failed to publish unsubscribe request: {}", e);
                }
            }
        }
    }
    

    pub async fn publish_request(&self, request: &SubscriptionRequest) -> Result<u64> {
        let mut conn: MultiplexedConnection = self.client.get_multiplexed_async_connection().await
            .context("Failed to get Redis connection")?;
        let channel: String = format!("{}:control", self.settings.exchange_name);
        let message: String = serde_json::to_string(&request)?;

        let receivers: u64 = conn.publish(&channel, message).await 
            .context("Failed to publish subscription request")?;
        info!("Published subscription request: {}", channel);
        Ok(receivers)
    }

    pub async fn subscribe(&self) -> Result<impl Stream<Item = MarketData>> {
        let client: redis::Client = self.client.clone();
        let mut pubsub_conn = client.get_async_pubsub().await
            .context("Failed to get Redis pubsub connection")?;

        let request: SubscriptionRequest = SubscriptionRequest::new(
            "subscribe".to_string(),
            self.settings.symbols.clone(),
            self.settings.stream_type.clone(),
            self.settings.market_type.clone(),
        );

        // 發送訂閱訊息
        let _response = self.publish_request(&request).await?;

        for channel in request.get_channels(&self.settings.exchange_name) {
            pubsub_conn.subscribe(&channel).await
                .context("Failed to subscribe to channel")?;
            info!("Subscribed to channel: {}", channel);
        }
        Ok(self.on_message(pubsub_conn))
    }

    fn on_message(&self, mut pubsub_conn: redis::aio::PubSub) -> impl Stream<Item = MarketData> {
        let (tx, rx) = mpsc::channel(100);

        tokio::spawn(async move {
            let mut stream = pubsub_conn.on_message();
            while let Some(msg) = stream.next().await {  // msg 直接是 `redis::Msg`
                let payload: String = msg.get_payload().unwrap_or_default();
                match serde_json::from_str::<MarketData>(&payload) {
                    Ok(data) => {
                        if tx.send(data).await.is_err() {
                            error!("Failed to send message to receiver");
                            break;
                        }
                    }
                    Err(e) => {
                        error!("Failed to parse message: {}", e);
                    }
                }
            }
        });
    
        tokio_stream::wrappers::ReceiverStream::new(rx)
    }
}

impl Drop for RedisService {
    fn drop(&mut self) {
        let service = self.clone();
        tokio::spawn(async move {
            service.cleanup().await;
        });
    }
}