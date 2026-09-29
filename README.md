# ODTÜ Mevzuat Asistanı: İki Aşamalı Kurumsal RAG Sistemi

Bu proje, Orta Doğu Teknik Üniversitesi (ODTÜ) Bilgi İşlem Daire Başkanlığı bünyesinde yürütülen İş Yeri Uygulaması (Staj) kapsamında geliştirilmiştir. Projenin amacı; kurumsal mevzuat külliyatı üzerinde halüsinasyonsuz, kaynak gösteren ve yüksek doğruluklu bir Bilgi Getirme ve Üretim (RAG) sistemi inşa etmektir.

##  Mimari Genel Bakış

Sistem iki aşamalı bir getirme (two-stage retrieval) mimarisi üzerine kuruludur:

1. **Analitik Vektör Deposu (ClickHouse):** 8 mevzuat belgesinden çıkarılan 631 yapısal madde chunk'ı `intfloat/multilingual-e5-base` modeli ile vektörleştirilerek ClickHouse üzerinde kosinüs mesafesiyle taranır (İlk aşama: Top-8 aday).

2. **Yeniden Sıralama (Cross-Encoder):** Aday havuzu `BAAI/bge-reranker-v2-m3` modeli ile çapraz doğrulamadan geçirilir ve en alakalı Top-3 madde seçilir.

3. **Deterministik Üretim (LLM):** Seçilen kaynaklar, katı sistem kurallarıyla donatılmış Groq API (`qwen/qwen3.8-27b`, temperature=0.0) modeline enjekte edilerek kaynak atıflı resmi yanıt üretilir.

##  Benchmark & Başarım (Golden Dataset)

20 soruluk referans test seti (`data/golden_set/golden_set.json`) üzerinde yapılan ölçüm sonuçları:

* **Hit@1:** %65.00
* **Hit@3:** %90.00
* **MRR (Mean Reciprocal Rank):** 0.7583

##  Kurulum ve Çalıştırma

### 1. Servislerin Başlatılması (Docker)

```bash
docker compose up -d
```

### 2. Bağımlılıkların Yüklenmesi

```bash
python -m venv venv
```

**Windows:**

```bash
.\venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

### 3. Ortam Değişkenleri

```bash
python -m venv venv
```

**Windows:**

```bash
.\venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

### 4. Arayüzü Başlatma

```bash
streamlit run app.py
```
