import sys
from src.pipeline.rag_engine import RAGEngine


def print_separator():
    print("-" * 75)


def main():
    print("=" * 75)
    print("        ODTÜ MEVZUAT ASİSTANI - KURUMSAL RAG CLI")
    print("=" * 75)
    print("Sistem hazır. Çıkış yapmak için 'q' veya 'exit' yazabilirsiniz.\n")

    try:
        engine = RAGEngine(candidate_k=20, final_k=4)
    except Exception as e:
        print(f"Hata: Motor başlatılamadı -> {e}")
        sys.exit(1)

    chat_history = []

    while True:
        try:
            query = input("\n[SORU SORUN] > ").strip()
            if not query:
                continue
            if query.lower() in ["q", "exit", "cikis"]:
                print("\nSistem kapatılıyor. İyi çalışmalar!")
                break

            print("\nAranıyor ve cevap üretiliyor...")
            result = engine.answer_query(query=query, chat_history=chat_history)

            print_separator()
            print("CEVAP:")
            print(result["answer"])
            print_separator()
            print("KULLANILAN MEVZUAT KAYNAKLARI:")
            for idx, src in enumerate(result["sources"], start=1):
                print(f" {idx}. Belge: {src['source']} | Madde: {src['madde']} | Sayfa: {src['pages']} (Uygunluk: {src['score']:.4f})")
            print_separator()

            chat_history.append({"role": "user", "content": query})
            chat_history.append({"role": "assistant", "content": result["answer"]})
            chat_history = chat_history[-8:]

        except KeyboardInterrupt:
            print("\nİşlem iptal edildi. Çıkılıyor...")
            break
        except Exception as e:
            print(f"\nBir hata oluştu: {e}")


if __name__ == "__main__":
    main()
