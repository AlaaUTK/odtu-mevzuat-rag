import sys
from src.pipeline.rag_engine import RAGEngine

def print_separator():
    print("-" * 75)

def main():
    print("=" * 75)
    print("        ODTÜ MEVZUAT ASİSTANI - KURUMSAL RAG CLI PROTOTİPİ (FAZ 1)")
    print("=" * 75)
    print("Sistem hazır. Çıkış yapmak için 'q' veya 'exit' yazabilirsiniz.\n")

    try:
        engine = RAGEngine(top_k=3)
    except Exception as e:
        print(f"Hata: Motor başlatılamadı -> {e}")
        sys.exit(1)

    while True:
        try:
            query = input("\n[SORU SORUN] > ").strip()
            if not query:
                continue
            if query.lower() in ["q", "exit", "cikis"]:
                print("\nSistem kapatılıyor. İyi çalışmalar!")
                break

            print("\nAranıyor ve cevap üretiliyor...")
            result = engine.answer_query(query)

            print_separator()
            print("CEVAP:")
            print(result["answer"])
            print_separator()
            print("KULLANILAN MEVZUAT KAYNAKLARI (TOP-3):")
            for idx, src in enumerate(result["sources"], start=1):
                print(f" {idx}. Belge: {src['source']} | Madde: {src['madde']} | Sayfa: {src['pages']} (Benzerlik: {src['score']:.4f})")
            print_separator()

        except KeyboardInterrupt:
            print("\nİşlem iptal edildi. Çıkılıyor...")
            break
        except Exception as e:
            print(f"\nBir hata oluştu: {e}")

if __name__ == "__main__":
    main()