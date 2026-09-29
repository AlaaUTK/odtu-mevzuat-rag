from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer, CrossEncoder
from src.adapters.clickhouse_adapter import ClickHouseVectorDB

class RetrievalService:
    def __init__(
        self,
        embed_model_name: str = "intfloat/multilingual-e5-base",
        reranker_model_name: str = "BAAI/bge-reranker-v2-m3"
    ):
        self.embed_model = SentenceTransformer(embed_model_name)
        self.reranker = CrossEncoder(reranker_model_name)
        self.db = ClickHouseVectorDB()

    def retrieve(
        self,
        query: str,
        candidate_k: int = 15,
        final_k: int = 3,
        doc_filter: str = None
    ) -> List[Dict[str, Any]]:
        # 1. Aşama: Query Embedding & ClickHouse Aday Havuzu
        query_text = f"query: {query}"
        query_emb = self.embed_model.encode(query_text, normalize_embeddings=True)
        
        candidates = self.db.search(
            query_embedding=query_emb,
            top_k=candidate_k,
            doc_filter=doc_filter
        )

        if not candidates:
            return []

        # 2. Aşama: Cross-Encoder ile Yeniden Sıralama (Reranking)
        pairs = [[query, c["text"]] for c in candidates]
        scores = self.reranker.predict(pairs)

        for candidate, score in zip(candidates, scores):
            candidate["rerank_score"] = float(score)

        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return candidates[:final_k]