import os
import re
import json
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import clickhouse_connect

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SAFE_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class ClickHouseVectorDB:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        table_name: str = "odtu_mevzuat"
    ):
        if not SAFE_IDENTIFIER_RE.match(table_name):
            raise ValueError(f"Geçersiz tablo adı: {table_name}")

        self.table_name = table_name
        self._lock = threading.Lock()

        resolved_host = host or os.getenv("CLICKHOUSE_HOST", "localhost")
        resolved_port = int(port or os.getenv("CLICKHOUSE_PORT", "8123"))
        resolved_user = username or os.getenv("CLICKHOUSE_USER", "default")
        resolved_password = password if password is not None else os.getenv("CLICKHOUSE_PASSWORD", "clickhouse123")
        resolved_db = database or os.getenv("CLICKHOUSE_DATABASE", "default")

        # autogenerate_session_id=False ile eşzamanlı (concurrent) okuma sorgularında
        # ClickHouse session çakışması engellenir.
        self.client = clickhouse_connect.get_client(
            host=resolved_host,
            port=resolved_port,
            username=resolved_user,
            password=resolved_password,
            database=resolved_db,
            autogenerate_session_id=False
        )
        self._init_table()
        self._auto_seed()

    def _init_table(self):
        """Mevzuat parçaları ve vektörler için tabloyu oluşturur."""
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            chunk_id String,
            document_name String,
            article String,
            page_start UInt32,
            page_end UInt32,
            text String,
            embedding Array(Float32)
        ) ENGINE = MergeTree()
        ORDER BY (document_name, chunk_id);
        """
        with self._lock:
            self.client.command(ddl)

    def _auto_seed(self):
        """ClickHouse tablosu boşsa, data/processed/ altındaki işlenmiş verileri otomatik yükler."""
        try:
            result = self.client.query(f"SELECT count() FROM {self.table_name}")
            count = result.result_rows[0][0]
            if count > 0:
                print(f"[Auto-Seed] ClickHouse tablosunda zaten {count} kayıt mevcut. Yükleme atlandı.")
                return

            possible_paths = [
                BASE_DIR / "data" / "processed" / "chunks.json",
                Path("/app/data/processed/chunks.json"),
                Path("data/processed/chunks.json"),
            ]

            chunks_path = next((p for p in possible_paths if p.exists()), None)
            if not chunks_path:
                print("[Auto-Seed] Uyarı: 'data/processed/chunks.json' bulunamadı, otomatik yükleme yapılamadı.")
                return

            with open(chunks_path, "r", encoding="utf-8") as f:
                chunks = json.load(f)

            emb_path = chunks_path.parent / "embeddings_e5.npz"
            if not emb_path.exists():
                print(f"[Auto-Seed] Uyarı: '{emb_path}' bulunamadı, embedding'ler yüklenemiyor.")
                return

            with np.load(emb_path) as npz_data:
                key = npz_data.files[0]
                embeddings = npz_data[key]

            if len(chunks) != len(embeddings):
                print(f"[Auto-Seed] Hata: Chunk sayısı ({len(chunks)}) ile embedding sayısı ({len(embeddings)}) uyuşmuyor!")
                return

            print(f"[Auto-Seed] Tablo boş! data/processed üzerinden {len(chunks)} kayıt otomatik olarak yükleniyor...")
            self.insert_chunks(chunks, embeddings)
            print("[Auto-Seed] Veriler ClickHouse'a başarıyla işlendi!")

        except Exception as e:
            print(f"[Auto-Seed] Otomatik yükleme sırasında hata oluştu: {e}")

    def insert_chunks(self, chunks: List[Dict[str, Any]], embeddings: np.ndarray):
        """Chunk listesi ve bunlara karşılık gelen vektörleri toplu basar."""
        data = []
        for chunk, emb in zip(chunks, embeddings):
            emb_list = emb.tolist() if hasattr(emb, "tolist") else list(emb)
            data.append([
                str(chunk["chunk_id"]),
                str(chunk["document_name"]),
                str(chunk.get("article", "MADDE ?")),
                int(chunk.get("page_start", 0) or 0),
                int(chunk.get("page_end", 0) or 0),
                str(chunk["text"]),
                emb_list
            ])

        with self._lock:
            self.client.insert(
                table=self.table_name,
                data=data,
                column_names=[
                    "chunk_id", "document_name", "article",
                    "page_start", "page_end", "text", "embedding"
                ]
            )
        print(f"Toplam {len(data)} chunk ClickHouse tablosuna başarıyla yazıldı.")

    def delete_by_document(self, document_name: str):
        """Belirtilen dokümana ait tüm satırları ClickHouse tablosundan siler."""
        query = f"ALTER TABLE {self.table_name} DELETE WHERE document_name = %(doc_name)s"
        with self._lock:
            self.client.command(query, parameters={"doc_name": document_name})
        print(f"'{document_name}' için ClickHouse üzerindeki eski kayıtlar temizlendi.")

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 3,
        doc_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Kosinüs mesafesi hesaplayarak en yakın Top-K mevzuatı döndürür."""
        emb_list = query_embedding.tolist() if hasattr(query_embedding, "tolist") else list(query_embedding)

        filter_clause = ""
        parameters: Dict[str, Any] = {"query_emb": emb_list, "limit": int(top_k)}

        if doc_filter and doc_filter not in ("Tüm Belgeler", "Tüm Mevzuat"):
            filter_clause = "WHERE document_name = %(doc_filter)s"
            parameters["doc_filter"] = doc_filter

        query = f"""
        SELECT 
            chunk_id,
            document_name,
            article,
            page_start,
            page_end,
            text,
            cosineDistance(embedding, %(query_emb)s) AS distance,
            (1 - distance) AS similarity
        FROM {self.table_name}
        {filter_clause}
        ORDER BY distance ASC
        LIMIT %(limit)s;
        """

        result = self.client.query(query, parameters=parameters)

        hits = []
        for row in result.result_rows:
            hits.append({
                "chunk_id": row[0],
                "document_name": row[1],
                "article": row[2],
                "page_start": row[3],
                "page_end": row[4],
                "text": row[5],
                "similarity": float(row[7])
            })
        return hits
