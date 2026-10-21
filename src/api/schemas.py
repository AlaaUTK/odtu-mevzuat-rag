import re
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


SAFE_PDF_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+\.pdf$")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"] = Field(
        ...,
        description="Mesajı gönderen: yalnızca 'user' veya 'assistant' (role spoofing koruması)"
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Mesaj içeriği"
    )


class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=2,
        max_length=1500,
        description="Kullanıcının mevzuat sorusu",
        examples=["ÇAP başvuru şartları nelerdir?"]
    )
    source_filter: Optional[str] = Field(
        None,
        max_length=120,
        description="Belirli bir doküman adına göre filtreleme (opsiyonel)",
        examples=["cap_yonergesi.pdf"]
    )
    chat_history: Optional[List[ChatMessage]] = Field(
        default_factory=list,
        description="Takip soruları için geçmiş mesaj listesi"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Sorgu en az 2 karakter olmalıdır.")
        return cleaned

    @field_validator("source_filter")
    @classmethod
    def validate_source_filter(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned or cleaned in ("Tüm Mevzuat", "Tüm Belgeler"):
            return None
        if not SAFE_PDF_PATTERN.match(cleaned):
            raise ValueError("Geçersiz mevzuat dosya adı filtresi.")
        return cleaned

    @field_validator("chat_history")
    @classmethod
    def limit_chat_history(cls, v: Optional[List[ChatMessage]]) -> List[ChatMessage]:
        if not v:
            return []
        # Bellek ve token taşmasını önlemek için yalnızca son 8 mesajı tut
        return v[-8:]


class SourceMetadata(BaseModel):
    source: str = Field(..., description="Belge adı")
    madde: str = Field(..., description="İlgili madde etiketi")
    pages: str = Field(..., description="Sayfa aralığı")
    score: float = Field(..., description="Rerank benzerlik skoru")
    text: str = Field(..., description="Maddeye ait bağlam metni")


class QueryResponse(BaseModel):
    answer: str = Field(..., description="Modelin ürettiği nihai yanıt")
    sources: List[SourceMetadata] = Field(default_factory=list, description="Yanıta kaynaklık eden mevzuat maddeleri")
    rewritten_query: str = Field(..., description="Query rewriter tarafından arama için kullanılan sorgu")
    is_in_scope: bool = Field(default=True, description="Sorunun mevzuat kapsamında olup olmadığı")


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    version: str = Field(..., examples=["1.0.0"])
