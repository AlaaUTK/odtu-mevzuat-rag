import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

from sentence_transformers import SentenceTransformer, CrossEncoder
from src.adapters.clickhouse_adapter import ClickHouseVectorDB
from src.retrieval.bm25_search import BM25Searcher
from src.llm.client import GroqClient

ODTU_SYNONYMS = {
    r"\bçap\b": "çift ana dal programı çap",
    r"\byan dal\b": "yan dal programı",
    r"\byandal\b": "yan dal programı",
    r"\bgno\b": "genel not ortalaması",
    r"\böidb\b": "öğrenci işleri daire başkanlığı",
    r"\bwithdraw\b": "dersten çekilme withdraw"
}

def expand_query(query: str) -> str:
    expanded = query.lower()
    for pattern, replacement in ODTU_SYNONYMS.items():
        expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
    return expanded

def reciprocal_rank_fusion(dense_results: List[Dict[str, Any]], bm25_results: List[Dict[str, Any]], k: int = 60) -> List[Dict[str, Any]]:
    """
    Vektör ve BM25 sıralamalarını Reciprocal Rank Fusion (RRF) ile birleştirir.
    """
    fused_scores = {}
    doc_map = {}

    for rank, doc in enumerate(dense_results):
        doc_id = doc.get("chunk_id") or f"{doc['document_name']}_{doc['article']}_{doc['page_start']}"
        fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))
        doc_map[doc_id] = doc

    for rank, doc in enumerate(bm25_results):
        doc_id = doc.get("chunk_id") or f"{doc['document_name']}_{doc['article']}_{doc['page_start']}"
        fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))
        if doc_id not in doc_map:
            doc_map[doc_id] = doc

    sorted_doc_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)
    fused_list = []
    for doc_id in sorted_doc_ids:
        item = doc_map[doc_id].copy()
        item["rrf_score"] = fused_scores[doc_id]
        fused_list.append(item)

    return fused_list

class RAGEngine:
    def __init__(self, candidate_k: int = 15, final_k: int = 4):
        self.candidate_k = candidate_k
        self.final_k = final_k

        print("Embedding modeli (multilingual-e5-base) yükleniyor...")
        self.embed_model = SentenceTransformer("intfloat/multilingual-e5-base")

        print("BM25 arama motoru yükleniyor...")
        self.bm25_searcher = BM25Searcher()

        print("Reranker modeli (BAAI/bge-reranker-v2-m3) yükleniyor...")
        self.reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")

        print("ClickHouse vektör veri tabanına bağlanılıyor...")
        self.db = ClickHouseVectorDB()

        print("LLM istemcisi ilklendiriliyor...")
        self.llm = GroqClient()

    def retrieve(self, query: str, source_filter: str = None):
        enhanced_query = expand_query(query)

        # 1. Aşama A: Vektör Arama (Dense)
        query_text = f"query: {enhanced_query}"
        query_emb = self.embed_model.encode(query_text, normalize_embeddings=True)
        dense_candidates = self.db.search(
            query_embedding=query_emb,
            top_k=self.candidate_k,
            doc_filter=source_filter
        )

        # 1. Aşama B: BM25 Arama (Sparse)
        bm25_candidates = self.bm25_searcher.search(
            query=query,
            top_k=self.candidate_k,
            doc_filter=source_filter
        )

        # 1. Aşama C: Hibrit Harmanlama (RRF)
        fused_candidates = reciprocal_rank_fusion(dense_candidates, bm25_candidates)
        top_candidates = fused_candidates[:self.candidate_k]

        if not top_candidates:
            return []

        # 2. Aşama: Cross-Encoder Reranking
        pairs = [[enhanced_query, c["text"][:600]] for c in top_candidates]
        scores = self.reranker.predict(pairs)

        for candidate, score in zip(top_candidates, scores):
            candidate["rerank_score"] = float(score)

        top_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return top_candidates[:self.final_k]

    def _prepare_prompt(self, query: str, hits: List[Dict[str, Any]]):
        context_blocks = []
        ui_sources = []
        for i, hit in enumerate(hits, 1):
            context_blocks.append(
                f"[Kaynak {i}] Belge: {hit['document_name']} | Madde: {hit['article']} (Sayfa: {hit['page_start']})\n"
                f"Metin: {hit['text']}\n"
            )
            ui_sources.append({
                "source": hit["document_name"],
                "madde": hit["article"],
                "pages": f"{hit['page_start']} - {hit['page_end']}",
                "score": hit.get("rerank_score", 0.0),
                "text": hit["text"]
            })

        context = "\n---\n".join(context_blocks)

        system_prompt = (
            "Sen ODTÜ Mevzuat Danışmanısın. Yalnızca sana verilen mevzuat bağlamına dayanarak net, resmi ve eksiksiz bir dille yanıt ver. "
            "Bağlamda yer almayan hiçbir bilgiyi kendinden ekleme ve tahmin yürütme. "
            "Kullanıcı bir koşul sorduğunda bağlamdaki farklı aşamaları (başvuru, devam, mezuniyet gibi) net şekilde ayır. "
            "Her bilginin dayandığı belge adını ve madde numarasını mutlaka açıkça belirt."
        )

        user_prompt = f"Mevzuat Bağlamı:\n{context}\n\nKullanıcı Sorusu: {query}\n\nYanıt:"
        return system_prompt, user_prompt, ui_sources

    def answer_query(self, query: str, source_filter: str = None, chat_history: Optional[List[Dict[str, str]]] = None):
        search_query = query
        if chat_history:
            search_query = self.llm.rewrite_query(query=query, history=chat_history)
            if search_query != query:
                print(f"[Query Rewriter] Orijinal: '{query}' -> Yeniden Yazılan: '{search_query}'")

        hits = self.retrieve(query=search_query, source_filter=source_filter)

        if not hits:
            return {
                "answer": "Sorunuzla ilgili ODTÜ mevzuatında doğrudan bir madde bulunamadı.",
                "sources": [],
                "rewritten_query": search_query
            }

        system_prompt, user_prompt, ui_sources = self._prepare_prompt(query, hits)
        answer = self.llm.generate(prompt=user_prompt, system_prompt=system_prompt)

        return {
            "answer": answer,
            "sources": ui_sources,
            "rewritten_query": search_query
        }

    def answer_query_stream(self, query: str, source_filter: str = None, chat_history: Optional[List[Dict[str, str]]] = None):
        """
        Streamlit için yanıtı token token yield eden jeneratör ve kaynakları döndürür.
        """
        search_query = query
        if chat_history:
            search_query = self.llm.rewrite_query(query=query, history=chat_history)
            if search_query != query:
                print(f"[Query Rewriter] Orijinal: '{query}' -> Yeniden Yazılan: '{search_query}'")

        hits = self.retrieve(query=search_query, source_filter=source_filter)

        if not hits:
            def empty_generator():
                yield "Sorunuzla ilgili ODTÜ mevzuatında doğrudan bir madde bulunamadı."
            return empty_generator(), [], search_query

        system_prompt, user_prompt, ui_sources = self._prepare_prompt(query, hits)
        stream_generator = self.llm.generate_stream(prompt=user_prompt, system_prompt=system_prompt)

        return stream_generator, ui_sources, search_query