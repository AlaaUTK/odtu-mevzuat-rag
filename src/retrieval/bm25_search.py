import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from rank_bm25 import BM25Okapi

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TOKEN_PATTERN = re.compile(r"\b\w+\b")


def turkish_tokenize(text: str) -> List[str]:
    """
    Türkçe karakter uyumlu küçük harfe dönüştürme ve kelime ayırma.
    """
    if not text:
        return []
    normalized = text.replace("İ", "i").replace("I", "ı").lower()
    return TOKEN_PATTERN.findall(normalized)


class BM25Searcher:
    def __init__(self, chunks_path: Optional[Path] = None):
        self.chunks_path = chunks_path or (BASE_DIR / "data" / "processed" / "chunks.json")
        self.chunks: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.reload()

    def reload(self):
        """chunks.json dosyasını okur ve BM25 indeksini oluşturur."""
        if not self.chunks_path.exists():
            raise FileNotFoundError(f"Chunk dosyası bulunamadı: {self.chunks_path}")

        with open(self.chunks_path, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)

        self.tokenized_corpus = [
            turkish_tokenize(chunk.get("text", ""))
            for chunk in self.chunks
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus) if self.tokenized_corpus else None

    def search(self, query: str, top_k: int = 15, doc_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.bm25 or not self.chunks:
            return []

        tokens = turkish_tokenize(query)
        if not tokens:
            return []

        scores = self.bm25.get_scores(tokens)
        ranked_indices = np.argsort(scores)[::-1]

        active_filter = doc_filter if (doc_filter and doc_filter not in ("Tüm Belgeler", "Tüm Mevzuat")) else None

        results = []
        for idx in ranked_indices:
            score = float(scores[idx])
            # Skorlar azalan sırada olduğundan 0 veya altına düşüldüğünde döngüyü erken sonlandır
            if score <= 0.0:
                break

            raw_chunk = self.chunks[int(idx)]
            if active_filter and raw_chunk.get("document_name") != active_filter:
                continue

            chunk = raw_chunk.copy()
            chunk["bm25_score"] = score
            results.append(chunk)

            if len(results) >= top_k:
                break

        return results
