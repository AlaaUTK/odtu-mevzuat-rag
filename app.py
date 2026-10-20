import os
import re
import sys
import json
import time
import html
import requests
from pathlib import Path
from collections import Counter
import streamlit as st

# Kök dizini yola ekle
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Docker içinde "backend:8000", yerel (local) çalışmalarda "http://127.0.0.1:8000" kullanır
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
LOG_FILE_PATH = BASE_DIR / "logs" / "api_queries.jsonl"
LOGO_PATH = BASE_DIR / "logo.png"

st.set_page_config(
    page_title="ODTÜ Mevzuat Danışmanı",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hakkında Sayfası ve İsim Eşleştirmesi İçin 22 Mevzuatın Detaylı Envanteri
DOCUMENT_INVENTORY = [
    {"No": 1, "Belge Adı": "Lisans Eğitim-Öğretim Yönetmeliği", "Kategori": "Eğitim & Öğretim", "Dosya": "lisans_yonetmeligi.pdf"},
    {"No": 2, "Belge Adı": "Lisansüstü Eğitim-Öğretim Yönetmeliği", "Kategori": "Eğitim & Öğretim", "Dosya": "lisansustu_yonetmeligi.pdf"},
    {"No": 3, "Belge Adı": "Tezsiz Yüksek Lisans Yönergesi", "Kategori": "Eğitim & Öğretim", "Dosya": "tezsiz_yuksek_lisans_yonergesi.pdf"},
    {"No": 4, "Belge Adı": "İngilizce Hazırlık Sınıfı Yönetmeliği", "Kategori": "Dil & Hazırlık", "Dosya": "hazirlik_yonetmeligi.pdf"},
    {"No": 5, "Belge Adı": "Yaz Okulu Yönergesi", "Kategori": "Eğitim & Öğretim", "Dosya": "yaz_okulu_yonergesi.pdf"},
    {"No": 6, "Belge Adı": "Azami Öğrenim Süreleri Sonunda Verilecek Ek Süre ve Sınav Esasları", "Kategori": "Öğrenim Süresi", "Dosya": "azami_sure_esaslari.pdf"},
    {"No": 7, "Belge Adı": "Çift Anadal Programı (ÇAP) Yönergesi", "Kategori": "Anadal & Yan Dal", "Dosya": "cap_yonergesi.pdf"},
    {"No": 8, "Belge Adı": "Yan Dal Programı Yönergesi", "Kategori": "Anadal & Yan Dal", "Dosya": "yan_dal_yonergesi.pdf"},
    {"No": 9, "Belge Adı": "Kurum İçi ve Kurum Dışı Yatay Geçiş Yönergesi", "Kategori": "Geçiş & İntibak", "Dosya": "yatay_gecis_yonergesi.pdf"},
    {"No": 10, "Belge Adı": "Dikey Geçiş (DGS) Lisans Öğrenimine İntibak Yönergesi", "Kategori": "Geçiş & İntibak", "Dosya": "dikey_gecis_yonergesi.pdf"},
    {"No": 11, "Belge Adı": "Muafiyet ve Ders Sayımı Esasları", "Kategori": "Geçiş & İntibak", "Dosya": "ders_sayimi_esaslari.pdf"},
    {"No": 12, "Belge Adı": "Değişim Programları (Erasmus / Mevlana / Farabi) Yönergesi", "Kategori": "Değişim & Özel", "Dosya": "degisim_programlari_yonergesi.pdf"},
    {"No": 13, "Belge Adı": "Özel Öğrenci Yönergesi", "Kategori": "Değişim & Özel", "Dosya": "ozel_ogrenci_yonergesi.pdf"},
    {"No": 14, "Belge Adı": "Sınav Kuralları ve Uygulama Kılavuzu", "Kategori": "Sınav & Değerlendirme", "Dosya": "sinav_kurallari_kilavuzu.pdf"},
    {"No": 15, "Belge Adı": "Bütünleme Sınavları Yönergesi", "Kategori": "Sınav & Değerlendirme", "Dosya": "butunleme_sinavlari_yonergesi.pdf"},
    {"No": 16, "Belge Adı": "Çevrimiçi (Online) Sınav Uygulama Esasları", "Kategori": "Sınav & Değerlendirme", "Dosya": "online_sinav_esaslari.pdf"},
    {"No": 17, "Belge Adı": "Mezuniyet Başarı Sıralaması Yönergesi", "Kategori": "Mezuniyet", "Dosya": "mezuniyet_siralama_yonergesi.pdf"},
    {"No": 18, "Belge Adı": "Akademik Dürüstlük ve Etik Kılavuzu", "Kategori": "Disiplin & Etik", "Dosya": "akademik_durustluk_kilavuzu.pdf"},
    {"No": 19, "Belge Adı": "Öğrenci Disiplin Yönetmeliği", "Kategori": "Disiplin & Etik", "Dosya": "ogrenci_disiplin_yonetmeligi.pdf"},
    {"No": 20, "Belge Adı": "Öğrenci Sağlık Raporları ve Mazeret Yönergesi", "Kategori": "İdari & Sağlık", "Dosya": "saglik_raporlari_yonergesi.pdf"},
    {"No": 21, "Belge Adı": "Burs ve Yardım Yönergesi", "Kategori": "Sosyal & Barınma", "Dosya": "burs_yardim_yonergesi.pdf"},
    {"No": 22, "Belge Adı": "Öğrenci Yurtları Yönetmeliği", "Kategori": "Sosyal & Barınma", "Dosya": "yurtlar_yonetmeligi.pdf"}
]

DOC_NAME_MAP = {item["Dosya"]: item["Belge Adı"] for item in DOCUMENT_INVENTORY}

# Kapsam Filtresi için Mevzuat Dokümanları (22 PDF)
ALL_DOCUMENTS = ["Tüm Mevzuat"] + [item["Dosya"] for item in DOCUMENT_INVENTORY]

# Varsayılan Yedek Sıkça Sorulan Sorular (Fallback)
DEFAULT_FAQ_ITEMS = [
    {
        "category": "Yaz Okulu",
        "question": "Yaz okulunda en fazla kaç ders alabilirim ve başka üniversiteden ders alabilir miyim?",
        "count": 1
    },
    {
        "category": "Öğrenim Süresi",
        "question": "4 yıllık lisans programında azami süre ne kadardır, süre bitince ek sınav hakkı verilir mi?",
        "count": 1
    },
    {
        "category": "Çift Anadal (ÇAP)",
        "question": "Çift anadal programına (ÇAP) başvurmak için genel not ortalaması en az kaç olmalı?",
        "count": 1
    },
    {
        "category": "Yurt İşlemleri",
        "question": "Yurtlara kesin kayıt yaptırmak için gerekli belgeler ve şartlar nelerdir?",
        "count": 1
    },
    {
        "category": "Geçiş & İntibak",
        "question": "Kurum içi yatay geçiş yapabilmek için en az kaç yarıyıl tamamlanmış olmalıdır?",
        "count": 1
    },
    {
        "category": "Ders Kayıt & İntibak",
        "question": "Ders ekleme ve bırakma (add-drop) süresi bittikten sonra dersten çekilme (withdraw) yapılabilir mi?",
        "count": 1
    }
]


def format_doc_label(doc_key: str) -> str:
    """Dosya adını kullanıcı dostu resmi mevzuat adına dönüştürür."""
    if doc_key == "Tüm Mevzuat":
        return "Tüm Mevzuat Belgeleri (22 Doküman)"
    return DOC_NAME_MAP.get(doc_key, doc_key)


def truncate_clean(text: str, max_len: int = 280) -> str:
    """Metni kelime ortasından bölmeden temiz bir şekilde kısaltır."""
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= max_len:
        return cleaned
    cut = cleaned[:max_len].rsplit(" ", 1)[0]
    return f"{cut}..."


def classify_faq_category(query_text: str) -> str:
    """Sorgu içeriğine göre uygun mevzuat kategorisini belirler."""
    q_lower = query_text.lower()
    if "yaz okul" in q_lower:
        return "Yaz Okulu"
    if "çap" in q_lower or "çift anadal" in q_lower or "çift ana dal" in q_lower:
        return "Çift Anadal (ÇAP)"
    if "yan dal" in q_lower or "yandal" in q_lower:
        return "Yan Dal Programı"
    if "yurt" in q_lower:
        return "Yurt İşlemleri"
    if "yatay geçiş" in q_lower or "dikey geçiş" in q_lower or "dgs" in q_lower:
        return "Yatay & Dikey Geçiş"
    if "azami" in q_lower or "ek süre" in q_lower or "ek sınav" in q_lower:
        return "Öğrenim Süresi"
    if "add-drop" in q_lower or "ders ekle" in q_lower or "çekilme" in q_lower or "withdraw" in q_lower:
        return "Ders Kayıt & İntibak"
    if "burs" in q_lower or "yardım" in q_lower:
        return "Burs & Yardım"
    if "kopya" in q_lower or "disiplin" in q_lower or "intihal" in q_lower or "etik" in q_lower:
        return "Disiplin & Etik"
    if "sağlık" in q_lower or "rapor" in q_lower or "mazeret" in q_lower:
        return "İdari & Sağlık"
    if "bütünleme" in q_lower or "sınav" in q_lower:
        return "Sınav & Değerlendirme"
    if "hazırlık" in q_lower or "muafiyet" in q_lower:
        return "Dil & Hazırlık"
    return "Genel Mevzuat"


def check_api_health() -> bool:
    """Backend servisinin durumunu kontrol eder."""
    try:
        res = requests.get(f"{API_BASE_URL}/health", timeout=1.5)
        return res.status_code == 200 and res.json().get("status") == "ok"
    except Exception:
        return False


def get_dynamic_faq():
    """
    Log dosyasından yalnızca mevzuat kapsamında yanıtlanmış (source_count > 0),
    güvenli ve anlamlı sorguları analiz ederek SSS listesi oluşturur.
    """
    if not LOG_FILE_PATH.exists():
        return DEFAULT_FAQ_ITEMS

    blocked_patterns = (
        "talimatlarını unut",
        "sistem talimat",
        "ignore previous",
        "gizli geçit",
        "yemekhane menüsü",
        "ring otobüs",
        "python dilinde",
    )
    followup_prefixes = (
        "peki ",
        "bu ",
        "bunun ",
        "o zaman ",
        "aynı ",
        "yukarıdaki ",
        "bahsedilen ",
    )

    normalized_counts: Counter = Counter()
    canonical_questions: dict[str, str] = {}

    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    status = entry.get("status", "")
                    source_count = int(entry.get("source_count", 0) or 0)
                    top_score = float(entry.get("top_score", 0.0) or 0.0)

                    raw_q = (entry.get("query") or "").strip()
                    rewritten_q = (entry.get("rewritten_query") or "").strip()

                    # Yalnızca başarılı, kaynak bulunmuş ve eşik üstü sorguları dahil et
                    if status != "SUCCESS" or source_count <= 0 or top_score < 0.25:
                        continue

                    combined_lower = f"{raw_q} {rewritten_q}".lower()
                    if any(pat in combined_lower for pat in blocked_patterns):
                        continue

                    # Takip sorusu ise bağlamsal (rewritten) sorguyu, değilse orijinal soruyu tercih et
                    is_followup = raw_q.lower().startswith(followup_prefixes) or len(raw_q) < 22
                    candidate_q = rewritten_q if (is_followup and rewritten_q) else (raw_q or rewritten_q)
                    candidate_q = " ".join(candidate_q.split())

                    # Çok kısa, çok uzun (kişisel senaryo) veya anlamsız karakter dizilerini ele
                    if len(candidate_q) < 20 or len(candidate_q) > 160:
                        continue
                    if all(c in "?! .,;:-_*" for c in candidate_q):
                        continue

                    # Tekilleştirme anahtarı (noktalama ve büyük/küçük harf duyarsız)
                    norm_key = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ]", "", candidate_q.lower()).strip()
                    norm_key = " ".join(norm_key.split())
                    if not norm_key:
                        continue

                    normalized_counts[norm_key] += 1
                    # Soru işareti ile biten formu tercih et
                    if norm_key not in canonical_questions or (
                        candidate_q.endswith("?") and not canonical_questions[norm_key].endswith("?")
                    ):
                        canonical_questions[norm_key] = candidate_q
                except Exception:
                    continue
    except Exception:
        return DEFAULT_FAQ_ITEMS

    if not normalized_counts:
        return DEFAULT_FAQ_ITEMS

    dynamic_items = []
    seen_norms = set()

    for norm_key, count in normalized_counts.most_common(6):
        q_text = canonical_questions[norm_key]
        if not q_text.endswith("?"):
            q_text = f"{q_text}?"
        dynamic_items.append({
            "category": classify_faq_category(q_text),
            "question": q_text,
            "count": count
        })
        seen_norms.add(norm_key)

    # Eğer dinamik liste 6'dan azsa varsayılan SSS sorularıyla tamamla
    if len(dynamic_items) < 6:
        for fallback in DEFAULT_FAQ_ITEMS:
            fb_norm = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ]", "", fallback["question"].lower()).strip()
            fb_norm = " ".join(fb_norm.split())
            if fb_norm not in seen_norms:
                dynamic_items.append(fallback)
                seen_norms.add(fb_norm)
            if len(dynamic_items) >= 6:
                break

    return dynamic_items


