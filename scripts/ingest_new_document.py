import os
import sys
import json
import re
import uuid
import argparse
from pathlib import Path
from typing import List, Dict, Any
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

# Proje kök dizini
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.adapters.clickhouse_adapter import ClickHouseVectorDB

def extract_chunks_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Verilen PDF dosyasını okur ve madde bazlı chunk'lara böler.
    """
    reader = PdfReader(str(pdf_path))
    doc_name = pdf_path.name
    full_pages = []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = re.sub(r"[ \t]+", " ", text).strip()
        full_pages.append((page_num, text))

    article_pattern = re.compile(r"(MADDE\s+\d+|Geçici\s+Madde\s+\d+)", re.IGNORECASE)

    chunks = []
    current_article = "GİRİŞ / GENEL HÜKÜMLER"
    current_text = []
    start_page = 1

    for page_num, text in full_pages:
        lines = text.split("\n")
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            match = article_pattern.match(line_clean)
            if match:
                if current_text:
                    body = " ".join(current_text).strip()
                    if len(body) > 40:
                        chunks.append({
                            "chunk_id": f"{doc_name}_{current_article.replace(' ', '_')}_{start_page}_{str(uuid.uuid4())[:6]}",
                            "document_name": doc_name,
                            "article": current_article,
                            "page_start": start_page,
                            "page_end": page_num,
                            "text": f"{current_article}\n{body}"
                        })
                current_article = match.group().upper()
                current_text = [line_clean[match.end():].strip()]
                start_page = page_num
            else:
                current_text.append(line_clean)

    if current_text:
        body = " ".join(current_text).strip()
        if len(body) > 40:
            chunks.append({
                "chunk_id": f"{doc_name}_{current_article.replace(' ', '_')}_{start_page}_{str(uuid.uuid4())[:6]}",
                "document_name": doc_name,
                "article": current_article,
                "page_start": start_page,
                "page_end": len(reader.pages),
                "text": f"{current_article}\n{body}"
            })

    return chunks

def main():
    parser = argparse.ArgumentParser(description="Mevcut RAG sistemine yeni bir PDF yönerge ekler.")
    parser.add_argument("--pdf_path", type=str, required=True, help="Eklenecek PDF dosyasının yolu")
    args = parser.parse_args()

    pdf_file = Path(args.pdf_path)
    if not pdf_file.exists():
        print(f"Hata: Belirtilen PDF dosyası bulunamadı: {pdf_file}")
        return

    print("=" * 65)
    print(f"YENİ DOKÜMAN İŞLEME VE İNDEKSLEME: {pdf_file.name}")
    print("=" * 65)

    # 1. PDF'ten chunk'ları ayıkla
    print("\n[1/4] PDF okunuyor ve maddelere ayrıştırılıyor...")
    new_chunks = extract_chunks_from_pdf(pdf_file)
    print(f"-> Toplam {len(new_chunks)} adet mevzuat chunk'ı oluşturuldu.")

    if not new_chunks:
        print("Uyarı: PDF'ten geçerli bir madde/metin bloğu çıkarılamadı.")
        return

    # 2. Embedding üretimi (E5-base)
    print("\n[2/4] multilingual-e5-base ile vektörler hesaplanıyor...")
    embed_model = SentenceTransformer("intfloat/multilingual-e5-base")
    passages = [f"passage: {c['text']}" for c in new_chunks]
    embeddings = embed_model.encode(passages, normalize_embeddings=True, show_progress_bar=True)

    # 3. ClickHouse'a ekleme (Mevcut insert_chunks imzasını kullanıyoruz)
    print("\n[3/4] ClickHouse veritabanına aktarılıyor...")
    db = ClickHouseVectorDB()
    
    # Eskileri temizle (Idempotent yükleme)
    db.delete_by_document(pdf_file.name)
    
    # Yenileri ekle
    db.insert_chunks(chunks=new_chunks, embeddings=embeddings)

    # 4. chunks.json (BM25 verisi) senkronizasyonu
    print("\n[4/4] data/processed/chunks.json güncelleniyor (BM25 senkronizasyonu)...")
    chunks_path = BASE_DIR / "data" / "processed" / "chunks.json"
    
    existing_chunks = []
    if chunks_path.exists():
        with open(chunks_path, "r", encoding="utf-8") as f:
            existing_chunks = json.load(f)

    # Idempotency: Eğer bu doküman daha önce eklendiyse eskilerini temizle
    filtered_chunks = [c for c in existing_chunks if c.get("document_name") != pdf_file.name]
    
    # Yeni parçaları listeye ekle
    filtered_chunks.extend(new_chunks)

    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(filtered_chunks, f, ensure_ascii=False, indent=2)

    print(f"-> chunks.json güncellendi. Toplam parça sayısı: {len(filtered_chunks)}")
    print("\n" + "=" * 65)
    print(f"BAŞARILI: '{pdf_file.name}' hem Vektör (ClickHouse) hem Sparse (BM25) aramaya dahil edildi!")
    print("=" * 65)

if __name__ == "__main__":
    main()