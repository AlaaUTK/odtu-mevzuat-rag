"""
scripts/ingest_new_document.py

Yeni PDF mevzuat belgelerini veya kılavuzları sisteme entegre eden uçtan uca boru hattı.
- Belgelerde MADDE varsa madde bazlı ayrıştırır.
- Kılavuz tarzı (MADDE içermeyen) belgelerde pencereleme (windowing) yöntemiyle dengeli parçalar üretir.
- Metinleri multilingual-e5-base ile vektörleştirir.
- ClickHouse'a idempotent (varsa eskisini silip) yazar.
- BM25 (chunks.json) ve Auto-Seed (embeddings_e5.npz) dosyalarını senkronize eder.
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF
import numpy as np
from sentence_transformers import SentenceTransformer

# Proje kök dizinini ekle
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.adapters.clickhouse_adapter import ClickHouseVectorDB

ARTICLE_PATTERN = re.compile(
    r'(?:^|\n)\s*(?:(?:GEÇİCİ|GECICI)\s+)?(?:MADDE|Madde)\s*[-–—:.]*\s*(\d+)',
    re.MULTILINE
)


def extract_pdf_pages(pdf_path: str) -> List[Dict[str, Any]]:
    doc = fitz.open(pdf_path)
    pages = []
    for idx in range(len(doc)):
        text = doc[idx].get_text("text") or ""
        pages.append({"page_num": idx + 1, "text": text})
    doc.close()
    return pages


def parse_guideline_content(full_text: str, doc_name: str, total_pages: int = 1) -> List[Dict[str, Any]]:
    """MADDE formatında olmayan kılavuzları 120-180 kelimelik dengeli parçalara böler."""
    chunks = []
    lines = [line.strip() for line in full_text.splitlines() if line.strip() and not line.strip().isdigit()]

    current_lines = []
    current_words = 0
    part_idx = 1

    for line in lines:
        words = line.split()
        if current_words + len(words) > 160 and current_lines:
            combined_text = " ".join(current_lines)
            summary_title = current_lines[0][:40].strip()
            chunks.append({
                "article": f"KISIM {part_idx} ({summary_title})",
                "text": f"[{doc_name} - KISIM {part_idx}]\n{combined_text}",
                "page_start": 1,
                "page_end": max(1, total_pages)
            })
            part_idx += 1
            current_lines = [line]
            current_words = len(words)
        else:
            current_lines.append(line)
            current_words += len(words)

    if current_lines:
        combined_text = " ".join(current_lines)
        summary_title = current_lines[0][:40].strip()
        chunks.append({
            "article": f"KISIM {part_idx} ({summary_title})",
            "text": f"[{doc_name} - KISIM {part_idx}]\n{combined_text}",
            "page_start": 1,
            "page_end": max(1, total_pages)
        })

    return chunks


def parse_document_to_chunks(pdf_path: str) -> List[Dict[str, Any]]:
    doc_name = os.path.basename(pdf_path)
    pages = extract_pdf_pages(pdf_path)
    full_text = "\n".join([f"[SAYFA {p['page_num']}]\n{p['text']}" for p in pages])

    matches = list(ARTICLE_PATTERN.finditer(full_text))

    # MADDE bulunamadıysa kılavuz ayrıştırıcısını devreye sok
    if len(matches) < 2:
        raw_full_text = "\n".join([p["text"] for p in pages])
        guide_chunks = parse_guideline_content(raw_full_text, doc_name, total_pages=len(pages))
        result = []
        for i, c in enumerate(guide_chunks):
            result.append({
                "chunk_id": f"{doc_name}_part_{i+1}",
                "document_name": doc_name,
                "article": c["article"],
                "text": c["text"],
                "page_start": c["page_start"],
                "page_end": c["page_end"],
                "source": doc_name
            })
        return result

    # Standart Madde Bazlı Ayrıştırma
    chunks = []
    for i in range(len(matches)):
        start_pos = matches[i].start()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)

        match_text = matches[i].group(0).strip()
        article_num = matches[i].group(1)
        article_label = (
            f"GEÇİCİ MADDE {article_num}"
            if ("GEÇİCİ" in match_text.upper() or "GECICI" in match_text.upper())
            else f"MADDE {article_num}"
        )

        chunk_raw = full_text[start_pos:end_pos].strip()

        page_matches = re.findall(r'\[SAYFA (\d+)\]', chunk_raw)
        p_start = int(page_matches[0]) if page_matches else 1
        p_end = int(page_matches[-1]) if page_matches else p_start

        clean_text = re.sub(r'\[SAYFA \d+\]\n?', '', chunk_raw).strip()

        chunks.append({
            "chunk_id": f"{doc_name}_{article_label.replace(' ', '_')}_{i}",
            "document_name": doc_name,
            "article": article_label,
            "text": clean_text,
            "page_start": p_start,
            "page_end": p_end,
            "source": doc_name
        })

    return chunks


def sync_local_artifacts(
    new_chunks: List[Dict[str, Any]],
    new_embeddings: np.ndarray,
    doc_name: str,
    processed_dir: Path = BASE_DIR / "data" / "processed"
):
    """chunks.json ve embeddings_e5.npz dosyalarını birlikte senkronize eder."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    json_path = processed_dir / "chunks.json"
    npz_path = processed_dir / "embeddings_e5.npz"

    all_chunks: List[Dict[str, Any]] = []
    old_embeddings = None

    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            all_chunks = json.load(f)

    if npz_path.exists():
        try:
            with np.load(npz_path) as data:
                key = data.files[0]
                old_embeddings = data[key]
        except Exception:
            old_embeddings = None

    if old_embeddings is not None and len(old_embeddings) == len(all_chunks):
        keep_indices = [i for i, c in enumerate(all_chunks) if c.get("document_name") != doc_name]
        filtered_chunks = [all_chunks[i] for i in keep_indices]
        if keep_indices:
            kept_embs = old_embeddings[keep_indices]
            combined_embs = np.vstack([kept_embs, new_embeddings])
        else:
            combined_embs = new_embeddings
        filtered_chunks.extend(new_chunks)
        np.savez_compressed(npz_path, embeddings=combined_embs)
    else:
        filtered_chunks = [c for c in all_chunks if c.get("document_name") != doc_name]
        filtered_chunks.extend(new_chunks)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(filtered_chunks, f, ensure_ascii=False, indent=2)
    print(f"[OK] Yerel veri dosyaları güncellendi. Toplam parça: {len(filtered_chunks)}")


