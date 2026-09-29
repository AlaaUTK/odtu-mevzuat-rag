import os
import json
import time
import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS_FILE = os.path.join(BASE_DIR, "data", "processed", "chunks.json")

print("1. Chunk verisi yükleniyor...")
with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Toplam yüklenecek parça sayısı: {len(chunks)}")

print("\n2. Embedding modeli yükleniyor (multilingual-e5-base)...")
t0 = time.time()
model = SentenceTransformer("intfloat/multilingual-e5-base")
print(f"Model hazır! Süre: {time.time() - t0:.2f} sn")

texts = [f"passage: {c['text']}" for c in chunks]

print("\n3. 185 parça vektörleştiriliyor (embedding generation)...")
t1 = time.time()
corpus_embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
print(f"Embedding tamamlandı! Süre: {time.time() - t1:.2f} sn | Vektör boyutu: {corpus_embeddings.shape[1]}")

def search(query_text: str, top_k: int = 3):
    print("\n" + "=" * 70)
    print(f"SORGU: '{query_text}'")
    print("=" * 70)
    
    query_vector = model.encode([f"query: {query_text}"], normalize_embeddings=True)[0]
    
    scores = np.dot(corpus_embeddings, query_vector)
    top_indices = np.argsort(scores)[::-1][:top_k]
    
    for rank, idx in enumerate(top_indices, start=1):
        c = chunks[idx]
        score = scores[idx]
        meta = c["metadata"]
        print(f"\n[SIRA {rank}] Benzerlik Skoru: {score:.4f}")
        print(f"Belge: {meta['source']} | Madde: {meta['madde']} | Sayfa: {meta['pages']}")
        print(f"Metin: {c['text'][:250]}...")

search("Çift anadal programına başvurabilmek için not ortalaması en az kaç olmalıdır?")
search("Yurttan çıkarma cezasını gerektiren durumlar nelerdir?")