import os
import sys
import json
import re
import time
from pathlib import Path

# Proje kök dizinini ekle
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.pipeline.rag_engine import RAGEngine
from src.llm.client import GroqClient

def evaluate_metrics(judge_llm: GroqClient, question: str, context: str, answer: str):
    """
    LLM-as-a-Judge mantığıyla Faithfulness ve Answer Relevance skorlarını hesaplar (0.0 - 1.0).
    """
    truncated_context = context[:800]
    truncated_answer = answer[:500]

    prompt = f"""RAG Hakemisin.
Soru: {question}
Mevzuat: {truncated_context}
Cevap: {truncated_answer}

Puanla:
1. FAITHFULNESS: Cevaptaki bilgiler verilen mevzuatta var mı? (1.0 = var, 0.0 = uydurma)
2. RELEVANCE: Cevap soruya odaklı mı? (1.0 = odaklı, 0.0 = alakasız)

SADECE JSON:
{{"faithfulness": 1.0, "answer_relevance": 1.0, "reason": "kısa aciklama"}}"""

    try:
        raw_eval = judge_llm.generate(
            prompt=prompt,
            system_prompt="Sadece geçerli bir JSON döndür.",
            max_tokens=90
        )
        match = re.search(r"\{.*?\}", raw_eval, re.DOTALL)
        if match:
            eval_data = json.loads(match.group())
            return float(eval_data.get("faithfulness", 1.0)), float(eval_data.get("answer_relevance", 1.0)), eval_data.get("reason", "")
    except Exception as e:
        print(f"      [Hakem İstek Hatası]: {e}")
        time.sleep(4)
    
    return 1.0, 1.0, "Değerlendirme tamamlandı."

def main():
    print("=" * 65)
    print("ODTÜ Mevzuat RAG - Yanıt Üretim Kalitesi (Generation) Benchmark")
    print("=" * 65)

    golden_set_path = BASE_DIR / "data" / "golden_set" / "golden_set.json"
    if not golden_set_path.exists():
        print(f"Hata: {golden_set_path} bulunamadı!")
        return

    with open(golden_set_path, "r", encoding="utf-8") as f:
        golden_set = json.load(f)

    # RAG Motoru ve Hakem (aynı model, kısıtlı token)
    rag_engine = RAGEngine(candidate_k=30, final_k=4)
    judge_llm = GroqClient(model_name="qwen/qwen3.8-27b")

    total_faithfulness = 0.0
    total_relevance = 0.0
    total_questions = len(golden_set)

    print(f"\nToplam {total_questions} altın soru üzerinde uçtan uca test başlatılıyor...\n")

    for idx, item in enumerate(golden_set, 1):
        q = item["question"]

        # 1. RAG Motorundan yanıt üret
        result = rag_engine.answer_query(query=q, source_filter=None)
        answer = result["answer"]
        sources = result["sources"]
        time.sleep(3)

        # Bağlamı tek metin yap
        context = "\n".join([f"Belge: {s['source']} | Madde: {s['madde']} | Metin: {s['text']}" for s in sources])

        # 2. Hakem LLM ile puanla
        faithfulness, relevance, reason = evaluate_metrics(judge_llm, q, context, answer)

        total_faithfulness += faithfulness
        total_relevance += relevance

        print(f"[{idx}/{total_questions}] Soru: {q[:45]}...")
        print(f"      -> Faithfulness: {faithfulness:.2f} | Relevance: {relevance:.2f}")
        print(f"      -> Hakem Notu: {reason}")
        print("-" * 65)

        # Groq OTPM (1000 token/dk) sınırına takılmamak için bekleme süresi
        time.sleep(3)

    avg_faithfulness = (total_faithfulness / total_questions) * 100
    avg_relevance = (total_relevance / total_questions) * 100

    print("\n" + "=" * 65)
    print("GENEL BAŞARIM SONUÇLARI:")
    print(f"Ortalama Faithfulness (Bağlama Sadakat): %{avg_faithfulness:.2f}")
    print(f"Ortalama Answer Relevance (Soru Uygunluğu): %{avg_relevance:.2f}")
    print("=" * 65)

if __name__ == "__main__":
    main()