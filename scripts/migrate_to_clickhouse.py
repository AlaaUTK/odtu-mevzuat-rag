import json
import time
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from src.adapters.clickhouse_adapter import ClickHouseVectorDB

def main():
    # scripts/ içinden proje kök dizinine (..) çıkış
    root = Path(__file__).resolve().parent.parent
    chunks_path = root / "data" / "processed" / "chunks.json"
    cache_path = root / "data" / "processed" / "embeddings_e5.npz"

    print("1. Chunks dosyası okunuyor...")
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"Toplam {len(chunks)} adet chunk yüklendi.")

    print("\n2. Embedding modeli (multilingual-e5-base) yükleniyor...")
    model = SentenceTransformer("intfloat/multilingual-e5-base")

    passages = [f"passage: {c['text']}" for c in chunks]

    if cache_path.exists():
        print(f"\n3. Hazır vektör önbelleği bulundu, diskten yükleniyor: {cache_path}")
        embeddings = np.load(cache_path)["embeddings"]
    else:
        print(f"\n3. {len(passages)} chunk vektörleştiriliyor (CPU)...")
        start_time = time.time()
        embeddings = model.encode(passages, normalize_embeddings=True, show_progress_bar=True)
        np.savez_compressed(cache_path, embeddings=embeddings)

    print("\n5. ClickHouse'a veri aktarımı başlatılıyor...")
    db = ClickHouseVectorDB()
    
    db.client.command(f"TRUNCATE TABLE IF EXISTS {db.table_name}")
    db.insert_chunks(chunks, embeddings)

    print("\n--- Test Arama Doğrulaması ---")
    test_emb = embeddings[0]
    hits = db.search(test_emb, top_k=1)
    print("Test eşleşmesi (kendi skoru ~1.0 olmalı):")
    print(f"Belge: {hits[0]['document_name']} | Madde: {hits[0]['article']} | Skor: {hits[0]['similarity']:.4f}")

if __name__ == "__main__":
    main()