def ingest_pdf(pdf_path: str, client: ClickHouseVectorDB, embedder: SentenceTransformer):
    doc_name = os.path.basename(pdf_path)
    print("\n==========================================")
    print(f"İşleniyor: {doc_name}")
    print("==========================================")

    chunks = parse_document_to_chunks(pdf_path)
    if not chunks:
        print(f"[HATA] {doc_name} dosyasından parça çıkarılamadı!")
        return 0
    print(f"-> {len(chunks)} parça çıkarıldı.")

    texts_to_embed = [f"passage: {c['text']}" for c in chunks]
    print("-> Vektörleştiriliyor (multilingual-e5-base)...")
    embeddings = embedder.encode(texts_to_embed, normalize_embeddings=True, show_progress_bar=False)

    print("-> ClickHouse eski kayıtlar temizleniyor (idempotent)...")
    client.delete_by_document(doc_name)

    print(f"-> ClickHouse'a {len(chunks)} parça ekleniyor...")
    client.insert_chunks(chunks, embeddings)

    sync_local_artifacts(chunks, embeddings, doc_name)
    print(f"[BAŞARILI] {doc_name} sisteme entegre edildi.")
    return len(chunks)


def main():
    parser = argparse.ArgumentParser(description="PDF Mevzuat Belgesini Sisteme Entegre Et")
    parser.add_argument("--pdf", "--pdf_path", dest="pdf", type=str, help="İşlenecek tekil PDF dosyasının yolu")
    parser.add_argument("--all-new", action="store_true", help="data/raw altındaki henüz işlenmemiş tüm PDF'leri sırayla ekle")
    args = parser.parse_args()

    client = ClickHouseVectorDB()
    embedder = SentenceTransformer("intfloat/multilingual-e5-base")

    if args.all_new:
        chunks_file = BASE_DIR / "data" / "processed" / "chunks.json"
        raw_dir = BASE_DIR / "data" / "raw"
        existing_docs = set()
        if chunks_file.exists():
            with open(chunks_file, "r", encoding="utf-8") as f:
                existing_docs = {c.get("document_name") for c in json.load(f)}

        raw_files = [f for f in os.listdir(raw_dir) if f.endswith(".pdf")]
        to_process = [f for f in raw_files if f not in existing_docs]

        print(f"Taranan PDF: {len(raw_files)} | Zaten Yüklü: {len(existing_docs)} | Yüklenecek Yeni: {len(to_process)}")
        for doc_file in to_process:
            ingest_pdf(str(raw_dir / doc_file), client, embedder)
        print("\n[TAMAMLANDI] Tüm yeni belgeler başarıyla yüklendi!")

    elif args.pdf:
        if not os.path.exists(args.pdf):
            print(f"Dosya bulunamadı: {args.pdf}")
            return
        ingest_pdf(args.pdf, client, embedder)
    else:
        print("Lütfen --pdf <dosya_yolu> veya --all-new parametresi verin.")


if __name__ == "__main__":
    main()
