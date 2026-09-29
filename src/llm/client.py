import os
from pathlib import Path
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

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature
        )
        return response.choices[0].message.content