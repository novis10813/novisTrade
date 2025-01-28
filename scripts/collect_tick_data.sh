#!/bin/bash

python dataCollector.py \
    --channels "binance:spot:btcusdt:aggTrade" "binance:spot:ethusdt:aggTrade" \
    --ws_uri "ws://localhost:8766" \
    --data_dir "./Data"