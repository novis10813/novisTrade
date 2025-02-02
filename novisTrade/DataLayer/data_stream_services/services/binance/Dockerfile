FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製 shared 目錄
COPY services/binance/src /app/src
COPY shared /app/shared

ENV PYTHONPATH=/app

CMD ["python", "src/main.py"]