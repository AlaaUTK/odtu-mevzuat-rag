ODTÜ Mevzuat Danışmanı (RAG)

ODTÜ'nün lisans ve lisansüstü yönetmeliklerini, yönergelerini ve usul-esaslarını kapsayan 22 resmî PDF dokümanı üzerinde çalışan, hibrit arama ve yeniden sıralama (reranking) tabanlı bir Retrieval-Augmented Generation (RAG) asistanı.

Sistem, ilgili mevzuat maddelerini bulmak için anlamsal ve anahtar kelime tabanlı aramayı birleştirir; yanıtları kaynak bağlamına dayandırarak üretir.

Özellikler
Hibrit Arama: Dense Search (vektör arama) ve BM25 tabanlı Sparse Search.
RRF: Farklı arama yöntemlerinden gelen sonuçları birleştirme.
Cross-Encoder Reranking: Aday sonuçları alaka düzeyine göre yeniden sıralama.
SSE Streaming: Yanıtları kullanıcı arayüzüne gerçek zamanlı aktarma.
Kapsam Filtresi: Reranker skoru 0.10 altında kalan sorguları LLM çağrısından önce eleme.
Mikroservis Mimarisi: FastAPI backend ve Streamlit istemcisinin ayrılması.
Telemetri: Sorgu gecikmesi, kaynak sayısı ve skorların JSONL formatında kaydedilmesi.
Artımlı İndeksleme: Yeni mevzuat PDF'lerini sisteme ekleyebilme.
Mimari
flowchart TD
    A["Streamlit UI<br/>:8501"] --> B["FastAPI Backend<br/>:8000"]
    B --> C["Query Rewriter"]
    C --> D["Dense Search<br/>E5 + ClickHouse"]
    C --> E["Sparse Search<br/>BM25"]
    D --> F["RRF"]
    E --> F
    F --> G["Cross-Encoder Reranker"]
    G --> H{"Skor >= 0.10?"}
    H -- Evet --> I["Groq API / Qwen"]
    H -- Hayır --> J["Kapsam Dışı Yanıt"]
    I --> K["SSE ile Yanıt Akışı"]
    K --> A
    B --> L["JSONL Telemetri"]

Teknoloji yığını
Bileşen	Teknoloji
Arayüz	Streamlit
Backend	FastAPI, Uvicorn
Vektör veritabanı	ClickHouse
Embedding modeli	intfloat/multilingual-e5-base
Reranker modeli	BAAI/bge-reranker-v2-m3
LLM	Groq API / Qwen
Sparse arama	BM25
Sonuç birleştirme	Reciprocal Rank Fusion (RRF)
İletişim	HTTP / Server-Sent Events (SSE)
Benchmark Sonuçları

ODTÜ mevzuatına ait altın soru seti (Golden Test Set) üzerinde elde edilen bilgi getirme sonuçları:

Metrik	Sonuç
Hit@4	%80,00
MRR	%60,83
Relevance Threshold	0.10
Hit@4: Doğru mevzuat maddesinin ilk dört sonuç arasında bulunma oranı.
MRR: Doğru sonucun sıralamadaki konumunu dikkate alan ortalama karşılıklı sıra.

Bu metrikler bilgi getirme performansını ölçer; uçtan uca yanıt doğruluğunu tek başına göstermez.

Kurulum
Gereksinimler
Python
Docker
Groq API anahtarı
1. Bağımlılıkları yükleyin
pip install -r requirements.txt

2. Ortam değişkenlerini tanımlayın

Proje kök dizininde .env dosyası oluşturun:

GROQ_API_KEY=gsk_sizin_anahtariniz
CLICKHOUSE_PASSWORD=clickhouse123

3. ClickHouse'u başlatın
docker run -d \
  --name clickhouse-server \
  -p 8123:8123 \
  -p 9000:9000 \
  --ulimit nofile=262144:262144 \
  -e CLICKHOUSE_PASSWORD=clickhouse123 \
  clickhouse/clickhouse-server

4. Backend'i başlatın
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000

5. Arayüzü başlatın

Yeni bir terminalde:

streamlit run app.py

Not: ClickHouse veritabanı şemasının oluşturulması ve ilk belgelerin indekslenmesi için projenin ilgili başlatma ve indeksleme adımlarının da tamamlanmış olması gerekir.
Yeni Mevzuat Ekleme

Yeni bir PDF belgesini indekslemek için:

python scripts/ingest_new_document.py \
  --pdf_path data/raw/yeni_yonerge.pdf

Proje Yapısı
.
├── app.py
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
