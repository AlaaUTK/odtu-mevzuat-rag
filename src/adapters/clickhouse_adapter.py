import os
import json
import numpy as np
import clickhouse_connect
from typing import List, Dict, Any

class ClickHouseVectorDB:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8123,
        username: str = "default",
        password: str = os.getenv("CLICKHOUSE_PASSWORD", "clickhouse123"),
        database: str = "default",
        table_name: str = "odtu_mevzuat"
    ):
        self.table_name = table_name
        self.client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=username,
            password=password,
            database=database
        )
        self._init_table()

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
        ORDER BY chunk_id;
        """
        self.client.command(ddl)

    def insert_chunks(self, chunks: List[Dict[str, Any]], embeddings: np.ndarray):
        """Chunk listesi ve bunlara karşılık gelen vektörleri toplu basar."""
        data = []
        for chunk, emb in zip(chunks, embeddings):
            data.append([
                chunk["chunk_id"],
                chunk["document_name"],
                chunk.get("article", "MADDE ?"),
                chunk.get("page_start", 0),
                chunk.get("page_end", 0),
                chunk["text"],
                emb.tolist()
            ])

        self.client.insert(
            table=self.table_name,
            data=data,
            column_names=[
                "chunk_id", "document_name", "article",
                "page_start", "page_end", "text", "embedding"
            ]
        )
        print(f"Toplam {len(data)} chunk ClickHouse tablosuna başarıyla yazıldı.")

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 3,
        doc_filter: str = None
    ) -> List[Dict[str, Any]]:
        """Kosinüs mesafesi hesaplayarak en yakın Top-K mevzuatı döndürür."""
        emb_list = query_embedding.tolist()

        filter_clause = ""
        parameters = {"query_emb": emb_list, "limit": top_k}

        if doc_filter and doc_filter != "Tüm Belgeler":
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