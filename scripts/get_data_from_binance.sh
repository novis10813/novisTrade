#!/bin/bash

# 顯示使用方法
usage() {
    echo "Usage: $0 [-s symbol] [-d days] [-p path]"
    echo "  -s: Trading symbol (default: BTCUSD_PERP)"
    echo "  -d: Number of days to download (default: 7)"
    echo "  -p: Base path for data storage (default: ./data)"
    exit 1
}

# 預設值
SYMBOL="BTCUSD_PERP"
DAYS=7
BASE_PATH="./data"

# 解析命令列參數
while getopts "s:d:p:h" opt; do
    case $opt in
        s) SYMBOL="$OPTARG";;
        d) DAYS="$OPTARG";;
        p) BASE_PATH="$OPTARG";;
        h) usage;;
        ?) usage;;
    esac
done

# 設置基礎 URL 和下載參數
BASE_URL="https://data.binance.vision/data/futures/cm/daily/trades/${SYMBOL}"
END_DATE=$(date +%Y-%m-%d)
START_DATE=$(date -d "$END_DATE -$((DAYS-1)) days" +%Y-%m-%d)
DOWNLOAD_DIR="${BASE_PATH}/${SYMBOL}"

# 創建下載目錄（確保目錄存在）
mkdir -p "$DOWNLOAD_DIR"

echo "Downloading $SYMBOL data from $START_DATE to $END_DATE"
echo "Files will be saved to $DOWNLOAD_DIR"
echo "-------------------------------------------"

# 轉換日期為秒數以便比較
start_seconds=$(date -d "$START_DATE" +%s)
end_seconds=$(date -d "$END_DATE" +%s)
current_seconds=$start_seconds

# 下載並處理檔案
while [ $current_seconds -le $end_seconds ]; do
    # 格式化當前日期
    current_date=$(date -d @$current_seconds +%Y-%m-%d)
    
    # 構建檔案名
    filename="${SYMBOL}-trades-${current_date}.zip"
    checksum_filename="${SYMBOL}-trades-${current_date}.zip.CHECKSUM"
    
    echo "Processing data for $current_date..."
    
    # 下載數據文件
    if wget -q --show-progress -P "$DOWNLOAD_DIR" "$BASE_URL/$filename" 2>/dev/null; then
        # 下載校驗檔
        if wget -q -P "$DOWNLOAD_DIR" "$BASE_URL/$checksum_filename" 2>/dev/null; then
            # 驗證校驗和
            cd "$DOWNLOAD_DIR"
            if sha256sum -c "$checksum_filename" > /dev/null 2>&1; then
                echo "✓ Checksum verified for $filename"
                
                # 解壓縮到當前目錄
                unzip -q -o "$filename"
                
                # 刪除 zip 和 checksum 文件
                rm -f "$filename" "$checksum_filename"
                
                echo "✓ Extracted and cleaned up $filename"
            else
                echo "✗ Checksum verification failed for $filename"
                rm -f "$filename" "$checksum_filename"
            fi
            cd - > /dev/null
        else
            echo "✗ Failed to download checksum for $current_date"
            rm -f "$DOWNLOAD_DIR/$filename"
        fi
    else
        echo "✗ Failed to download data for $current_date"
    fi
    
    # 增加一天
    current_seconds=$((current_seconds + 86400))
    
    # 避免請求過於頻繁
    sleep 1
done

echo "-------------------------------------------"
echo "Download completed!"
echo "Data files are in: $DOWNLOAD_DIR"

# 更新 README
cat > "${BASE_PATH}/README.md" << EOF
# Binance Futures Data

This directory contains downloaded futures trading data from Binance Vision.

## Directory Structure
\`\`\`
data/
└── BTCUSD_PERP/
    ├── BTCUSD_PERP-trades-2024-11-12.csv
    └── ...
\`\`\`

## Data Format
Each file contains the following columns:
1. Trade ID
2. Price
3. Quantity
4. Quote Quantity
5. Time
6. Is Buyer Maker
7. Is Best Match

Last updated: $(date)
EOF