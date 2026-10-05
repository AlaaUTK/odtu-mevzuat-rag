import json
from pathlib import Path

p = Path("data/golden_set/golden_set.json")
with open(p, "r", encoding="utf-8") as f:
    data = json.load(f)

# ID bazlı güncellemeler
updates = {
    29: {"expected_document": "degisim_programlari_yonergesi.pdf", "expected_article": "MADDE 5"},
    31: {"expected_document": "dikey_gecis_yonergesi.pdf", "expected_article": "MADDE 8"},
    32: {"expected_document": "hazirlik_yonetmeligi.pdf", "expected_article": "MADDE 10"},
    37: {"expected_document": "yatay_gecis_yonergesi.pdf", "expected_article": "MADDE 6"},
    38: {"expected_document": "yatay_gecis_yonergesi.pdf", "expected_article": "MADDE 9"}
}

for item in data:
    if item["id"] in updates:
        item["expected_document"] = updates[item["id"]]["expected_document"]
        item["expected_article"] = updates[item["id"]]["expected_article"]

with open(p, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Golden set başarıyla güncellendi.")