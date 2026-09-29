import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import json
from sentence_transformers import SentenceTransformer, CrossEncoder
from src.adapters.clickhouse_adapter import ClickHouseVectorDB

def run_evaluation(use_reranker: bool = True, candidate_k: int = 10, final_k: int = 3):
    golden_path = ROOT_DIR / "data" / "golden_set" / "golden_set.json"
    if not golden_path.exists():
        print(f"Hata: {golden_path} bulunamadı!")
        return

    with open(golden_path, "r", encoding="utf-8") as f:
        golden_set = json.load(f)

    print(f"Altın Soru Havuzu: {len(golden_set)} soru")
    print("Embedding modeli ve ClickHouse bağlantısı hazırlanıyor...")

    embed_model = SentenceTransformer("intfloat/multilingual-e5-base")
    db = ClickHouseVectorDB()

    reranker = None
    if use_reranker:
        print("Reranker modeli (BAAI/bge-reranker-v2-m3) yükleniyor...")
        # Çok dilli (Türkçe uyumlu) güçlü reranker
        reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")

    hit_at_1 = 0
    hit_at_3 = 0
    reciprocal_ranks = []
    missed_questions = []

    print(f"\n--- Değerlendirme Başlatılıyor (Reranker={'AÇIK (Candidate-K: ' + str(candidate_k) + ')' if use_reranker else 'KAPALI'}) ---\n")

    for item in golden_set:
        q_id = item["id"]
        question = item["question"]
        exp_doc = item["expected_document"].strip().lower()
        exp_art = item["expected_article"].strip().lower()

        # 1. Aşama: ClickHouse'dan aday havuzu çek (Top-10)
        query_text = f"query: {question}"
        query_emb = embed_model.encode(query_text, normalize_embeddings=True)
        candidates = db.search(query_embedding=query_emb, top_k=candidate_k)

        # 2. Aşama: Reranker ile yeniden sırala
        if use_reranker and reranker and candidates:
            # Soru ile her aday metni çift olarak veriyoruz
            pairs = [[question, c["text"]] for c in candidates]
            scores = reranker.predict(pairs)
            
            # Skorlara göre adayları büyükten küçüğe diz
            scored_candidates = list(zip(candidates, scores))
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            hits = [item[0] for item in scored_candidates[:final_k]]
        else:
            hits = candidates[:final_k]

        found_rank = 0
        for rank, hit in enumerate(hits, start=1):
            doc_match = (hit["document_name"].strip().lower() == exp_doc)
            art_match = (exp_art in hit["article"].strip().lower())

            if doc_match and art_match:
                found_rank = rank
                break

        if found_rank == 1:
            hit_at_1 += 1
            hit_at_3 += 1
            reciprocal_ranks.append(1.0)
            print(f"[{q_id:02d}] HIT@1 | {question[:45]}...")
        elif 1 < found_rank <= 3:
            hit_at_3 += 1
            reciprocal_ranks.append(1.0 / found_rank)
            print(f"[{q_id:02d}] HIT@{found_rank} | {question[:45]}...")
        else:
            reciprocal_ranks.append(0.0)
            print(f"[{q_id:02d}] MISSED | {question[:45]}...")
            missed_questions.append({
                "id": q_id,
                "question": question,
                "expected": f"{exp_doc} -> {exp_art}",
                "retrieved": [f"{h['document_name']} ({h['article']})" for h in hits]
            })

    total_q = len(golden_set)
    hit_1_score = (hit_at_1 / total_q) * 100
    hit_3_score = (hit_at_3 / total_q) * 100
    mrr_score = sum(reciprocal_ranks) / total_q

    print("\n" + "="*45)
    print("      DEĞERLENDİRME METRİK SONUÇLARI      ")
    print("="*45)
    print(f"Reranker Durumu    : {'Aktif (Candidate-K: ' + str(candidate_k) + ')' if use_reranker else 'Devre Dışı'}")
    print(f"Toplam Test Sorusu : {total_q}")
    print(f"Hit@1 Başarımı     : %{hit_1_score:.2f} ({hit_at_1}/{total_q})")
    print(f"Hit@3 Başarımı     : %{hit_3_score:.2f} ({hit_at_3}/{total_q})")
    print(f"MRR Skoru          : {mrr_score:.4f}")
    print("="*45)

    if missed_questions:
        print("\n--- İsabet Sağlanamayan Soruların Analizi ---")
        for m in missed_questions:
            print(f"Soru [{m['id']}]: {m['question']}")
            print(f"  Beklenen : {m['expected']}")
            print(f"  Gelenler : {', '.join(m['retrieved'])}\n")

if __name__ == "__main__":
    run_evaluation(use_reranker=True, candidate_k=15, final_k=3)