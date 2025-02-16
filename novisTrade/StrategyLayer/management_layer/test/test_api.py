# test_api.py
import requests
import json

BASE_URL = "http://localhost:5000"


def test_strategy_operations():
    # 1. 新增策略
    strategy_data = {
        "name": "Test Strategy",
        "description": "Testing strategy operations",
        "status": "stopped",
        "data": {
            "source": "stream",  # stream or historic
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
            ],  # list of different data sources
        },
        "preprocess": {
            "binance:spot:btcusdt:aggTrade": {
                "processId_1": [
                    {
                        "operation": "timebar",
                        "params": {"interval": "1m", "on": "price"},
                    },  # process aggTrade time bar with 1 minute interval
                    # timebar will return data with open, high, low, close, volume
                    {
                        "operation": "ema",
                        "params": {"period": 10, "on": "open"},
                    },  # process ema with 10 period using open price
                ],
                "processId_2": [
                    {
                        "operation": "timebar",
                        "params": {"interval": "5m", "on": "price"},
                    },  # process aggTrade time bar with 5 minute interval
                    {
                        "operation": "ema",
                        "params": {"period": 20, "on": "close"},
                    },  # process ema with 20 period using close price
                ],
            }
        },
        "signals": {  # 負責使用 preprocessed data 來產生交易進出場訊號，產生方式可以單純透過技術指標的邏輯，或是透過機器學習模型預測後再進行邏輯判斷
            "models": [
                {
                    "model_id": "model_1",
                    "file_name": "model_1.pkl",
                    "input_features": ["processId_1", "processId_2"],
                    "should_wait": False,  # 是否等待所有特徵都有資料才進行預測，默認為 True，若為 False 則只要有一個特徵有新資料，剩下的特徵就用最後一筆資料
                },
                {
                    "model_id": "model_2",
                    "file_name": "model_2.pkl",
                    "input_features": ["processId_2"],
                },
            ],
            "logic": {  # 這邊應該會使用類似 Langchain 的模板設計，類似以下的寫法:
                "long_entry": "",  # """{processId_1} > {processId_2}"""
                "long_exit": "",  # """{model_1} > 0.5 ..."""
                "short_entry": "",
                "short_exit": "",
            },
        },
    }

    # print("\n1. Adding new strategy...")
    # response = requests.post(f"{BASE_URL}/api/v1/strategies", json=strategy_data)
    # print(f"Status Code: {response.status_code}")
    # if response.status_code == 201:
    #     strategy_id = response.json()["id"]
    #     print(f"response: {response.json()}")
    
    # 2. 列出所有策略
    # print("\n2. Listing all runtime strategies...")
    # response = requests.get(f"{BASE_URL}/api/v1/strategies/runtime")
    # print(f"Status Code: {response.status_code}")
    # if response.status_code == 202:
    #     print(json.dumps(response.json(), indent=2))
    
    # print("\n3. Listing all db strategies...")
    # response = requests.get(f"{BASE_URL}/api/v1/strategies/db")
    # print(f"Status Code: {response.status_code}")
    # if response.status_code == 202:
    #     print(json.dumps(response.json(), indent=2))
    #     print("Now we have {} strategies in db".format(len(response.json())))


    # 3. 列出指定策略
    # print("\n3. Listing specified strategy...")
    # response = requests.get(f"{BASE_URL}/api/v1/strategies/runtime/f8841ecb-42ab-47c5-9b31-b25c32578abf")
    # print(f"Status Code: {response.status_code}")
    # if response.status_code == 202:
    #     print(json.dumps(response.json(), indent=2))

    print("\n4. Listing specific db strategies...")
    response = requests.get(f"{BASE_URL}/api/v1/strategies/db/f8841ecb-42ab-47c5-9b31-b25c32578abf")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 202:
        print(json.dumps(response.json(), indent=2))
        print("success")

    #     # 3. 暫停策略
    #     print(f"\n3. Pausing strategy {strategy_id}...")
    #     response = requests.patch(f"{BASE_URL}/strategies/{strategy_id}/pause")
    #     print(f"Status Code: {response.status_code}")
    #     if response.status_code == 200:
    #         print(json.dumps(response.json(), indent=2))

    #     # 4. 修改策略參數
    #     print(f"\n4. Updating strategy {strategy_id}...")
    #     update_data = {"parameters": {"param1": 200, "param2": "new_value"}}
    #     response = requests.put(
    #         f"{BASE_URL}/strategies/{strategy_id}", json=update_data
    #     )
    #     print(f"Status Code: {response.status_code}")
    #     if response.status_code == 200:
    #         print(json.dumps(response.json(), indent=2))

    #     # 5. 恢復策略
    #     print(f"\n5. Resuming strategy {strategy_id}...")
    #     response = requests.patch(f"{BASE_URL}/strategies/{strategy_id}/resume")
    #     print(f"Status Code: {response.status_code}")
    #     if response.status_code == 200:
    #         print(json.dumps(response.json(), indent=2))

    #     # 6. 刪除策略
    #     print(f"\n6. Deleting strategy {strategy_id}...")
    #     response = requests.delete(f"{BASE_URL}/strategies/{strategy_id}")
    #     print(f"Status Code: {response.status_code}")
    #     if response.status_code == 200:
    #         print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    test_strategy_operations()

