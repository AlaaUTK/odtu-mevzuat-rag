from clickhouse_connect import get_client
from surrealdb import Surreal


def test_clickhouse():
  print("\n--- ClickHouse Testi Başlıyor ---")
  try:
    client = get_client(
        host="localhost",
        port=8123,
        username="default",
        password="clickhouse123",
    )
    res = client.command("SELECT 1 + 1")
    version = client.command("SELECT version()")
    print("ClickHouse Bağlantısı BAŞARILI!")
    print(f"Sürüm: {version} | Test Sorgusu (1+1): {res}")
  except Exception as e:
    print(f"ClickHouse Bağlantı HATASI: {e}")


def test_surrealdb():
  print("\n--- SurrealDB Testi Başlıyor ---")
  try:
    with Surreal("http://localhost:8000") as db:
      db.signin({"username": "root", "password": "root"})
      db.use("staj_namespace", "staj_database")
      res = db.query("RETURN 2 + 2;")
      print("SurrealDB Bağlantısı BAŞARILI!")
      print(f"Test Sorgusu (2+2): {res}")
  except Exception as e:
    print(f"SurrealDB Bağlantı HATASI: {e}")


if __name__ == "__main__":
  test_clickhouse()
  test_surrealdb()