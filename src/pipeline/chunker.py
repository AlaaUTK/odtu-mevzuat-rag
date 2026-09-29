import os
import re
import json
from pathlib import Path
import fitz  # PyMuPDF

ARTICLE_LABEL_PATTERN = re.compile(
    r'^(?:GEÇİCİ\s+)?MADDE\s*[-–—:.]*\s*(\d+)',
    re.IGNORECASE
)

def clean_text(text: str) -> str:
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def extract_chunks_from_pdf(pdf_path: Path, max_words_per_chunk: int = 250, overlap_words: int = 30):
    doc = fitz.open(pdf_path)
    doc_name = pdf_path.name
    all_chunks = []

    full_doc_lines = []
    page_map = []

    for page_num in range(len(doc)):
        text = doc[page_num].get_text("text")
        for line in text.splitlines():
            line_str = line.strip()
            if line_str:
                full_doc_lines.append(line_str)
                page_map.append(page_num + 1)
    doc.close()

    if not full_doc_lines:
        return []

    # Madde başlangıçlarını tespit et (Önündeki başlığı da maddeye dahil et)
    article_indices = []
    for idx, line in enumerate(full_doc_lines):
        m = ARTICLE_LABEL_PATTERN.match(line)
        if m:
            prefix = "GEÇİCİ MADDE " if "GEÇİCİ" in line.upper() else "MADDE "
            start_idx = idx
            
            # Eğer bir önceki satır kısa bir başlıksa (örn: "Kontenjanlar"), o satırı da bu maddenin başına al
            if idx > 0:
                prev_line = full_doc_lines[idx - 1]
                if len(prev_line.split()) <= 4 and not ARTICLE_LABEL_PATTERN.match(prev_line):
                    start_idx = idx - 1

            article_indices.append((start_idx, f"{prefix}{m.group(1)}"))

    if not article_indices:
        words = " ".join(full_doc_lines).split()
        for i in range(0, len(words), max_words_per_chunk - overlap_words):
            chunk_text = " ".join(words[i:i + max_words_per_chunk])
            all_chunks.append({
                "chunk_id": f"{doc_name}_1_{i}",
                "document_name": doc_name,
                "article": "GENEL",
                "page_start": 1,
                "page_end": len(doc),
                "text": clean_text(chunk_text)
            })
        return all_chunks

    # Giriş kısmı
    first_art_start = article_indices[0][0]
    if first_art_start > 0:
        pre_lines = full_doc_lines[:first_art_start]
        all_chunks.append({
            "chunk_id": f"{doc_name}_intro",
            "document_name": doc_name,
            "article": "GENEL",
            "page_start": 1,
            "page_end": page_map[first_art_start - 1],
            "text": clean_text(" ".join(pre_lines))
        })

    for i in range(len(article_indices)):
        start_line_idx, article_label = article_indices[i]
        end_line_idx = article_indices[i + 1][0] if i + 1 < len(article_indices) else len(full_doc_lines)

        art_lines = full_doc_lines[start_line_idx:end_line_idx]
        start_page = page_map[start_line_idx]
        end_page = page_map[end_line_idx - 1]

        art_text = " ".join(art_lines)
        words = art_text.split()

        if len(words) <= max_words_per_chunk:
            all_chunks.append({
                "chunk_id": f"{doc_name}_{article_label.replace(' ', '_')}_0",
                "document_name": doc_name,
                "article": article_label,
                "page_start": start_page,
                "page_end": end_page,
                "text": clean_text(art_text)
            })
        else:
            step = max_words_per_chunk - overlap_words
            sub_id = 0
            for w_idx in range(0, len(words), step):
                sub_words = words[w_idx:w_idx + max_words_per_chunk]
                sub_text = " ".join(sub_words)
                all_chunks.append({
                    "chunk_id": f"{doc_name}_{article_label.replace(' ', '_')}_{sub_id}",
                    "document_name": doc_name,
                    "article": article_label,
                    "page_start": start_page,
                    "page_end": end_page,
                    "text": clean_text(sub_text)
                })
                sub_id += 1
                if w_idx + max_words_per_chunk >= len(words):
                    break

    return all_chunks

def run_chunking():
    root = Path(__file__).resolve().parent.parent.parent
    raw_dir = root / "data" / "raw"
    processed_dir = root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(list(raw_dir.glob("*.pdf")))
    total_chunks = []
    for pdf_file in pdf_files:
        chunks = extract_chunks_from_pdf(pdf_file)
        total_chunks.extend(chunks)

    output_path = processed_dir / "chunks.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(total_chunks, f, ensure_ascii=False, indent=2)

    print(f"Başarılı! Toplam chunk sayısı: {len(total_chunks)}")

if __name__ == "__main__":
    run_chunking()