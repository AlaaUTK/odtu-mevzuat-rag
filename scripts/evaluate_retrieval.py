import os
import sys
import json
import re
import argparse
from pathlib import Path

# Proje kök dizinini ekle
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.pipeline.rag_engine import RAGEngine

def normalize_article(article_str: str) -> str:
    """Madde metninden sadece sayısal kısmı ayıklar (Örn: 'MADDE 14' -> '14')."""
    match = re.search(r"\d+", str(article_str))
    return match.group() if match else str(article_str).strip()

def main():
    parser = argparse.ArgumentParser(description="Retrieval Benchmark Parametre Testi")
    parser.add_argument("--candidate_k", type=int, default=15, help="Reranker'a giren aday havuzu büyüklüğü")
    parser.add_argument("--final_k", type=int, default=4, help="LLM'e giden nihai bağlam parça sayısı")
    args = parser.parse_args()

    print("=" * 65)
    print(f"ODTÜ Mevzuat RAG - Retrieval Benchmark (candidate_k={args.candidate_k}, final_k={args.final_k})")
    print("=" * 65)

    golden_set_path = BASE_DIR / "data" / "golden_set" / "golden_set.json"
    if not golden_set_path.exists():
        print(f"Hata: {golden_set_path} bulunamadı!")
        return

    with open(golden_set_path, "r", encoding="utf-8") as f:
        golden_set = json.load(f)

    # Parametrik RAG motorunu başlat
    engine = RAGEngine(candidate_k=args.candidate_k, final_k=args.final_k)

    total_questions = len(golden_set)
    hit_at_1 = 0
    hit_at_3 = 0
    hit_at_4 = 0
    reciprocal_ranks = []

    print(f"\nToplam {total_questions} altın soru üzerinde test başlatılıyor...\n")

    for idx, item in enumerate(golden_set, 1):
        question = item["question"]
        expected_doc = item["expected_document"]
        expected_article = normalize_article(item["expected_article"])

        retrieved_docs = engine.retrieve(query=question, source_filter=None)

        ranks = []
        for rank, doc in enumerate(retrieved_docs, start=1):
            retrieved_doc_name = doc.get("document_name", "")
            retrieved_article = normalize_article(doc.get("article", ""))

            if retrieved_doc_name == expected_doc and retrieved_article == expected_article:
                ranks.append(rank)

        if ranks:
            best_rank = min(ranks)
            reciprocal_ranks.append(1.0 / best_rank)
            if best_rank == 1:
                hit_at_1 += 1
            if best_rank <= 3:
                hit_at_3 += 1
            if best_rank <= 4:
                hit_at_4 += 1
            status = f"BAŞARILI (Sıra: {best_rank})"
        else:
            reciprocal_ranks.append(0.0)
            status = f"BAŞARISIZ (İlk {args.final_k}'te yok)"

        print(f"[{idx:02d}/{total_questions:02d}] {question[:45]}... -> {status}")

    hit_1_rate = (hit_at_1 / total_questions) * 100
    hit_3_rate = (hit_at_3 / total_questions) * 100
    hit_4_rate = (hit_at_4 / total_questions) * 100
    mrr = (sum(reciprocal_ranks) / total_questions) * 100

    print("\n" + "=" * 65)
    print(f"SONUÇLAR (candidate_k={args.candidate_k}):")
    print(f"Hit@1: %{hit_1_rate:.2f} ({hit_at_1}/{total_questions})")
    print(f"Hit@3: %{hit_3_rate:.2f} ({hit_at_3}/{total_questions})")
    print(f"Hit@4: %{hit_4_rate:.2f} ({hit_at_4}/{total_questions})")
    print(f"MRR: %{mrr:.2f}")
    print("=" * 65)

if __name__ == "__main__":
    main()