def load_telemetry_metrics():
    """logs/api_queries.jsonl dosyasını okuyup metrik ve özet listeyi çıkarır."""
    if not LOG_FILE_PATH.exists():
        return {
            "total_queries": 0,
            "avg_latency": 0.0,
            "success_rate": 100.0,
            "in_scope_rate": 100.0,
            "max_score": 0.0,
            "avg_score": 0.0,
            "recent_logs": []
        }

    records = []
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        continue
    except Exception:
        pass

    if not records:
        return {
            "total_queries": 0,
            "avg_latency": 0.0,
            "success_rate": 100.0,
            "in_scope_rate": 100.0,
            "max_score": 0.0,
            "avg_score": 0.0,
            "recent_logs": []
        }

    total_queries = len(records)
    latencies = [float(r.get("latency_ms", 0)) for r in records if r.get("latency_ms") is not None]
    avg_latency = (sum(latencies) / len(latencies)) / 1000.0 if latencies else 0.0

    success_count = sum(1 for r in records if r.get("status") == "SUCCESS")
    success_rate = (success_count / total_queries) * 100.0 if total_queries > 0 else 100.0

    in_scope_records = [r for r in records if int(r.get("source_count", 0) or 0) > 0]
    in_scope_rate = (len(in_scope_records) / total_queries) * 100.0 if total_queries > 0 else 100.0

    scores = [
        float(r.get("top_score", 0.0))
        for r in in_scope_records
        if r.get("top_score") is not None and float(r.get("top_score", 0.0)) > 0
    ]
    max_score = max(scores) if scores else 0.0
    avg_score = (sum(scores) / len(scores)) if scores else 0.0

    recent_logs = records[-20:][::-1]

    return {
        "total_queries": total_queries,
        "avg_latency": avg_latency,
        "success_rate": success_rate,
        "in_scope_rate": in_scope_rate,
        "max_score": max_score,
        "avg_score": avg_score,
        "recent_logs": recent_logs
    }


