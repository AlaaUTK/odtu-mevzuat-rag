import os
import sys
import json
import time
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

# Proje kök dizinini Python yoluna ekle
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.pipeline.rag_engine import RAGEngine
from src.utils.telemetry import TelemetryLogger
from src.api.schemas import (
    HealthResponse,
    QueryRequest,
    QueryResponse,
    SourceMetadata
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Uygulama başlarken RAG motorunu tek sefer yükle (Singleton)
    print("\n--- [FastAPI] RAG Motoru Yükleniyor (Singleton) ---")
    app.state.rag_engine = RAGEngine(
        candidate_k=20,
        final_k=4,
        score_threshold=0.10
    )
    print("--- [FastAPI] Sistem Başarıyla Hazırlandı ---\n")
    yield
    print("\n--- [FastAPI] Servis Kapatılıyor ---")


app = FastAPI(
    title="ODTÜ Mevzuat RAG API",
    description="ODTÜ Yönetmelik ve Yönergeleri için Semantik Arama ve Yanıt Servisi",
    version="1.0.0",
    lifespan=lifespan
)

# CORS yapılandırması (Wildcard origin ile credentials=False standart uyumluluğu)
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=("*" not in cors_origins),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["Sistem"])
async def health_check():
    """Sistemin ve API servisinin ayakta olup olmadığını kontrol eder."""
    return HealthResponse(status="ok", version="1.0.0")


@app.post("/api/v1/query", response_model=QueryResponse, tags=["RAG Servisi"])
async def query_rag(request_data: QueryRequest, request: Request):
    """
    Kullanıcı sorusunu alır, standart senkron JSON yanıtı döndürür.
    CPU/IO yoğun işlemler asyncio.to_thread ile çalıştırılarak event loop korunur.
    """
    rag_engine: RAGEngine = request.app.state.rag_engine
    start_time = time.perf_counter()

    try:
        history_list = None
        if request_data.chat_history:
            history_list = [
                {"role": msg.role, "content": msg.content}
                for msg in request_data.chat_history
            ]

        result = await asyncio.to_thread(
            rag_engine.answer_query,
            query=request_data.query,
            source_filter=request_data.source_filter,
            chat_history=history_list
        )

        sources_list = [
            SourceMetadata(
                source=src.get("source", ""),
                madde=src.get("madde", ""),
                pages=str(src.get("pages", "")),
                score=float(src.get("score", 0.0)),
                text=src.get("text", "")
            )
            for src in result.get("sources", [])
        ]

        is_in_scope = len(sources_list) > 0
        rewritten = result.get("rewritten_query", request_data.query)
        latency_ms = (time.perf_counter() - start_time) * 1000
        top_score = sources_list[0].score if sources_list else 0.0

        TelemetryLogger.log_query(
            query=request_data.query,
            rewritten_query=rewritten,
            source_count=len(sources_list),
            top_score=top_score,
            latency_ms=latency_ms,
            is_stream=False
        )

        return QueryResponse(
            answer=result.get("answer", ""),
            sources=sources_list,
            rewritten_query=rewritten,
            is_in_scope=is_in_scope
        )

    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        TelemetryLogger.log_query(
            query=request_data.query,
            rewritten_query=request_data.query,
            source_count=0,
            top_score=0.0,
            latency_ms=latency_ms,
            is_stream=False,
            error=str(e)
        )
        print(f"[API Hata] /api/v1/query çalışırken hata: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Sorgu işlenirken bir sunucu hatası oluştu."
        )


@app.post("/api/v1/query/stream", tags=["RAG Servisi"])
async def query_rag_stream(request_data: QueryRequest, request: Request):
    """
    Server-Sent Events (SSE) ile token ve kaynak akışı sağlar.
    """
    rag_engine: RAGEngine = request.app.state.rag_engine
    start_time = time.perf_counter()

    history_list = None
    if request_data.chat_history:
        history_list = [
            {"role": msg.role, "content": msg.content}
            for msg in request_data.chat_history
        ]

    async def event_generator():
        rewritten_final = request_data.query
        source_count = 0
        top_score = 0.0

        try:
            # Durum 1: Sohbet geçmişi varsa bağlamsal sorgu çözümleme
            if history_list:
                yield {
                    "event": "status",
                    "data": json.dumps({"text": "Soru analiz ediliyor ve bağlam çözümleniyor..."}, ensure_ascii=False)
                }
                rewritten_final = await asyncio.to_thread(
                    rag_engine.resolve_query,
                    query=request_data.query,
                    chat_history=history_list
                )

            # Durum 2: Hibrit Arama + Cross-Encoder Reranking
            yield {
                "event": "status",
                "data": json.dumps({"text": "22 ODTÜ mevzuatında hibrit arama (Dense + Sparse) yürütülüyor..."}, ensure_ascii=False)
            }

            stream_gen, ui_sources, rewritten_query = await asyncio.to_thread(
                rag_engine.answer_query_stream,
                query=request_data.query,
                source_filter=request_data.source_filter,
                chat_history=history_list,
                pre_resolved_query=rewritten_final
            )

            rewritten_final = rewritten_query
            source_count = len(ui_sources)
            top_score = float(ui_sources[0].get("score", 0.0)) if ui_sources else 0.0

            # 1. Aşama: Metadata Olayı
            metadata_payload = {
                "sources": ui_sources,
                "rewritten_query": rewritten_query,
                "is_in_scope": len(ui_sources) > 0
            }
            yield {
                "event": "metadata",
                "data": json.dumps(metadata_payload, ensure_ascii=False)
            }

            # Durum 3: Yanıt üretimi
            yield {
                "event": "status",
                "data": json.dumps({"text": "Mevzuat hükümleri derleniyor ve yanıt yazılıyor..."}, ensure_ascii=False)
            }

            # 2. Aşama: Token Akışı
            for token in stream_gen:
                yield {
                    "event": "token",
                    "data": json.dumps({"token": token}, ensure_ascii=False)
                }
                await asyncio.sleep(0.002)

            # 3. Aşama: Akış Bitiş Olayı
            yield {
                "event": "done",
                "data": "[DONE]"
            }

            latency_ms = (time.perf_counter() - start_time) * 1000
            TelemetryLogger.log_query(
                query=request_data.query,
                rewritten_query=rewritten_final,
                source_count=source_count,
                top_score=top_score,
                latency_ms=latency_ms,
                is_stream=True
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            TelemetryLogger.log_query(
                query=request_data.query,
                rewritten_query=rewritten_final,
                source_count=source_count,
                top_score=top_score,
                latency_ms=latency_ms,
                is_stream=True,
                error=str(e)
            )
            print(f"[API Stream Hata] {str(e)}")
            yield {
                "event": "error",
                "data": json.dumps({"error": "Sorgu işlenirken bir sunucu hatası oluştu."}, ensure_ascii=False)
            }

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
