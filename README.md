# ODTÜ Mevzuat Danışmanı (RAG)

ODTÜ'nün lisans ve lisansüstü yönetmeliklerini, yönergelerini ve usul-esaslarını kapsayan 22 resmî PDF dokümanı üzerinde çalışan, hibrit arama ve yeniden sıralama (reranking) tabanlı bir RAG asistanı.

## Özellikler

- **Hibrit Arama:** Dense Search ve BM25 tabanlı Sparse Search.
- **RRF:** Farklı arama yöntemlerinden gelen sonuçları birleştirme.
- **Reranking:** Cross-Encoder ile sonuçları yeniden sıralama.
- **SSE Streaming:** Yanıtları gerçek zamanlı aktarma.
- **Kapsam Filtresi:** Reranker skoru 0.10 altında kalan sorguları filtreleme.
- **Telemetri:** Sorgu performansını JSONL formatında kaydetme.
- **Artımlı İndeksleme:** Yeni PDF belgelerini sisteme ekleme.

## Teknolojiler

- Python
- Streamlit
- FastAPI
- ClickHouse
- BM25
- Groq API / Qwen
- `intfloat/multilingual-e5-base`
- `BAAI/bge-reranker-v2-m3`

## Benchmark Sonuçları

| Metrik | Sonuç |
|---|---:|
| Hit@4 | %80,00 |
| MRR | %60,83 |
| Relevance Threshold | 0.10 |

## Kurulum

### Gereksinimler

- Python
- Docker
- Groq API anahtarı

### 1. Bağımlılıkları yükleyin

```bash
pip install -r requirements.txt
```
### 2. Ortam değişkenlerini ayarlayın
Proje kök dizininde .env dosyası oluşturun:
```bash
dotenv
GROQ_API_KEY=gsk_sizin_anahtariniz
CLICKHOUSE_PASSWORD=clickhouse123
```
### 3. ClickHouse'u başlatın
```bash
docker run -d \
  --name clickhouse-server \
  -p 8123:8123 \
  -p 9000:9000 \
  --ulimit nofile=262144:262144 \
  -e CLICKHOUSE_PASSWORD=clickhouse123 \
  clickhouse/clickhouse-server
```
### 4. Backend'i başlatın
```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```
### 5. Arayüzü başlatın
```bash
streamlit run app.py
```
Yeni Mevzuat Ekleme
Yeni bir PDF belgesini indekslemek için:

```bash
python scripts/ingest_new_document.py --pdf_path data/raw/yeni_yonerge.pdf
```
## Proje Yapısı

```text
.
├── app.py
├── README.md
├── requirements.txt
├── data/
│   ├── raw/
│   └── processed/
├── logs/
│   └── api_queries.jsonl
├── scripts/
│   ├── evaluate_retrieval.py
│   └── ingest_new_document.py
└── src/
    ├── adapters/
    ├── api/
    ├── llm/
    ├── pipeline/
    ├── retrieval/
    └── utils/
```
## Telemetri
Sorgu gecikmesi, kaynak sayısı, reranker skoru ve işlem durumu logs/api_queries.jsonl dosyasına kaydedilir.