# ==============================================================================
# OTURUM DURUMU (SESSION STATE) VE CALLBACK FONKSİYONLARI
# ==============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_nav" not in st.session_state:
    st.session_state.current_nav = "Sohbet"
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = 0


def trigger_query_from_button(question_text: str):
    """
    SSS veya örnek soru butonuna tıklandığında script çalışmadan ÖNCE tetiklenir.
    Böylece ara rerun gerektirmeden doğrudan Sohbet sayfasına geçilir ve soru eklenir.
    """
    if not question_text or st.session_state.is_generating:
        return
    st.session_state.messages.append({"role": "user", "content": question_text})
    st.session_state.is_generating = True
    st.session_state.current_nav = "Sohbet"


def reset_chat_session():
    """Sohbet geçmişini temizler ve yeni bir oturum başlatır."""
    st.session_state.messages = []
    st.session_state.is_generating = False
    st.session_state.current_nav = "Sohbet"
    st.session_state.chat_session_id += 1


# ==============================================================================
# KURUMSAL STİL VE SAYFA ÖRTÜŞMESİ (DOM GHOSTING) KORUMA KATMANI
# ==============================================================================
# Aktif olmayan sayfaların konteynerlerini CSS seviyesinde de anında gizle
NAV_KEY_MAP = {
    "Sohbet": f"page_sohbet_{st.session_state.chat_session_id}",
    "Sıkça Sorulan Sorular": "page_sss",
    "Sistem Metrikleri": "page_metrikler",
    "Hakkında & Kapsam": "page_hakkinda"
}
inactive_selectors = ", ".join(
    f".st-key-{k}" for nav_name, k in NAV_KEY_MAP.items()
    if nav_name != st.session_state.current_nav
)

