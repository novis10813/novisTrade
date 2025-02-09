#!/bin/bash

# 獲取當前腳本所在的目錄的絕對路徑
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 設置 PYTHONPATH 為專案根目錄
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

# 從專案根目錄執行 main.py
python app/run.py --dev