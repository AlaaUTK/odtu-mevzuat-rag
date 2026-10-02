Orta Doğu Teknik Üniversitesi (ODTÜ) lisans ve lisansüstü
yönetmelikleri, yönergeleri ve usul esasları üzerinde çalışan; hibrit
arama, yeniden sıralama (reranking) ve dil modeli entegrasyonuna sahip
kurumsal seviye bir Soru-Cevap (RAG) asistanıdır.

------------------------------------------------------------------------

## Mimari Genel Bakış

Sistem, geleneksel salt vektör aramalarının (Naive RAG) hukuki/akademik
metinlerde yaşadığı bağlam kaybını ve halüsinasyon risklerini bertaraf
etmek amacıyla çok aşamalı bir arama ve doğrulama hattı (Pipeline)
kullanır:

1.  Kullanıcı Sorusu
2.  Query Rewriter (LLM): Konuşma geçmişinden bağımsız net arama sorgusu
    üretir.
3.  Hibrit Arama (Hybrid Search):
    -   Dense Arama: intfloat/multilingual-e5-base + ClickHouse Vector
        DB
    -   Sparse Arama: BM25 (rank_bm25)
4.  Aday Birleştirme: Reciprocal Rank Fusion (RRF) ile Top-15 aday
    havuzu oluşturulur.
5.  Cross-Encoder Reranker: BAAI/bge-reranker-v2-m3 modeli ile adaylar
    yeniden skorlanır.
6.  Relevance Threshold (0.10): Eşik altı sorgular LLM çağrılmadan
    kapsam dışı olarak elenir.
7.  Yanıt Üretimi: qwen/qwen3.8-27b modeli üzerinden akışkan (streaming)
    ve üstel geri çekilmeli (retry/backoff) yanıt üretilir.
8.  Denetim ve Kayıt: logs/query_audit.jsonl dosyasına yapılandırılmış
    audit log basılır.

------------------------------------------------------------------------

## Öne Çıkan Özellikler

-   Hibrit Arama (Dense + Sparse): ClickHouse üzerinde kosinüs
    benzerliği ile semantik arama, BM25 ile doğrudan yönetmelik ve madde
    numarası araması.
-   RRF ve Cross-Encoder Yeniden Sıralama: Çift yönlü arama sonuçları
    Reciprocal Rank Fusion ile harmanlanır ve BAAI/bge-reranker-v2-m3
    modeliyle en yüksek alaka düzeyine göre sıralanır.
-   Kapsam Dışı Soru Koruması (Relevance Thresholding): Reranker taban
    skoru 0.10 altında kalan sorular LLM inference adımına girmeden
    reddedilir; token israfı ve halüsinasyon riski sıfırlanır.
-   Hata Toleransı ve Dayanıklılık (Resilience): Groq LLM çağrıları
    üstel geri çekilme (exponential backoff) ve otomatik yeniden deneme
    (retry) mekanizmasıyla korunur.
-   Yapılandırılmış Günlükleme (Audit Trail): Her sorgu, gecikme süresi,
    dönen mevzuat referansları ve rerank skorlarıyla
    logs/query_audit.jsonl kütüğüne işlenir.
-   Modüler Belge Alma (Idempotent Ingestion): Sisteme yeni bir PDF
    yönerge eklendiğinde tüm veritabanını yeniden kurmadan, mükerrer
    kayıt oluşturmadan doğrudan ClickHouse ve BM25 dizinlerine yazma
    imkânı.

------------------------------------------------------------------------

## Benchmark ve Değerlendirme Sonuçları

ODTÜ mevzuatına dair 20 farklı altın soru (Golden Test Set) üzerinden
yapılan nesnel ölçüm sonuçları:

-   Hit@4: %80.00 (İlgili mevzuat maddesinin ilk 4 bağlamda bulunma
    oranı)
-   MRR: %60.83 (Doğru maddenin sıralamadaki ortalama başarı skoru)
-   Aday Havuzu (k): 15 (Reranker modeline beslenen optimum aday parça
    sayısı)
-   Relevance Threshold: 0.10 (Kapsam dışı sorgu ayrıştırma eşik değeri)

------------------------------------------------------------------------

## Kurulum ve Çalıştırma

### 1. Gereksinimler ve Sanal Ortam

``` bash
pip install -r requirements.txt
pip install pypdf
```

### 2. Ortam Değişkenleri (.env)

Proje kök dizininde .env dosyasını oluşturun:

``` env
GROQ_API_KEY=gsk_...
CLICKHOUSE_PASSWORD=clickhouse123
```

### 3. ClickHouse Vektör Veritabanını Başlatma

``` bash
docker run -d --name clickhouse-server -p 8123:8123 -p 9000:9000 --ulimit nofile=262144:262144 -e CLICKHOUSE_PASSWORD=clickhouse123 clickhouse/clickhouse-server
```

### 4. Arayüzü Başlatma

``` bash
streamlit run app.py
```

------------------------------------------------------------------------

## Yeni Bir Yönetmelik / Yönerge Ekleme

Yeni bir PDF belgesini sisteme artımlı (incremental) ve tekilleştirme
garantili olarak eklemek için:

``` bash
python scripts/ingest_new_document.py --pdf_path data/raw/yeni_yonerge.pdf
```

------------------------------------------------------------------------

## Proje Dizin Yapısı

-   data/raw: Ham PDF yönergeler ve yönetmelikler
-   data/processed: BM25 indeks parçaları (chunks.json)
-   logs/query_audit.jsonl: Yapılandırılmış sorgu denetim logları
-   scripts/evaluate_retrieval.py: Retrieval benchmark ölçüm aracı
-   scripts/ingest_new_document.py: Idempotent yeni PDF indeksleme boru
    hattı
-   scripts/test_logging.py: Denetim ve dayanıklılık doğrulama betiği
-   src/adapters: ClickHouse vektör veritabanı sürücüsü
-   src/llm: Groq API istemcisi (Backoff retry destekli)
-   src/pipeline: RAG Engine, RRF, Hybrid Search ve Reranker
-   src/utils: Yapılandırılmış audit logger
-   app.py: Streamlit web arayüzü
-   README.md: Dokümantasyon