st.markdown(f"""
<style>
    /* Boş st.empty() yer tutucularının ve aktif olmayan sayfa bloklarının gizlenmesi */
    div[data-testid="stElementContainer"]:has(div[data-testid="stEmpty"]) {{
        display: none !important;
    }}
    {inactive_selectors} {{
        display: none !important;
    }}

    .page-title {{
        font-size: 1.85rem;
        font-weight: 700;
        color: #E63956;
        margin-bottom: 0.25rem;
        letter-spacing: -0.4px;
    }}
    .page-desc {{
        font-size: 0.92rem;
        color: #9ca3af;
        margin-bottom: 1.25rem;
        line-height: 1.5;
    }}

    /* Aktif Kapsam Filtresi Bilgi Bandı */
    .filter-banner {{
        background: linear-gradient(90deg, rgba(211, 17, 69, 0.14) 0%, rgba(26, 29, 36, 0.85) 100%);
        border: 1px solid rgba(230, 57, 86, 0.35);
        border-left: 4px solid #E63956;
        border-radius: 6px;
        padding: 8px 14px;
        margin-bottom: 14px;
        font-size: 0.85rem;
        color: #e5e7eb;
    }}

    /* Boş Sohbet Karşılama Alanı */
    .welcome-box {{
        background-color: #161920;
        border: 1px solid #262b36;
        border-radius: 10px;
        padding: 24px 26px;
        margin: 8px 0 18px 0;
    }}
    .welcome-box h4 {{
        color: #f3f4f6;
        font-size: 1.08rem;
        font-weight: 600;
        margin: 0 0 8px 0;
    }}
    .welcome-box p {{
        color: #9ca3af;
        font-size: 0.88rem;
        margin: 0;
        line-height: 1.55;
    }}

    /* Kaynak Kutusu */
    .source-box {{
        background-color: #181b22;
        border: 1px solid #2a2f3a;
        border-left: 4px solid #D31145;
        padding: 12px 15px;
        margin-bottom: 10px;
        border-radius: 6px;
        font-size: 0.87rem;
        color: #e5e7eb;
        line-height: 1.5;
    }}
    .source-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 6px;
    }}
    .source-score-badge {{
        font-size: 0.74rem;
        background-color: rgba(230, 57, 86, 0.15);
        color: #ff7b93;
        border: 1px solid rgba(230, 57, 86, 0.35);
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 600;
    }}

    /* Bağlamsal Sorgu Kutusu */
    .rewritten-query-box {{
        margin-bottom: 10px;
        font-size: 0.84rem;
    }}
    .rewritten-query-box details {{
        background: #181b22;
        padding: 6px 12px;
        border-radius: 6px;
        border: 1px solid #2a2f3a;
        cursor: pointer;
    }}
    .rewritten-query-box summary {{
        font-weight: 600;
        color: #d1d5db;
        outline: none;
    }}
    .rewritten-query-box p {{
        margin-top: 5px;
        margin-bottom: 0;
        color: #9ca3af;
        font-style: italic;
    }}

    /* Canlı Durum (Status) Göstergesi */
    .stream-status-pill {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background-color: #181b22;
        border: 1px solid #2a2f3a;
        border-left: 3px solid #E63956;
        color: #d1d5db;
        font-size: 0.86rem;
        padding: 7px 14px;
        border-radius: 6px;
        margin-bottom: 8px;
    }}

    /* Metrik Kartları */
    .metric-card {{
        background-color: #181b22;
        border: 1px solid #282d37;
        border-radius: 8px;
        text-align: center;
        padding: 18px 12px;
        margin-bottom: 12px;
        box-sizing: border-box;
    }}
    .metric-val {{
        font-size: 1.75rem;
        font-weight: 700;
        color: #f3f4f6;
        margin-bottom: 4px;
    }}
    .metric-lbl {{
        font-size: 0.78rem;
        color: #9ca3af;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* SSS Rozetleri */
    .faq-badge {{
        font-size: 0.75rem;
        background-color: rgba(230, 57, 86, 0.14);
        color: #ff7b93;
        border: 1px solid rgba(230, 57, 86, 0.3);
        font-weight: 600;
        padding: 3px 9px;
        border-radius: 4px;
        display: inline-block;
    }}
    .faq-count-badge {{
        font-size: 0.75rem;
        background-color: #1f242d;
        color: #9ca3af;
        padding: 3px 9px;
        border-radius: 4px;
        display: inline-block;
        margin-left: 6px;
        border: 1px solid #2d333f;
    }}

    /* Hakkında Kartları */
    .about-card {{
        background-color: #181b22;
        border: 1px solid #282d37;
        border-radius: 8px;
        padding: 20px 22px;
        margin-bottom: 18px;
        box-sizing: border-box;
        min-height: 215px;
    }}
    .about-card h3 {{
        color: #ff6b81;
        font-size: 1.05rem;
        margin-top: 0;
        margin-bottom: 10px;
        font-weight: 600;
    }}
    .about-card p, .about-card li {{
        font-size: 0.87rem;
        color: #d1d5db;
        line-height: 1.55;
    }}

    /* Sidebar Navigasyon Buton Görünümü */
    div[data-testid="stRadio"] div[role="radiogroup"] {{
        gap: 6px;
    }}
    div[data-testid="stRadio"] label {{
        background-color: transparent !important;
        padding: 9px 14px !important;
        border-radius: 6px !important;
        cursor: pointer;
        width: 100%;
        margin-bottom: 2px;
        border-left: 3px solid transparent;
        transition: all 0.15s ease-in-out;
    }}
    div[data-testid="stRadio"] label:hover {{
        background-color: #21252d !important;
    }}
    div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] {{
        margin-left: 0 !important;
    }}
    div[data-testid="stRadio"] label > div:first-child {{
        display: none !important;
    }}
    div[data-testid="stRadio"] label:has(input:checked) {{
        background-color: #262b36 !important;
        border-left: 3px solid #E63956 !important;
        border-radius: 0 6px 6px 0 !important;
    }}
    div[data-testid="stRadio"] label:has(input:checked) p {{
        color: #ffffff !important;
        font-weight: 600 !important;
    }}
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# KENAR ÇUBUĞU (SIDEBAR)
# ==============================================================================
api_online = check_api_health()

with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=115)

    st.markdown("### ODTÜ Mevzuat Danışmanı")
    st.caption("Resmi Yönetmelik ve Yönerge Asistanı")

    st.radio(
        "Menü",
        options=["Sohbet", "Sıkça Sorulan Sorular", "Sistem Metrikleri", "Hakkında & Kapsam"],
        key="current_nav",
        label_visibility="collapsed"
    )

    st.markdown("---")

    # API Durum Göstergesi
    if api_online:
        st.markdown(
            '<div style="color: #2ecc71; font-weight: 600; font-size: 0.85rem; margin-bottom: 12px;">'
            '● API Servisi Bağlı ve Hazır</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="color: #e74c3c; font-weight: 600; font-size: 0.85rem; margin-bottom: 12px;">'
            '● API Servisi Çevrimdışı (Port 8000)</div>',
            unsafe_allow_html=True
        )

    # Kapsam Filtresi (Resmi belge adlarıyla)
    doc_filter = st.selectbox(
        "Mevzuat Kapsam Filtresi",
        options=ALL_DOCUMENTS,
        index=0,
        format_func=format_doc_label,
        help="Sorgunun yalnızca seçilen resmi yönetmelik veya yönerge içinde taranmasını sağlar."
    )
    selected_doc = None if doc_filter == "Tüm Mevzuat" else doc_filter

    st.markdown("---")

    # Sohbet Dışa Aktarma
    if st.session_state.messages:
        chat_export_text = "# ODTÜ Mevzuat Danışmanı — Görüşme Kaydı\n\n"
        for m in st.session_state.messages:
            role_name = "Kullanıcı" if m["role"] == "user" else "ODTÜ Mevzuat Danışmanı"
            chat_export_text += f"### {role_name}\n{m['content']}\n\n"
            if m.get("sources"):
                chat_export_text += "**Dayanak Alınan Resmi Kaynaklar:**\n"
                for s in m["sources"]:
                    src_file = s.get("source", "")
                    src_title = DOC_NAME_MAP.get(src_file, src_file)
                    chat_export_text += f"- {src_title} (`{src_file}`) — {s.get('madde')} (Sayfa: {s.get('pages')})\n"
                chat_export_text += "\n"

        st.download_button(
            label="Sohbeti Dışa Aktar (.md)",
            data=chat_export_text,
            file_name=f"odtu_mevzuat_gorusme_{int(time.time())}.md",
            mime="text/markdown",
            use_container_width=True,
            disabled=st.session_state.is_generating
        )

    st.button(
        "Yeni Sohbet Başlat",
        on_click=reset_chat_session,
        use_container_width=True,
        disabled=st.session_state.is_generating
    )


def sse_stream_generator(query: str, source_filter: str | None, history: list, response_holder: dict, status_box):
    """FastAPI SSE endpoint'ine bağlanır, durum mesajlarını canlı günceller ve token'ları yield eder."""
    payload = {
        "query": query,
        "source_filter": source_filter,
        "chat_history": [
            {"role": m["role"], "content": m["content"]}
            for m in history
            if not m.get("is_error")
        ]
    }

    try:
        with requests.post(
            f"{API_BASE_URL}/api/v1/query/stream",
            json=payload,
            stream=True,
            timeout=60
        ) as response:
            if response.status_code != 200:
                response_holder["has_error"] = True
                yield f"Sunucu hatası oluştu (HTTP {response.status_code}). Lütfen daha sonra tekrar deneyiniz."
                return

            current_event = None

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                if line.startswith("event:"):
                    current_event = line[6:].strip()
                elif line.startswith("data:"):
                    raw_data = line[5:].strip()

                    if current_event == "status":
                        try:
                            s_data = json.loads(raw_data)
                            status_msg = re.sub(r"^[^\w\sçğıöşüÇĞİÖŞÜ0-9]+\s*", "", s_data.get("text", "")).strip()
                            if status_msg:
                                response_holder["status_text"] = status_msg
                                safe_status = html.escape(status_msg)
                                status_box.markdown(
                                    f'<div class="stream-status-pill">{safe_status}</div>',
                                    unsafe_allow_html=True
                                )
                        except Exception:
                            pass

                    elif current_event == "metadata":
                        try:
                            meta = json.loads(raw_data)
                            response_holder["sources"] = meta.get("sources", [])
                            response_holder["rewritten_query"] = meta.get("rewritten_query", query)
                        except Exception:
                            pass

                    elif current_event == "token":
                        try:
                            data_json = json.loads(raw_data)
                            yield data_json.get("token", "")
                        except Exception:
                            yield raw_data

                    elif current_event == "done":
                        break

                    elif current_event == "error":
                        response_holder["has_error"] = True
                        try:
                            err_data = json.loads(raw_data)
                            yield f"\n\nHata: {err_data.get('error', 'Bilinmeyen bir sunucu hatası oluştu.')}"
                        except Exception:
                            yield f"\n\nHata: {raw_data}"
                        break

    except requests.exceptions.ConnectionError:
        response_holder["has_error"] = True
        yield "FastAPI backend servisine ulaşılamadı. Lütfen sunucunun (Port 8000) çalıştığından emin olunuz."
    except requests.exceptions.Timeout:
        response_holder["has_error"] = True
        yield "Sunucu yanıt süresi zaman aşımına uğradı. Lütfen sorunuzu tekrar gönderiniz."
    except Exception as e:
        response_holder["has_error"] = True
        yield f"Beklenmeyen bir bağlantı hatası oluştu: {str(e)}"


# ==============================================================================
# BAĞIMSIZ SAYFA YER TUTUCULARI (DOM GHOSTING ENGELLEYİCİ MİMARİ)
# ==============================================================================
# Her sayfa kendi bağımsız st.empty() yuvasına sahiptir. Sayfa değiştiğinde eski
# sayfanın yuvası ElementNode(empty) olarak sıfırlanır ve React tarafından anında kaldırılır.
slot_sohbet = st.empty()
slot_sss = st.empty()
slot_metrikler = st.empty()
slot_hakkinda = st.empty()


# ==============================================================================
# SAYFA 1: SOHBET (CHAT)
# ==============================================================================
if st.session_state.current_nav == "Sohbet":
    # Girdi alanı akış başlamadan önce tanımlanır; böylece yanıt üretilirken stale kalmaz
    active_prompt = st.chat_input(
        "Mevzuatla ilgili sorunuzu yazınız...",
        disabled=st.session_state.is_generating
    )
    if active_prompt and active_prompt.strip():
        st.session_state.messages.append({"role": "user", "content": active_prompt.strip()})
        st.session_state.is_generating = True

    with slot_sohbet.container(key=NAV_KEY_MAP["Sohbet"]):
        st.markdown('<div class="page-title">ODTÜ Mevzuat Danışmanı</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-desc">Öğrenci işleri, sınav kuralları, burslar, yurtlar ve idari yönetmelikler hakkında resmi mevzuat danışmanlığı.</div>',
            unsafe_allow_html=True
        )

        # Aktif kapsam filtresi varsa kullanıcıya bildir
        if selected_doc:
            safe_doc_title = html.escape(DOC_NAME_MAP.get(selected_doc, selected_doc))
            safe_doc_file = html.escape(selected_doc)
            st.markdown(
                f'<div class="filter-banner">'
                f'<b>Aktif Kapsam Filtresi:</b> Sorgularınız yalnızca <b>{safe_doc_title}</b> (<code>{safe_doc_file}</code>) içinde taranmaktadır.'
                f'</div>',
                unsafe_allow_html=True
            )

        # Boş durum (Empty State): Henüz mesaj yokken karşılama ekranı ve örnek sorular
        if not st.session_state.messages and not st.session_state.is_generating:

            st.markdown("##### Hızlı Başlangıç İçin Örnek Sorular")
            q_cols = st.columns(2)
            for i, sample in enumerate(DEFAULT_FAQ_ITEMS[:4]):
                with q_cols[i % 2]:
                    st.button(
                        f"{sample['question']} ↗",
                        key=f"welcome_sample_{i}",
                        on_click=trigger_query_from_button,
                        args=(sample["question"],),
                        use_container_width=True
                    )

        # Mevcut mesaj geçmişini çiz
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if msg["role"] == "assistant" and msg.get("rewritten_query"):
                    safe_rq = html.escape(str(msg["rewritten_query"]))
                    st.markdown(
                        f"""<div class="rewritten-query-box">
                        <details>
                            <summary>Aranan Bağlamsal Sorgu</summary>
                            <p>{safe_rq}</p>
                        </details>
                        </div>""",
                        unsafe_allow_html=True
                    )

                st.markdown(msg["content"])

                if msg.get("sources"):
                    with st.expander(f"Dayanak Alınan Mevzuat Maddeleri ({len(msg['sources'])} Kaynak)", expanded=False):
                        for s in msg["sources"]:
                            raw_src = str(s.get("source", ""))
                            official_title = DOC_NAME_MAP.get(raw_src, raw_src)
                            safe_title = html.escape(official_title)
                            safe_src = html.escape(raw_src)
                            safe_madde = html.escape(str(s.get("madde", "-")))
                            safe_pages = html.escape(str(s.get("pages", "-")))
                            score_val = float(s.get("score", 0.0) or 0.0)
                            snippet = html.escape(truncate_clean(str(s.get("text", "")), 300))

                            st.markdown(f"""
                            <div class="source-box">
                                <div class="source-header">
                                    <span><b>{safe_title}</b> <small style="color:#9ca3af;">({safe_src})</small> — <b>{safe_madde}</b> (Sayfa: {safe_pages})</span>
                                    <span class="source-score-badge">Uygunluk: {score_val:.4f}</span>
                                </div>
                                <i style="color:#9ca3af;">"{snippet}"</i>
                            </div>
                            """, unsafe_allow_html=True)

        # Yanıt Üretimi (is_generating aktifse)
        if st.session_state.is_generating and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            latest_query = st.session_state.messages[-1]["content"]
            if not api_online:
                st.error("FastAPI backend servisi kapalı olduğu için sorgu iletilemedi. Lütfen sunucuyu (Port 8000) başlatınız.")
                st.session_state.is_generating = False
            else:
                with st.chat_message("assistant"):
                    response_holder = {
                        "sources": [],
                        "rewritten_query": latest_query,
                        "status_text": "Mevzuat belgeleri taranıyor...",
                        "has_error": False
                    }
                    status_box = st.empty()
                    safe_init_status = html.escape(response_holder["status_text"])
                    status_box.markdown(
                        f'<div class="stream-status-pill">{safe_init_status}</div>',
                        unsafe_allow_html=True
                    )

                    token_stream = sse_stream_generator(
                        query=latest_query,
                        source_filter=selected_doc,
                        history=st.session_state.messages[:-1],
                        response_holder=response_holder,
                        status_box=status_box
                    )

                    def monitored_stream():
                        has_first_token = False
                        for token in token_stream:
                            if not has_first_token:
                                status_box.empty()
                                has_first_token = True
                            yield token
                        status_box.empty()

                    full_response = st.write_stream(monitored_stream())
                    status_box.empty()

                if isinstance(full_response, str) and full_response.strip():
                    rewritten_val = response_holder.get("rewritten_query")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_response,
                        "sources": response_holder.get("sources", []),
                        "rewritten_query": rewritten_val if (rewritten_val and rewritten_val != latest_query) else None,
                        "is_error": response_holder.get("has_error", False)
                    })
                st.session_state.is_generating = False
                st.rerun()


# ==============================================================================
# SAYFA 2: SIKÇA SORULAN SORULAR (DİNAMİK TELEMETRİ / LOG TABANLI FAQ)
# ==============================================================================
elif st.session_state.current_nav == "Sıkça Sorulan Sorular":
    with slot_sss.container(key=NAV_KEY_MAP["Sıkça Sorulan Sorular"]):
        st.markdown('<div class="page-title">Sıkça Sorulan Sorular</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-desc">Sisteme yöneltilen ve mevzuat kapsamında doğrulanan en popüler sorular derlenmiştir. Dilediğiniz soruyu tek tıkla doğrudan asistanımıza yöneltebilirsiniz.</div>',
            unsafe_allow_html=True
        )

        faq_list = get_dynamic_faq()

        for idx, item in enumerate(faq_list):
            safe_category = html.escape(str(item.get("category", "Genel Mevzuat")))
            safe_question = html.escape(str(item.get("question", "")))
            item_count = int(item.get("count", 1) or 1)

            with st.container(border=True):
                col_text, col_btn = st.columns([5, 1.25], vertical_alignment="center")

                with col_text:
                    st.markdown(f"""
                    <div style="padding: 6px 0 10px 0;">
                        <span class="faq-badge">{safe_category}</span>
                        <span class="faq-count-badge">Talep Frekansı: {item_count} kez</span>
                        <div style="font-size: 0.96rem; font-weight: 600; color: #f3f4f6; margin-top: 8px; margin-bottom: 4px; line-height: 1.45;">
                            {safe_question}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_btn:
                    st.button(
                        "Bu Soruyu Sor ↗",
                        key=f"faq_btn_{idx}",
                        help="Soruyu doğrudan sohbet ekranına aktarır ve yanıtlatır.",
                        on_click=trigger_query_from_button,
                        args=(item["question"],),
                        use_container_width=True
                    )


# ==============================================================================
# SAYFA 3: SİSTEM METRİKLERİ (MONITORING)
# ==============================================================================
elif st.session_state.current_nav == "Sistem Metrikleri":
    with slot_metrikler.container(key=NAV_KEY_MAP["Sistem Metrikleri"]):
        st.markdown('<div class="page-title">Sistem Metrikleri ve İzleme</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-desc">Sistem genelinde işlenen sorguların telemetri verileri, yanıt süreleri ve bilgi getirme (retrieval) kalite göstergeleri.</div>',
            unsafe_allow_html=True
        )

        metrics = load_telemetry_metrics()

        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        with kpi1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val">{metrics['total_queries']}</div>
                <div class="metric-lbl">Toplam Sorgu</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val">{metrics['avg_latency']:.2f} sn</div>
                <div class="metric-lbl">Ort. Yanıt Süresi</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val">%{metrics['success_rate']:.1f}</div>
                <div class="metric-lbl">Servis Başarısı</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val">{metrics['avg_score']:.4f}</div>
                <div class="metric-lbl">Ort. Reranker Skoru</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi5:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val">{metrics['max_score']:.4f}</div>
                <div class="metric-lbl">En Yüksek Skor</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### Son İşlenen Sorgular ve Telemetri Kayıtları")

        recent_logs = metrics["recent_logs"]
        if not recent_logs:
            st.info("Henüz kaydedilmiş bir sorgu telemetri verisi bulunmamaktadır.")
        else:
            table_data = []
            for entry in recent_logs:
                ts = str(entry.get("timestamp", "-"))
                ts_formatted = ts.replace("T", " ")[:16] if len(ts) >= 16 else ts

                src_cnt = int(entry.get("source_count", 0) or 0)
                raw_status = entry.get("status", "SUCCESS")
                if raw_status != "SUCCESS":
                    status_label = "Hata"
                elif src_cnt == 0:
                    status_label = "Kapsam Dışı"
                else:
                    status_label = "Başarılı"

                table_data.append({
                    "Zaman": ts_formatted,
                    "Kullanıcı Sorgusu": entry.get("query", "-"),
                    "Gecikme (sn)": round(float(entry.get("latency_ms", 0) or 0) / 1000.0, 2),
                    "Dayanak": f"{src_cnt} Madde" if src_cnt > 0 else "Yok",
                    "Reranker Skoru": round(float(entry.get("top_score", 0.0) or 0.0), 4),
                    "Durum": status_label
                })

            st.dataframe(
                table_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Zaman": st.column_config.TextColumn("Tarih / Saat", width="small"),
                    "Kullanıcı Sorgusu": st.column_config.TextColumn("Kullanıcı Sorgusu", width="large"),
                    "Gecikme (sn)": st.column_config.NumberColumn("Yanıt Süresi", format="%.2f sn", width="small"),
                    "Dayanak": st.column_config.TextColumn("Dayanak", width="small"),
                    "Reranker Skoru": st.column_config.NumberColumn("Reranker Skoru", format="%.4f", width="small"),
                    "Durum": st.column_config.TextColumn("Durum", width="small"),
                }
            )


