import os
import time
from typing import List, Dict, Generator
from groq import Groq, RateLimitError, APIConnectionError, InternalServerError
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

class GroqClient:
    def __init__(self, model_name: str = "qwen/qwen3.8-27b"):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY ortam değişkeni bulunamadı. Lütfen .env dosyasını kontrol edin.")
        self.client = Groq(api_key=self.api_key)
        self.model_name = model_name

    def generate(self, prompt: str, system_prompt: str = None, max_retries: int = 3, max_tokens: int = 512) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content
            except (RateLimitError, APIConnectionError, InternalServerError) as e:
                wait_time = (2 ** attempt) + 1
                print(f"[Groq Uyarı] API hatası ({e}). {wait_time}s sonra yeniden deneniyor... (Deneme {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    return "Üzgünüz, şu anda dil modeli servisinde geçici bir yoğunluk yaşanıyor. Lütfen sorunuzu birkaç saniye sonra tekrar deneyiniz."
                time.sleep(wait_time)
            except Exception as e:
                print(f"[Groq Hata] Beklenmeyen hata: {e}")
                return "Sistemsel bir hata oluştu. Lütfen sistem yöneticisi ile iletişime geçiniz."

    def generate_stream(self, prompt: str, system_prompt: str = None, max_retries: int = 3) -> Generator[str, None, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(max_retries):
            try:
                stream = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=max_tokens,
                    stream=True,
                )
                for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
                return  # Başarıyla bitti
            except (RateLimitError, APIConnectionError, InternalServerError) as e:
                wait_time = (2 ** attempt) + 1
                print(f"[Groq Stream Uyarı] API hatası ({e}). {wait_time}s sonra yeniden deneniyor... (Deneme {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    yield "⚠️ *Üzgünüz, dil modeli servisinde geçici bir yoğunluk veya bağlantı sorunu yaşanıyor. Lütfen sorunuzu birazdan tekrar yöneltiniz.*"
                    return
                time.sleep(wait_time)
            except Exception as e:
                print(f"[Groq Stream Hata] Beklenmeyen hata: {e}")
                yield "⚠️ *Sorgu yanıtlanırken beklenmeyen bir hata oluştu.*"
                return

    def rewrite_query(self, query: str, history: List[Dict[str, str]]) -> str:
        """
        Geçmiş konuşmayı kullanarak örtük zamirleri/bağlamları tekil ve açık bir arama sorgusuna dönüştürür.
        """
        if not history:
            return query

        formatted_history = ""
        for msg in history[-4:]:
            role = "Kullanıcı" if msg["role"] == "user" else "Asistan"
            formatted_history += f"{role}: {msg['content']}\n"

        prompt = (
            "Aşağıdaki konuşma geçmişini ve son kullanıcı sorusunu dikkate alarak, "
            "arama motorunun (vektör/BM25) en iyi mevzuat maddesini bulabilmesi için soruyu tek bir açık, müstakil ve net sorguya dönüştür.\n"
            "Örtük zamirleri ('bunun', 'onun', 'bu durumda') önceki bağlamla tamamla.\n"
            "YALNIZCA üretilen yeni sorgu cümlesini yaz, tırnak işareti, açıklama veya ek metin ekleme.\n\n"
            f"Konuşma Geçmişi:\n{formatted_history}\n"
            f"Son Kullanıcı Sorusu: {query}\n"
            "Yeniden Yazılmış Sorgu:"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100,
            )
            rewritten = response.choices[0].message.content.strip().strip('"').strip("'")
            return rewritten if rewritten else query
        except Exception:
            return query