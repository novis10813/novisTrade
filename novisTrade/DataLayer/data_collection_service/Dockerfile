# 使用官方 Rust 映像作為基礎
FROM rust:1.84.0

# 設置工作目錄
WORKDIR /app

# # 複製整個專案
COPY . .

# 構建專案
RUN cargo build --release

# 運行應用
CMD ["./target/release/data_collection_service"]

# 只複製 Cargo.toml 和 Cargo.lock
# COPY Cargo.toml Cargo.lock ./

# # 建立一個空的 main.rs 來預先編譯依賴
# RUN mkdir src && \
#     echo "fn main() {}" > src/main.rs && \
#     cargo build && \
#     rm -rf src

# # 在容器啟動時編譯和運行
# CMD ["cargo", "run"]
