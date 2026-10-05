import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CHUNKS_PATH = BASE_DIR / "data" / "processed" / "chunks.json"

def clean_broken_spacing(text: str) -> str:
    # 1. Aşama: Kelimeye yapışmış büyük harf geçişlerini ayır (örn. 'öğrencilerindeÜniversite' -> 'öğrencilerinde Üniversite')
    text = re.sub(r'([a-zçğıöşü])([A-ZÇĞİÖŞÜ])', r'\1 \2', text)

    # 2. Aşama: 'tarafındanöğrencilere' gibi yapışmaları ayırmak için bilinen kelime sonu eklerini ve yaygın kalıpları ayır
    # (Önceki hatalı çalıştırmanın yapıştırdığı kelimeler için)
    text = re.sub(r'(tarafından)(öğrencilere)', r'\1 \2', text)
    text = re.sub(r'(programları)(tanıtım)', r'\1 \2', text)
    text = re.sub(r'(toplantıları)(yapılır)', r'\1 \2', text)
    text = re.sub(r'(başvurularında)(Üniversite)', r'\1 \2', text)

    # 3. Aşama: Tek harfli Türkçe karakter kopukluklarını birleştir
    # Look-behind yerine doğrudan capture group kullanıyoruz (Python 3.14 uyumlu)
    # Örnek: 'ö ğ renci' -> 'öğrenci', 'de ğ i ş im' -> 'değişim'
    for _ in range(6):
        text = re.sub(
            r'([a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+([çğıöşüÇĞİÖŞÜ])\s+([a-zA-ZçğıöşüÇĞİÖŞÜ]+)',
            r'\1\2\3',
            text
        )
        text = re.sub(
            r'([a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+([çğıöşüÇĞİÖŞÜ])\b',
            r'\1\2',
            text
        )
        text = re.sub(
            r'\b([çğıöşüÇĞİÖŞÜ])\s+([a-zA-ZçğıöşüÇĞİÖŞÜ]+)',
            r'\1\2',
            text
        )

    # 4. Aşama: Çift boşlukları ve satır içi gereksiz tab'leri temizle
    text = re.sub(r'[ \t]+', ' ', text)
    return text

def main():
    if not CHUNKS_PATH.exists():
        print(f"Hata: {CHUNKS_PATH} bulunamadı!")
        return

    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    for chunk in chunks:
        chunk["text"] = clean_broken_spacing(chunk["text"])

    sample = next((c for c in chunks if c["document_name"] == "degisim_programlari_yonergesi.pdf" and "MADDE 7" in c["article"]), None)
    if sample:
        print("--- KONTROL ÇIKTISI (Değişim Madde 7) ---")
        print(sample["text"][:300])

    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print("\nchunks.json başarıyla onarıldı ve kaydedildi.")

if __name__ == "__main__":
    main()