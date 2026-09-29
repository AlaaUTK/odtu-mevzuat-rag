import os
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

from sentence_transformers import SentenceTransformer, CrossEncoder
from src.adapters.clickhouse_adapter import ClickHouseVectorDB
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

class RAGEngine:
    def __init__(self, candidate_k: int = 8, final_k: int = 3):
        self.candidate_k = candidate_k
        self.final_k = final_k

        print("Embedding modeli (multilingual-e5-base) yükleniyor...")
        self.embed_model = SentenceTransformer("intfloat/multilingual-e5-base")

        print("Reranker modeli (BAAI/bge-reranker-v2-m3) yükleniyor...")
        self.reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")

        print("ClickHouse vektör veri tabanına bağlanılıyor...")
        self.db = ClickHouseVectorDB()

        print("LLM istemcisi ilklendiriliyor...")
        self.llm = GroqClient()

    def retrieve(self, query: str, source_filter: str = None):
        # Sorgu Genişletme (çap -> çift ana dal)
        enhanced_query = expand_query(query)

        # 1. Aşama: ClickHouse Aday Havuzu (Hız için 8 aday kafi)
        query_text = f"query: {enhanced_query}"
        query_emb = self.embed_model.encode(query_text, normalize_embeddings=True)
        candidates = self.db.search(
            query_embedding=query_emb,
            top_k=self.candidate_k,
            doc_filter=source_filter
        )

        if not candidates:
            return []

        # 2. Aşama: Hızlı Reranking (Maksimum 8 aday, 0.5 - 1 sn sürer)
        pairs = [[enhanced_query, c["text"][:600]] for c in candidates]
        scores = self.reranker.predict(pairs)

        for candidate, score in zip(candidates, scores):
            candidate["rerank_score"] = float(score)

        candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return candidates[:self.final_k]

    def answer_query(self, query: str, source_filter: str = None):
        hits = self.retrieve(query=query, source_filter=source_filter)

        if not hits:
            return {
                "answer": "Sorunuzla ilgili ODTÜ mevzuatında doğrudan bir madde bulunamadı.",
                "sources": []
            }

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
            "Her bilginin dayandığı belge adını ve madde numarasını mutlaka açıkça belirt."
        )

        user_prompt = f"Mevzuat Bağlamı:\n{context}\n\nKullanıcı Sorusu: {query}\n\nYanıt:"
        answer = self.llm.generate(prompt=user_prompt, system_prompt=system_prompt)

        return {
            "answer": answer,
            "sources": ui_sources
        }