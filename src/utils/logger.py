import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "query_audit.jsonl"

class AuditLogger:
    @staticmethod
    def log_query(
        query: str,
        rewritten_query: str,
        latency_sec: float,
        is_in_scope: bool,
        top_score: float,
        sources: List[Dict[str, Any]],
        doc_filter: str = None
    ):
        """
        Gelen her kullanıcı sorgusunu yapılandırılmış JSONL formatında kaydeder.
        """
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "rewritten_query": rewritten_query,
            "latency_seconds": round(latency_sec, 3),
            "is_in_scope": is_in_scope,
            "top_rerank_score": round(top_score, 4) if top_score is not None else 0.0,
            "filter_applied": doc_filter if doc_filter else "None",
            "retrieved_sources": [
                {
                    "document": s.get("source") or s.get("document_name"),
                    "article": s.get("madde") or s.get("article"),
                    "score": round(s.get("score") or s.get("rerank_score", 0.0), 4)
                }
                for s in sources
            ]
        }

        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[Logging Hatası] Audit log yazılamadı: {e}")