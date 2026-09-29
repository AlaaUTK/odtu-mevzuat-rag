from clickhouse_connect import get_client
from surrealdb import Surreal

# 1. ClickHouse Vektör Testi
print("\n=== ClickHouse Vektör Testi ===")
ch = get_client(
    host="localhost", port=8123, username="default", password="clickhouse123"
)

ch.command("DROP TABLE IF EXISTS test_vectors")
ch.command("""
CREATE TABLE test_vectors (
    id UInt32,
    metin String,
    vec Array(Float32)
) ENGINE = MergeTree() ORDER BY id
""")

ch.insert(
    "test_vectors",
    [
        [1, "Kitap", [1.0, 0.0, 0.0]],
        [2, "Kalem", [0.0, 1.0, 0.0]],
    ],
    column_names=["id", "metin", "vec"],
)

res_ch = ch.query("""
SELECT metin, cosineDistance(vec, [0.9, 0.1, 0.0]) as mesafe
FROM test_vectors
ORDER BY mesafe ASC
LIMIT 1
""").result_rows

print(f"ClickHouse En Yakin: {res_ch[0][0]} (Mesafe: {res_ch[0][1]:.4f})")

# 2. SurrealDB Vektör Testi
print("\n=== SurrealDB Vektör Testi ===")
with Surreal("http://localhost:8000") as db:
  db.signin({"username": "root", "password": "root"})
  db.use("staj_namespace", "staj_database")

  db.create(
      "test_doc", {"metin": "Kitap", "vec": [1.0, 0.0, 0.0]}
  )
  db.create("test_doc", {"metin": "Kalem", "vec": [0.0, 1.0, 0.0]})

  res = db.query("""
        SELECT metin, vector::similarity::cosine(vec, [0.9, 0.1, 0.0]) AS benzerlik
        FROM test_doc
        ORDER BY benzerlik DESC
        LIMIT 1;
    """)

  data = res[0]["result"] if isinstance(res, list) and "result" in res[0] else res
  if isinstance(data, list) and len(data) > 0:
    en_yakin = data[0]
  else:
    en_yakin = data

  print(
      f"SurrealDB En Yakin: {en_yakin['metin']} (Benzerlik:"
      f" {en_yakin['benzerlik']:.4f})"
  )