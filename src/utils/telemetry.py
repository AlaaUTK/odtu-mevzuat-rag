import os
import json
import time
from datetime import datetime
from pathlib import Path

# Proje kök dizini ve log dizini
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "api_queries.jsonl"


class TelemetryLogger:
    @staticmethod
    def log_query(
        query: str,
        rewritten_query: str,
        source_count: int,
        top_score: float,
        latency_ms: float,
        is_stream: bool = False,
        error: str = None
    ):
        """
        Sorgu metriklerini JSON Lines formatında dosyaya yazar ve konsola özet basar.
        """
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query": query,
            "rewritten_query": rewritten_query,
            "source_count": source_count,
            "top_score": round(top_score, 4),
            "latency_ms": round(latency_ms, 2),
            "is_stream": is_stream,
            "status": "ERROR" if error else "SUCCESS",
            "error": error
        }

        # 1. JSONL Dosyasına Ekle
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[Telemetry Hata] Dosyaya yazılamadı: {e}")

        # 2. Konsola Yapılandırılmış Bilgi Bas
        status_tag = f"\033[91m[ERROR]\033[0m" if error else f"\033[92m[SUCCESS]\033[0m"
        stream_tag = "[STREAM]" if is_stream else "[SYNC]"
        print(
            f"{status_tag} {stream_tag} Latency: {log_entry['latency_ms']}ms | "
            f"Sources: {source_count} (Top: {log_entry['top_score']}) | "
            f"Q: '{query[:40]}...'"
        )