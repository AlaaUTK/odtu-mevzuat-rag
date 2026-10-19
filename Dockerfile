# Python tabanlı resmi hafif imajı kullanıyoruz
FROM python:3.11-slim

# Çalışma dizinini ayarla
WORKDIR /app

# Sistem bağımlılıkları (gereken derleme araçları vb.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/api/lists/*

# Bağımlılık dosyasını kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarının tamamını container içine kopyala
COPY . .

# Varsayılan portları tanımla (FastAPI: 8000, Streamlit: 8501)
EXPOSE 8000
EXPOSE 8501