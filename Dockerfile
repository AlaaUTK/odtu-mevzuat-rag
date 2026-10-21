# Python tabanlı resmi hafif imaj
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Sistem bağımlılıkları
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılık dosyasını kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını container içine kopyala
COPY . .

# Varsayılan portları tanımla (FastAPI: 8000, Streamlit: 8501)
EXPOSE 8000
EXPOSE 8501
