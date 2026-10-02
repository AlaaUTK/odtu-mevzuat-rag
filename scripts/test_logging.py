import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.pipeline.rag_engine import RAGEngine

def main():
    print("Loglama testi başlatılıyor...")
    engine = RAGEngine(candidate_k=15, final_k=4)

    # 1. Kapsam İçi Soru
    print("\n--- Test 1: Kapsam İçi Soru Gönderiliyor ---")
    resp1 = engine.answer_query("ÇAP programına başvuru koşulları nelerdir?")
    print(f"Cevap Başlangıcı: {resp1['answer'][:80]}...")

    # 2. Kapsam Dışı Soru
    print("\n--- Test 2: Kapsam Dışı Soru Gönderiliyor ---")
    resp2 = engine.answer_query("Bugün hava kaç derece?")
    print(f"Cevap: {resp2['answer']}")

    # Log dosyasını kontrol et
    log_path = BASE_DIR / "logs" / "query_audit.jsonl"
    print("\n" + "=" * 65)
    if log_path.exists():
        print(f"BAŞARILI: {log_path} dosyası oluşturuldu!")
        print("Kayıt Edilen Son Satırlar:")
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f.readlines()[-2:]:
                print(line.strip())
    else:
        print("HATA: Log dosyası bulunamadı!")
    print("=" * 65)

if __name__ == "__main__":
    main()