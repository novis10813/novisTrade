import pytest
import requests

BASE_URL = "http://localhost:5000"

@pytest.fixture
def strategy_payload() -> dict:
    return {
        "name": "Test Strategy",
        "description": "Testing create strategy with pytest",
        "status": "stopped",
        "data": {
            "source": "stream",
            "types": [
                {
                    "exchange": "binance",
                    "market": "spot",
                    "symbol": "btcusdt",
                    "stream": "aggTrade",
                },
                {
                    "exchange": "kraken",
                    "market": "spot",
                    "symbol": "BTC/USD",
                    "stream": "trade",
                }
            ],
        },
        "preprocess": {
            "binance:spot:btcusdt:aggTrade": {
                "processId_1": [
                    {
                        "operation": "timebar",
                        "params": {"interval": "1m", "on": "price"},
                    },
                    {
                        "operation": "ema",
                        "params": {"period": 10, "on": "open"},
                    },
                ],
                "processId_2": [
                    {
                        "operation": "timebar",
                        "params": {"interval": "5m", "on": "price"},
                    },
                    {
                        "operation": "ema",
                        "params": {"period": 20, "on": "close"},
                    },
                ],
            }
        },
        "signals": {
            "models": [
                {
                    "model_id": "model_1",
                    "file_name": "model_1.pkl",
                    "input_features": ["processId_1", "processId_2"],
                    "should_wait": False,
                },
                {
                    "model_id": "model_2",
                    "file_name": "model_2.pkl",
                    "input_features": ["processId_2"],
                },
            ],
            "logic": {
                "long_entry": "",
                "long_exit": "",
                "short_entry": "",
                "short_exit": "",
            },
        },
    }

def test_create_strategy(strategy_payload: dict):
    url = f"{BASE_URL}/api/v1/strategies"
    response = requests.post(url, json=strategy_payload)
    
    # 檢查是否正確回應 201
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    
    # 驗證 response 是否包含 strategy_id
    data = response.json()
    assert "id" in data, f"Missing strategy_id in response: {data}"