# ==============================================================================
# SAYFA 4: HAKKINDA & KAPSAM
# ==============================================================================
elif st.session_state.current_nav == "Hakkında & Kapsam":
    with slot_hakkinda.container(key=NAV_KEY_MAP["Hakkında & Kapsam"]):
        st.markdown('<div class="page-title">Sistem Hakkında ve Mevzuat Kapsamı</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-desc">ODTÜ Mevzuat Danışmanı mimarisi, doğruluk ilkeleri ve veri tabanında indekslenen 22 resmi mevzuat dokümanının tam listesi.</div>',
            unsafe_allow_html=True
        )

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("""
            <div class="about-card">
                <h3>Doğrulanabilirlik ve Halüsinasyon Koruması</h3>
                <p>Sistem, serbest veya dayanaksız yanıtlar üretmez. Yalnızca üniversite senatosu ve yetkili kurullar tarafından yürürlüğe konulmuş resmi mevzuat maddelerini kaynak kabul eder.</p>
                <p>Üretilen her yanıtta dayanak alınan resmi belge adı, ilgili madde numarası, sayfa aralığı ve uygunluk skoru kullanıcıya şeffaf bir biçimde raporlanır.</p>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown("""
            <div class="about-card">
                <h3>Teknik Altyapı ve Sorgulama Mimarisi</h3>
                <p>
                    <b>Arama Katmanı:</b> ClickHouse Vektör DB (multilingual-e5-base) + BM25 Hibrit Arama (RRF)<br>
                    <b>Yeniden Sıralama (Reranker):</b> BAAI/bge-reranker-v2-m3 Cross-Encoder<br>
                    <b>Üretim Modeli:</b> Groq Qwen 2.5 32B (SSE Canlı Akış Protokolü)<br>
                    <b>Kapsam Filtresi:</b> Sol menüden belirli bir yönetmelik seçilerek arama daraltılabilir.
                </p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("##### Veri Tabanında İndekslenen Resmi Mevzuat Envanteri (22 Doküman)")
        st.dataframe(
            DOCUMENT_INVENTORY,
            use_container_width=True,
            hide_index=True,
            column_config={
                "No": st.column_config.NumberColumn("#", width="small"),
                "Belge Adı": st.column_config.TextColumn("Resmi Mevzuat / Yönerge Adı", width="large"),
                "Kategori": st.column_config.TextColumn("Kategori", width="medium"),
                "Dosya": st.column_config.TextColumn("Sistem Dosya Adı", width="medium"),
            }
        )
