import os
import json
import numpy as np
import clickhouse_connect
from typing import List, Dict, Any

class ClickHouseVectorDB:
    def __init__(
        self,
        host: str = os.getenv("CLICKHOUSE_HOST", "localhost"),
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
        self._auto_seed()  # <-- Tablo boşsa otomatik veri yükleme tetiklenir

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

    def _auto_seed(self):
            """ClickHouse tablosu boşsa, data/processed/ altındaki işlenmiş verileri otomatik yükler."""
            try:
                # Tabloda kayıt var mı kontrol et
                result = self.client.query(f"SELECT count() FROM {self.table_name}")
                count = result.result_rows[0][0]
                if count > 0:
                    print(f"[Auto-Seed] ClickHouse tablosunda zaten {count} kayıt mevcut. Yükleme atlandı.")
                    return

                # İşlenmiş verilerin olası yolları (Docker içi ve lokal)
                possible_paths = [
                    "/app/data/processed/chunks.json",
                    "data/processed/chunks.json",
                    "./data/processed/chunks.json"
                ]
                
                chunks_path = None
                for p in possible_paths:
                    if os.path.exists(p):
                        chunks_path = p
                        break
                
                if not chunks_path:
                    print("[Auto-Seed] Uyarı: 'data/processed/chunks.json' bulunamadı, otomatik yükleme yapılamadı.")
                    return

                with open(chunks_path, "r", encoding="utf-8") as f:
                    chunks = json.load(f)

                emb_dir = os.path.dirname(chunks_path)
                emb_path = os.path.join(emb_dir, "embeddings_e5.npz")
                
                if not os.path.exists(emb_path):
                    print(f"[Auto-Seed] Uyarı: '{emb_path}' bulunamadı, embedding'ler yüklenemiyor.")
                    return

                # .npz arşivi içinden embedding'leri yükle (genellikle 'arr_0' veya benzeri bir key ile saklanır)
                npz_data = np.load(emb_path)
                # npz dosyası içindeki ilk array'i dinamik olarak alalım
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
        
    def delete_by_document(self, document_name: str):
            """Belirtilen dokümana ait tüm satırları ClickHouse tablosundan siler."""
            query = f"ALTER TABLE {self.table_name} DELETE WHERE document_name = %(doc_name)s"
            self.client.command(query, parameters={"doc_name": document_name})
            print(f"'{document_name}' için ClickHouse üzerindeki eski kayıtlar temizlendi.")

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