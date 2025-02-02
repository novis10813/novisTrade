# 專案介紹

## 專案設置

### 環境設置

為了確保服務能正確讀寫資料，需要設置適當的系統權限：

1. 建立群組和資料目錄：
```bash
# 建立 trade 群組
sudo groupadd trade

# 建立資料目錄
sudo mkdir -p /mnt/raid1/exchange_data/Data

# 設定目錄權限
sudo chown -R root:trade /mnt/raid1/exchange_data
sudo chmod -R 775 /mnt/raid1/exchange_data
```

2. 將使用者加入群組：
```bash
# 將當前使用者加入 trade 群組
sudo usermod -aG trade $USER
```

3. 取得 trade 群組的 GID：
```bash
# 查看 trade 群組 ID
getent group trade
```

4. 對於需要存取資料的服務設定 docker-compose.yml：
```yaml
services:
  collection_service:
    # ... 其他設定 ...
    user: "1000:trade的GID"  # 替換為實際的 trade 群組 GID
    volumes:
      - /mnt/raid1/exchange_data/Data:/app/Data
    # ... 其他設定 ...
```

#### 注意事項
- 確保所有需要存取資料的服務都使用相同的 trade 群組 GID
- 若遇到權限問題，檢查：
  - 目錄權限是否正確 (`ls -la /mnt/raid1/exchange_data`)
  - 使用者是否已加入 trade 群組 (`groups`)
  - docker-compose.yml 中的 GID 設定是否正確