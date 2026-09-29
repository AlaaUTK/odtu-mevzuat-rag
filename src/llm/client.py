import os
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
from groq import Groq

# .env dosyasını mutlak yol ile yükle
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

class GroqClient:
    def __init__(self, model_name: str = "qwen/qwen3.8-27b", temperature: float = 0.0):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY .env dosyasında bulunamadı!")
            
        self.client = Groq(api_key=self.api_key)
        self.model_name = model_name
        self.temperature = temperature

    def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 400) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

    def rewrite_query(self, query: str, history: List[Dict[str, str]]) -> str:
        if not history:
            return query

        history_context = ""
        for turn in history[-6:]:
            role_label = "Kullanıcı" if turn.get("role") == "user" else "Asistan"
            history_context += f"{role_label}: {turn.get('content', '')}\n"

        prompt = f"""Aşağıdaki konuşma geçmişini ve kullanıcının son sorusunu incele.
Kullanıcının son sorusunu, konuşma geçmişindeki atıfları (zamirler, ima edilen konular, belgeler) yerine koyarak ODTÜ mevzuat veritabanında aratılabilecek bağımsız, tekil bir soru cümlesi haline getir.

KURALLAR:
1. Kesinlikle soruya yanıt verme!
2. Sadece ve sadece yeniden yazılmış soruyu döndür.
3. Eğer soru zaten tek başına net ve anlaşılırsa veya geçmişle ilgisi yoksa aynen bırak.

Konuşma Geçmişi:
{history_context}

Kullanıcının Son Sorusu: {query}

Yeniden Yazılmış Soru:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=80
            )
            rewritten = response.choices[0].message.content.strip().strip('"')
            return rewritten if rewritten else query
        except Exception:
            return query