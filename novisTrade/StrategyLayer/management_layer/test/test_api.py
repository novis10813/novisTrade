# test_api.py
import requests
import json

BASE_URL = "http://localhost:5000"

def test_strategy_operations():
    # 1. 新增策略
    strategy_data = {
        "name": "Test Strategy",
        "description": "Testing strategy operations",
        "parameters": {
            "param1": 100,
            "param2": "value"
        }
    }
    
    print("\n1. Adding new strategy...")
    response = requests.post(f"{BASE_URL}/strategies", json=strategy_data)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        strategy = response.json()
        strategy_id = strategy['id']
        print(json.dumps(strategy, indent=2))
        
    # 2. 列出所有策略
    print("\n2. Listing all strategies...")
    response = requests.get(f"{BASE_URL}/strategies")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
        
        # 3. 暫停策略
        print(f"\n3. Pausing strategy {strategy_id}...")
        response = requests.patch(f"{BASE_URL}/strategies/{strategy_id}/pause")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
        
        # 4. 修改策略參數
        print(f"\n4. Updating strategy {strategy_id}...")
        update_data = {
            "parameters": {
                "param1": 200,
                "param2": "new_value"
            }
        }
        response = requests.put(f"{BASE_URL}/strategies/{strategy_id}", json=update_data)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
        
        # 5. 恢復策略
        print(f"\n5. Resuming strategy {strategy_id}...")
        response = requests.patch(f"{BASE_URL}/strategies/{strategy_id}/resume")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
        
        # 6. 刪除策略
        print(f"\n6. Deleting strategy {strategy_id}...")
        response = requests.delete(f"{BASE_URL}/strategies/{strategy_id}")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_strategy_operations()