# ODTÜ Mevzuat Danışmanı (RAG)

ODTÜ'nün lisans ve lisansüstü yönetmeliklerini, yönergelerini ve usul-esaslarını kapsayan resmî PDF dokümanları üzerinde çalışan, hibrit arama ve yeniden sıralama (reranking) tabanlı yapay zeka destekli bir RAG (Retrieval-Augmented Generation) asistanı.

## Önemli Özellikler

- **Hibrit Arama:** Dense Search ve BM25 tabanlı Sparse Search entegrasyonu.
- **Yeniden Sıralama (Reranking):** Cross-Encoder ile en alakalı sonuçların filtrelenmesi.
- **Gerçek Zamanlı Yanıt (SSE Streaming):** Groq LLM altyapısıyla akıcı yanıt aktarımı.
- **Otomatik Tohumlama (Auto-Seed):** Docker ile ilk ayağa kalkışta verilerin ve vektörlerin veritabanına otomatik yüklenmesi.
- **Gelişmiş Telemetri:** Sorgu performansının ve sistem metriklerinin anlık olarak kaydedilmesi.

## Teknolojiler

- **Python & FastAPI** (Backend ve API servisi)
- **Streamlit** (Kullanıcı dostu arayüz)
- **ClickHouse** (Yüksek performanslı vektör veritabanı)
- **Groq API / Qwen & Multilingual-e5-base** (Dil modeli ve embedding altyapısı)

## Kurulum ve Çalıştırma

Projeyi bilgisayarınızda (veya sunucuda) çalıştırmak için tek ihtiyacınız **Docker** ve bir **Groq API anahtarıdır**.

### 1. Projeyi Klonlayın

```bash
git clone https://github.com/AlaaUTK/odtu-mevzuat-rag.git
cd odtu-mevzuat-rag
```

### 2. Ortam Değişkenlerini Ayarlayın

Proje kök dizininde bir `.env` dosyası oluşturun ve Groq API anahtarınızı ekleyin:

```env
GROQ_API_KEY=gsk_sizin_api_anahtariniz
CLICKHOUSE_PASSWORD=clickhouse123
```

### 3. Docker ile Tek Komutta Başlatın

Ekstra manuel veritabanı kurulumuna gerek kalmaksızın, sistem tüm verileriyle birlikte tek komutla ayağa kalkar:

```bash
docker compose up --build
```

Sistem hazır olduktan sonra:

- **Streamlit Arayüzü:** `http://localhost:8501` adresinden erişebilirsiniz.
- **FastAPI Backend:** `http://localhost:8000` adresinde çalışır.

## Yeni Mevzuat Ekleme

Sisteme yeni bir PDF belgesi eklemek için `data/raw/` klasörüne dosyayı attıktan sonra şu komutu çalıştırabilirsiniz:

```bash
python scripts/ingest_new_document.py --pdf data/raw/yeni_yonerge.pdf
```

## Proje Yapısı

```text
.
├── app.py                 # Streamlit ön yüz uygulaması
├── Dockerfile             # Konteyner yapılandırması
├── docker-compose.yml     # Servis orkestrasyonu
├── requirements.txt       # Python bağımlılıkları
├── data/
│   ├── raw/               # Ham PDF yönetmelikler
│   └── processed/         # İşlenmiş chunk ve embedding verileri
├── logs/
│   └── api_queries.jsonl  # Telemetri ve sorgu logları
├── scripts/               # Veri işleme ve değerlendirme betikleri
└── src/                   # Backend, LLM ve adaptör modülleri
```
