import os
import sys
import json
import numpy as np

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import chromadb

CHUNKS_FILE = os.path.join(BASE_DIR, "data", "processed", "chunks.json")
CACHE_FILE = os.path.join(BASE_DIR, "data", "processed", "embeddings_e5.npz")
CHROMA_DIR = os.path.join(BASE_DIR, "data", "chroma_db")

class VectorStore:
    def __init__(self, collection_name: str = "odtu_mevzuat"):
        os.makedirs(CHROMA_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def populate_if_empty(self):

        count = self.collection.count()
        if count > 0:
            print(f"-> [VectorStore] Koleksiyon hazır. Mevcut kayıt sayısı: {count}")
            return

        print("-> [VectorStore] Koleksiyon boş. Veriler yükleniyor...")
        with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        if not os.path.exists(CACHE_FILE):
            raise FileNotFoundError(f"{CACHE_FILE} bulunamadı! Lütfen önce embedding önbelleğini oluşturun.")

        cached_data = np.load(CACHE_FILE)
        vectors = cached_data["embeddings"].tolist()

        ids = [str(c.get("id") or c.get("chunk_id") or f"chunk_{i}") for i, c in enumerate(chunks)]
        documents = [c["text"] for c in chunks]

        metadatas = []
        for c in chunks:
            meta = c.get("metadata", {})
            pages_val = meta.get("pages", "")
            if isinstance(pages_val, list):
                pages_val = f"{pages_val[0]}-{pages_val[-1]}" if len(pages_val) > 1 else str(pages_val[0])
            
            metadatas.append({
                "source": str(meta.get("source", "bilinmeyen")),
                "madde": str(meta.get("madde", "genel")),
                "pages": str(pages_val)
            })

        batch_size = 100
        for i in range(0, len(ids), batch_size):
            self.collection.add(
                ids=ids[i:i + batch_size],
                embeddings=vectors[i:i + batch_size],
                documents=documents[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size]
            )

        print(f"-> [VectorStore] {len(ids)} adet mevzuat parçası başarıyla indekslendi!")

    def search(self, query_vector: list, top_k: int = 3, source_filter: str = None, threshold: float = 0.80):

        where_clause = {"source": source_filter} if source_filter else None

        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where_clause
        )

        retrieved_items = []
        if not results["ids"] or not results["ids"][0]:
            return retrieved_items

        for idx in range(len(results["ids"][0])):
            distance = results["distances"][0][idx]
            similarity = 1.0 - distance

            if similarity < threshold:
                continue

            retrieved_items.append({
                "id": results["ids"][0][idx],
                "text": results["documents"][0][idx],
                "metadata": results["metadatas"][0][idx],
                "score": float(similarity)
            })

        return retrieved_items

def main():
    print("Vektör deposu test ediliyor...")
    store = VectorStore()
    store.populate_if_empty()
    print(f"Koleksiyondaki toplam kayıt: {store.collection.count()}")

if __name__ == "__main__":
    main()