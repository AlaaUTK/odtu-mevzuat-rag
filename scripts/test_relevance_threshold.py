import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.pipeline.rag_engine import RAGEngine

def main():
    engine = RAGEngine(candidate_k=15, final_k=4)

    test_queries = [
        # İlgili (Mevzuat) Soruları
        ("İlgili", "ÇAP programına kimler başvurabilir?"),
        ("İlgili", "Yurtlardan kesin çıkarma cezası hangi durumlarda verilir?"),
        
        # Kapsam Dışı / Alakasız Sorular
        ("Kapsam Dışı", "Ankara'da bugün hava durumu nasıl?"),
        ("Kapsam Dışı", "Python dilinde iki sayıyı toplayan fonksiyon yaz"),
        ("Kapsam Dışı", "Kızılay'dan ODTÜ'ye hangi dolmuş gider?"),
        ("Kapsam Dışı", "Merhaba, nasılsın?")
    ]

    print("\n" + "=" * 70)
    print(f"{'Kategori':<12} | {'En Yüksek Rerank Skoru':<22} | {'Soru'}")
    print("=" * 70)

    for category, query in test_queries:
        hits = engine.retrieve(query=query)
        if hits:
            top_score = hits[0]["rerank_score"]
            print(f"{category:<12} | {top_score:<22.4f} | {query}")
        else:
            print(f"{category:<12} | {'Aday Bulunamadı':<22} | {query}")

    print("=" * 70)

if __name__ == "__main__":
    main()