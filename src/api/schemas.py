from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="Mesajı gönderen: 'user' veya 'assistant'")
    content: str = Field(..., description="Mesaj içeriği")


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Kullanıcının mevzuat sorusu", example="ÇAP başvuru şartları nelerdir?")
    source_filter: Optional[str] = Field(None, description="Belirli bir doküman adına göre filtreleme (opsiyonel)", example="cap_yonergesi.pdf")
    chat_history: Optional[List[ChatMessage]] = Field(default=[], description="Takip soruları için geçmiş mesaj listesi")


class SourceMetadata(BaseModel):
    source: str = Field(..., description="Belge adı")
    madde: str = Field(..., description="İlgili madde etiketi")
    pages: str = Field(..., description="Sayfa aralığı")
    score: float = Field(..., description="Rerank benzerlik skoru")
    text: str = Field(..., description="Maddeye ait bağlam metni")


class QueryResponse(BaseModel):
    answer: str = Field(..., description="Modelin ürettiği nihai yanıt")
    sources: List[SourceMetadata] = Field(default=[], description="Yanıta kaynaklık eden mevzuat maddeleri")
    rewritten_query: str = Field(..., description="Query rewriter tarafından arama için kullanılan sorgu")
    is_in_scope: bool = Field(default=True, description="Sorunun mevzuat kapsamında olup olmadığı")


class HealthResponse(BaseModel):
    status: str = Field(..., example="ok")
    version: str = Field(..., example="1.0.0")