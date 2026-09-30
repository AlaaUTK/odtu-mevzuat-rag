import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def turkish_tokenize(text: str) -> List[str]:
    """
    Türkçe karakter uyumlu küçük harfe dönüştürme ve kelime ayırma.
    """
    text = text.replace("İ", "i").replace("I", "ı").lower()
    tokens = re.findall(r"\b\w+\b", text)
    return tokens

class BM25Searcher:
    def __init__(self, chunks_path: Optional[Path] = None):
        if chunks_path is None:
            chunks_path = BASE_DIR / "data" / "processed" / "chunks.json"

        if not chunks_path.exists():
            raise FileNotFoundError(f"Chunk dosyası bulunamadı: {chunks_path}")

        with open(chunks_path, "r", encoding="utf-8") as f:
            self.chunks: List[Dict[str, Any]] = json.load(f)

        # Her chunk'ı tokenize et
        self.tokenized_corpus = [
            turkish_tokenize(chunk.get("text", ""))
            for chunk in self.chunks
        ]
        
        # BM25 indeksini oluştur
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def search(self, query: str, top_k: int = 15, doc_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        tokens = turkish_tokenize(query)
        if not tokens:
            return []

        scores = self.bm25.get_scores(tokens)

        # Adayları puanlarıyla eşle
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        results = []
        for idx in ranked_indices:
            score = float(scores[idx])
            if score <= 0:
                continue

            chunk = self.chunks[idx].copy()
            
            # Doküman filtresi varsa uygula
            if doc_filter and chunk.get("document_name") != doc_filter:
                continue

            chunk["bm25_score"] = score
            results.append(chunk)

            if len(results) >= top_k:
                break

        return results