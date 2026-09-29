import os
import json
import time
import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS_FILE = os.path.join(BASE_DIR, "data", "processed", "chunks.json")

TEST_QUERIES = [
    {
        "id": "q1_lisans_azami",
        "query": "Lisans öğrenimini tamamlama için tanınan azami süre kaç yıldır?",
        "expected_doc": "lisans_yonetmeligi.pdf"
    },
    {
        "id": "q2_lisansustu_juri",
        "query": "Tezli yüksek lisans programında tez savunma jürisi kimlerden ve kaç kişiden oluşur?",
        "expected_doc": "lisansustu_yonetmeligi.pdf"
    },
    {
        "id": "q3_cap_not_sarti",
        "query": "Çift anadal programına başvurabilmek için aranan genel not ortalaması şartı nedir?",
        "expected_doc": "cap_yonergesi.pdf"
    },
    {
        "id": "q4_yurt_kinama",
        "query": "Yurtta kalan bir öğrenciye kınama cezasını hangi yetkili organ verir?",
        "expected_doc": "yurtlar_yonetmeligi.pdf"
    }
]

MODELS = [
    {
        "name": "multilingual-e5-base",
        "id": "intfloat/multilingual-e5-base",
        "prefix_passage": "passage: ",
        "prefix_query": "query: "
    },
    {
        "name": "bge-m3",
        "id": "BAAI/bge-m3",
        "prefix_passage": "", 
        "prefix_query": ""
    }
]

def run_benchmark():
    print("=" * 70)
    print("      EMBEDDING MODELLERİ KIYASLAMA VE BENCHMARK TESTİ (FAZ 1)")
    print("=" * 70)

    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"Toplam test edilecek mevzuat parçası: {len(chunks)}\n")

    benchmark_results = {}

    for m in MODELS:
        print(f"\n[MODEL TESTİ]: {m['name']} ({m['id']})")
        print("-" * 50)
        
        # 1. Modeli Yükle
        start_load = time.time()
        model = SentenceTransformer(m["id"])
        load_time = time.time() - start_load
        print(f"-> Model yüklenme süresi: {load_time:.2f} sn")

        # 2. 185 Chunk'ı Vektörleştir
        corpus_texts = [f"{m['prefix_passage']}{c['text']}" for c in chunks]
        start_enc = time.time()
        embeddings = model.encode(corpus_texts, normalize_embeddings=True, show_progress_bar=False)
        enc_time = time.time() - start_enc
        emb_dim = embeddings.shape[1]
        print(f"-> 185 chunk vektörleştirme süresi: {enc_time:.2f} sn (Boyut: {emb_dim})")
        print(f"-> Hız: {len(chunks) / enc_time:.1f} chunk/sn")

        query_evals = []
        for q in TEST_QUERIES:
            query_text = f"{m['prefix_query']}{q['query']}"
            q_vec = model.encode([query_text], normalize_embeddings=True)[0]
            
            scores = np.dot(embeddings, q_vec)
            top_indices = np.argsort(scores)[::-1][:3]
            
            top1_chunk = chunks[top_indices[0]]
            top1_doc = top1_chunk["metadata"]["source"]
            top1_score = float(scores[top_indices[0]])
            top2_score = float(scores[top_indices[1]])
            margin = top1_score - top2_score
            is_match = (top1_doc == q["expected_doc"])

            query_evals.append({
                "query_id": q["id"],
                "target_doc": q["expected_doc"],
                "top1_doc": top1_doc,
                "top1_madde": top1_chunk["metadata"]["madde"],
                "top1_score": top1_score,
                "margin": margin,
                "success": is_match
            })

        benchmark_results[m["name"]] = {
            "load_time": load_time,
            "enc_time": enc_time,
            "dim": emb_dim,
            "queries": query_evals
        }

    print("\n" + "=" * 70)
    print("                    SONUÇ KARŞILAŞTIRMA ÖZETİ")
    print("=" * 70)
    print(f"{'Metrik / Soru':<25} | {'multilingual-e5-base':<20} | {'bge-m3':<20}")
    print("-" * 70)
    print(f"{'Vektör Boyutu':<25} | {benchmark_results['multilingual-e5-base']['dim']:<20} | {benchmark_results['bge-m3']['dim']:<20}")
    print(f"{'Kodlama Süresi (185 chk)':<25} | {benchmark_results['multilingual-e5-base']['enc_time']:.2f} sn{'':<15} | {benchmark_results['bge-m3']['enc_time']:.2f} sn{'':<15}")
    print("-" * 70)

    for idx, q in enumerate(TEST_QUERIES):
        e5_res = benchmark_results["multilingual-e5-base"]["queries"][idx]
        bge_res = benchmark_results["bge-m3"]["queries"][idx]
        print(f"{q['id']:<25} | Skor: {e5_res['top1_score']:.4f} (M:{e5_res['margin']:.3f}) | Skor: {bge_res['top1_score']:.4f} (M:{bge_res['margin']:.3f})")

if __name__ == "__main__":
    run_benchmark()