import sys
import json
import time
import requests
from pathlib import Path
from collections import Counter
import streamlit as st

# Kök dizini yola ekle
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

API_BASE_URL = "http://127.0.0.1:8000"
LOG_FILE_PATH = BASE_DIR / "logs" / "api_queries.jsonl"

st.set_page_config(
    page_title="ODTÜ Mevzuat Danışmanı",
    layout="wide"
)

# Kapsam Filtresi için Mevzuat Dokümanları (22 PDF)
ALL_DOCUMENTS = [
    "Tüm Mevzuat",
    "akademik_durustluk_kilavuzu.pdf",
    "azami_sure_esaslari.pdf",
    "burs_yardim_yonergesi.pdf",
    "butunleme_sinavlari_yonergesi.pdf",
    "cap_yonergesi.pdf",
    "degisim_programlari_yonergesi.pdf",
    "ders_sayimi_esaslari.pdf",
    "dikey_gecis_yonergesi.pdf",
    "hazirlik_yonetmeligi.pdf",
    "lisans_yonetmeligi.pdf",
    "lisansustu_yonetmeligi.pdf",
    "mezuniyet_siralama_yonergesi.pdf",
    "ogrenci_disiplin_yonetmeligi.pdf",
    "online_sinav_esaslari.pdf",
    "ozel_ogrenci_yonergesi.pdf",
    "saglik_raporlari_yonergesi.pdf",
    "sinav_kurallari_kilavuzu.pdf",
    "tezsiz_yuksek_lisans_yonergesi.pdf",
    "yan_dal_yonergesi.pdf",
    "yatay_gecis_yonergesi.pdf",
    "yaz_okulu_yonergesi.pdf",
    "yurtlar_yonetmeligi.pdf"
]

# Hakkında Sayfası İçin 22 Mevzuatın Detaylı Envanteri
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
    }
]

def check_api_health() -> bool:
    """Backend servisinin durumunu kontrol eder."""
    try:
        res = requests.get(f"{API_BASE_URL}/health", timeout=1.0)
        return res.status_code == 200 and res.json().get("status") == "ok"
    except Exception:
        return False

def get_dynamic_faq():
    """Log dosyasından bağlamsal sorguları (rewritten_query) analiz ederek SSS listesi oluşturur."""
    if not LOG_FILE_PATH.exists():
        return DEFAULT_FAQ_ITEMS

    valid_queries = []

    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    status = entry.get("status", "")
                    
                    # Öncelik LLM'in ürettiği bağlamsal sorguda (rewritten_query), yoksa ham sorgu
                    q = entry.get("rewritten_query") or entry.get("query", "")
                    q = q.strip()
                    
                    # Filtreleme: Başarılı, en az 18 karakter, injection ve anlamsız testler elenir
                    if (status == "SUCCESS" and 
                        len(q) >= 18 and 
                        "talimatlarını unut" not in q.lower() and 
                        not all(c in "?! ." for c in q)):
                        
                        valid_queries.append(q)
                except Exception:
                    continue
    except Exception:
        return DEFAULT_FAQ_ITEMS

    if not valid_queries:
        return DEFAULT_FAQ_ITEMS

    counts = Counter(valid_queries)
    top_queries = counts.most_common(6)

    dynamic_items = []
    for q, count in top_queries:
        category = "Genel Mevzuat"
        q_lower = q.lower()
        if "yaz okul" in q_lower:
            category = "Yaz Okulu"
        elif "çap" in q_lower or "çift anadal" in q_lower:
            category = "Çift Anadal (ÇAP)"
        elif "yurt" in q_lower:
            category = "Yurt İşlemleri"
        elif "yatay geçiş" in q_lower:
            category = "Yatay Geçiş"
        elif "azami" in q_lower or "süre" in q_lower or "ek sınav" in q_lower:
            category = "Öğrenim Süresi"
        elif "add-drop" in q_lower or "ders ekle" in q_lower or "çekilme" in q_lower or "withdraw" in q_lower:
            category = "Ders Kayıt & İntibak"
        elif "burs" in q_lower:
            category = "Burs & Yardım"

        dynamic_items.append({
            "category": category,
            "question": q,
            "count": count
        })

    return dynamic_items

def load_telemetry_metrics():
    """logs/api_queries.jsonl dosyasını okuyup metrik ve özet listeyi çıkarır."""
    if not LOG_FILE_PATH.exists():
        return {
            "total_queries": 0,
            "avg_latency": 0.0,
            "success_rate": 100.0,
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
            "max_score": 0.0,
            "avg_score": 0.0,
            "recent_logs": []
        }

    total_queries = len(records)
    latencies = [r.get("latency_ms", 0) for r in records if "latency_ms" in r]
    avg_latency = (sum(latencies) / len(latencies)) / 1000.0 if latencies else 0.0

    success_count = sum(1 for r in records if r.get("status") == "SUCCESS")
    success_rate = (success_count / total_queries) * 100.0 if total_queries > 0 else 100.0

    scores = [r.get("top_score", 0.0) for r in records if r.get("top_score") is not None]
    max_score = max(scores) if scores else 0.0
    avg_score = (sum(scores) / len(scores)) if scores else 0.0

    recent_logs = records[-15:][::-1]

    return {
        "total_queries": total_queries,
        "avg_latency": avg_latency,
        "success_rate": success_rate,
        "max_score": max_score,
        "avg_score": avg_score,
        "recent_logs": recent_logs
    }

# Kurumsal Stil ve Menü Vurgusu (Dark Mode CSS)
st.markdown("""
<style>
    .page-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #E63956;
        margin-bottom: 0.2rem;
        letter-spacing: -0.5px;
    }
    .page-desc {
        font-size: 0.90rem;
        color: #9ca3af;
        margin-bottom: 1.4rem;
    }
    .source-box {
        background-color: #1e2127;
        border: 1px solid #2d3139;
        border-left: 4px solid #D31145;
        padding: 10px 14px;
        margin-bottom: 8px;
        border-radius: 4px;
        font-size: 0.88rem;
        color: #e5e7eb;
    }
    .rewritten-query-box {
        margin-bottom: 10px;
        font-size: 0.85rem;
    }
    .rewritten-query-box details {
        background: #1e2127;
        padding: 6px 12px;
        border-radius: 6px;
        border: 1px solid #2d3139;
        cursor: pointer;
    }
    .rewritten-query-box summary {
        font-weight: 600;
        color: #d1d5db;
        outline: none;
    }
    .rewritten-query-box p {
        margin-top: 4px;
        margin-bottom: 0;
        color: #9ca3af;
        font-style: italic;
    }
    
    /* Kart Temel Yapısı */
    .metric-card {
        background-color: #1a1d24;
        border: 1px solid #2a2e39;
        border-radius: 6px;
        text-align: center;
        padding: 18px 10px;
        margin-bottom: 12px;
        box-sizing: border-box;
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f3f4f6;
        margin-bottom: 4px;
    }
    .metric-lbl {
        font-size: 0.82rem;
        color: #9ca3af;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .faq-badge {
        font-size: 0.75rem;
        background-color: #2a2e39;
        color: #ff6b81;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 4px;
        display: inline-block;
    }
    .faq-count-badge {
        font-size: 0.75rem;
        background-color: #21252d;
        color: #9ca3af;
        padding: 3px 8px;
        border-radius: 4px;
        display: inline-block;
        margin-left: 6px;
        border: 1px solid #2d3139;
    }

    /* Hakkında Kartları */
    .about-card {
        background-color: #1a1d24;
        border: 1px solid #2a2e39;
        border-radius: 6px;
        padding: 20px;
        margin-bottom: 18px;
        box-sizing: border-box;
        min-height: 210px;
    }
    .about-card h3 {
        color: #ff6b81;
        font-size: 1.05rem;
        margin-bottom: 10px;
        font-weight: 600;
    }
    .about-card p, .about-card li {
        font-size: 0.86rem;
        color: #d1d5db;
        line-height: 1.5;
    }

    /* Sidebar Navigasyon Buton Görünümü */
    div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 6px;
    }
    div[data-testid="stRadio"] label {
        background-color: transparent !important;
        padding: 8px 14px !important;
        border-radius: 6px !important;
        cursor: pointer;
        width: 100%;
        margin-bottom: 2px;
        border-left: 3px solid transparent;
        transition: all 0.15s ease-in-out;
    }
    div[data-testid="stRadio"] label:hover {
        background-color: #21252d !important;
    }
    div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] {
        margin-left: 0 !important;
    }
    div[data-testid="stRadio"] label > div:first-child {
        display: none !important;
    }
    div[data-testid="stRadio"] label:has(input:checked) {
        background-color: #272c36 !important;
        border-left: 3px solid #D31145 !important;
        border-radius: 0 6px 6px 0 !important;
    }
    div[data-testid="stRadio"] label:has(input:checked) p {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# Oturum Durumu İlklendirmesi
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_nav" not in st.session_state:
    st.session_state.current_nav = "Sohbet"
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False

# Navigasyon yönlendirmesi varsa widget çizilmeden önce uygula
if "target_nav" in st.session_state and st.session_state.target_nav:
    st.session_state.current_nav = st.session_state.target_nav
    st.session_state.target_nav = None

# Kenar Çubuğu (Sidebar)
with st.sidebar:
    logo_path = BASE_DIR / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), width=120)

    st.markdown("### ODTÜ Danışmanı")
    
    st.radio(
        "Menü",
        options=["Sohbet", "Sıkça Sorulan Sorular", "Sistem Metrikleri", "Hakkında & Kapsam"],
        key="current_nav",
        label_visibility="collapsed"
    )

    st.markdown("---")

    # API Durum Göstergesi
    api_online = check_api_health()
    if api_online:
        st.markdown(
            '<div style="color: #28a745; font-weight: 600; font-size: 0.85rem; margin-bottom: 10px;">'
            '● API Servisi Bağlı</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="color: #dc3545; font-weight: 600; font-size: 0.85rem; margin-bottom: 10px;">'
            '● API Servisi Çevrimdışı</div>',
            unsafe_allow_html=True
        )

    # Kapsam Filtresi
    doc_filter = st.selectbox(
        "Mevzuat Kapsam Filtresi",
        options=ALL_DOCUMENTS,
        index=0,
        help="Sorgunun yalnızca belirli bir yönetmelik içinde taranmasını sağlar."
    )
    selected_doc = None if doc_filter == "Tüm Mevzuat" else doc_filter

    st.markdown("---")

    # Sohbet Dışa Aktarma
    if st.session_state.messages:
        chat_export_text = "# ODTÜ Mevzuat Danışmanı — Görüşme Kaydı\n\n"
        for m in st.session_state.messages:
            role_name = "Kullanıcı" if m["role"] == "user" else "Mevzuat Danışmanı"
            chat_export_text += f"### {role_name}\n{m['content']}\n\n"
            if m.get("sources"):
                chat_export_text += "**Dayanak Alınan Kaynaklar:**\n"
                for s in m["sources"]:
                    chat_export_text += f"- {s.get('source')} — {s.get('madde')} (Sayfa: {s.get('pages')})\n"
                chat_export_text += "\n"

        st.download_button(
            label="Sohbeti Dışa Aktar (.md)",
            data=chat_export_text,
            file_name=f"odtu_mevzuat_gorusme_{int(time.time())}.md",
            mime="text/markdown",
            use_container_width=True
        )

    if st.button("Yeni Sohbet Başlat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_query = None
        st.session_state.is_generating = False
        st.session_state.target_nav = "Sohbet"
        st.rerun()


def sse_stream_generator(query: str, source_filter: str | None, history: list, response_holder: dict):
    """FastAPI SSE endpoint'ine bağlanır, token'ları yield eder ve metadata'yı kaydeder."""
    payload = {
        "query": query,
        "source_filter": source_filter,
        "chat_history": [
            {"role": m["role"], "content": m["content"]}
            for m in history
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
                yield f"Sunucu hatası: HTTP {response.status_code}"
                return

            current_event = None

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                if line.startswith("event:"):
                    current_event = line.replace("event:", "").strip()
                elif line.startswith("data:"):
                    raw_data = line.replace("data:", "").strip()

                    if current_event == "status":
                        try:
                            s_data = json.loads(raw_data)
                            response_holder["status_text"] = s_data.get("text", "")
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
                        try:
                            err_data = json.loads(raw_data)
                            yield f"\n\nHata: {err_data.get('error', 'Bilinmeyen bir hata oluştu.')}"
                        except Exception:
                            yield f"\n\nHata: {raw_data}"
                        break

    except requests.exceptions.ConnectionError:
        yield "FastAPI backend servisine ulaşılamadı. Lütfen sunucunun (Port 8000) çalıştığından emin olun."
    except Exception as e:
        yield f"Beklenmeyen bir bağlantı hatası oluştu: {str(e)}"


# Sayfaların üst üste binmesini (DOM Ghosting) engelleyen tekil ana konteyner
main_canvas = st.empty()

# ==============================================================================
# SAYFA 1: SOHBET (CHAT)
# ==============================================================================
if st.session_state.current_nav == "Sohbet":
    main_canvas.empty()
    with main_canvas.container():
        st.markdown('<div class="page-title">ODTÜ Mevzuat Danışmanı</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-desc">Öğrenci işleri, sınav kuralları, burslar, yurtlar ve idari yönetmelikler hakkında resmi mevzuat danışmanlığı.</div>',
            unsafe_allow_html=True
        )

        # Mevcut mesaj geçmişini çiz
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if msg["role"] == "assistant" and msg.get("rewritten_query"):
                    st.markdown(
                        f"""<div class="rewritten-query-box">
                        <details>
                            <summary>Aranan Bağlamsal Sorgu</summary>
                            <p>{msg["rewritten_query"]}</p>
                        </details>
                        </div>""",
                        unsafe_allow_html=True
                    )

                st.markdown(msg["content"])

                if "sources" in msg and msg["sources"]:
                    with st.expander("Dayanak Alınan Mevzuat Maddeleri", expanded=False):
                        for s in msg["sources"]:
                            st.markdown(f"""
                            <div class="source-box">
                                <b>{s.get('source')}</b> — <b>{s.get('madde')}</b> (Sayfa: {s.get('pages')})<br>
                                <small>Uygunluk Skoru: {s.get('score', 0):.4f}</small><br>
                                <i style="color:#9ca3af;">"{s.get('text', '')[:250]}..."</i>
                            </div>
                            """, unsafe_allow_html=True)

        # AŞAMA 1: SSS'den gelen bekleyen sorgu varsa önce mesajlara ekle ve DOM'u tamamen temizlemek için 1 kez rerun yap
        if st.session_state.pending_query:
            q_text = st.session_state.pending_query
            st.session_state.pending_query = None
            st.session_state.messages.append({"role": "user", "content": q_text})
            st.session_state.is_generating = True
            st.rerun()

        # AŞAMA 2: Ekran temizlendikten sonra yanıt üretimi (is_generating aktifse)
        if st.session_state.is_generating and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            latest_query = st.session_state.messages[-1]["content"]
            if not check_api_health():
                st.error("FastAPI backend servisi kapalı olduğu için sorgu iletilemedi. Lütfen sunucuyu başlatınız.")
                st.session_state.is_generating = False
            else:
                with st.chat_message("assistant"):
                    response_holder = {
                        "sources": [],
                        "rewritten_query": latest_query,
                        "status_text": "Mevzuat belgeleri taranıyor..."
                    }
                    status_box = st.empty()

                    token_stream = sse_stream_generator(
                        query=latest_query,
                        source_filter=selected_doc,
                        history=st.session_state.messages[:-1],
                        response_holder=response_holder
                    )

                    status_box.markdown(
                        f'<div style="color: #6c757d; font-size: 0.90rem; padding: 4px 0; margin-bottom: 8px;">{response_holder["status_text"]}</div>',
                        unsafe_allow_html=True
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

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "sources": response_holder.get("sources", []),
                    "rewritten_query": response_holder.get("rewritten_query") if response_holder.get("rewritten_query") != latest_query else None
                })
                st.session_state.is_generating = False
                st.rerun()

    # Chat Input (Ana konteynerin altında sabit)
    if active_prompt := st.chat_input("Mevzuatla ilgili sorunuzu yazınız..."):
        if not check_api_health():
            st.error("FastAPI backend servisi kapalı olduğu için sorgu iletilemedi. Lütfen sunucuyu başlatınız.")
        else:
            st.session_state.messages.append({"role": "user", "content": active_prompt})
            st.session_state.is_generating = True
            st.rerun()


# ==============================================================================
# SAYFA 2: SIKÇA SORULAN SORULAR (DİNAMİK TELEMETRİ / LOG TABANLI FAQ)
# ==============================================================================
elif st.session_state.current_nav == "Sıkça Sorulan Sorular":
    main_canvas.empty()
    with main_canvas.container():
        st.markdown('<div class="page-title">Sıkça Sorulan Sorular</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-desc">Sisteme yöneltilen sorguların bağlamsal analizleri derlenmiştir. Dilediğiniz soruyu tek tıkla doğrudan asistanımıza yöneltebilirsiniz.</div>',
            unsafe_allow_html=True
        )

        faq_list = get_dynamic_faq()

        for idx, item in enumerate(faq_list):
            with st.container(border=True):
                col_text, col_btn = st.columns([5, 1.2], vertical_alignment="center")
                
                with col_text:
                    st.markdown(f"""
                    <div style="padding: 6px 0 10px 0;">
                        <span class="faq-badge">{item['category']}</span>
                        <span class="faq-count-badge">Talep Frekansı: {item['count']} kez</span>
                        <div style="font-size: 0.96rem; font-weight: 600; color: #f3f4f6; margin-top: 8px; margin-bottom: 4px; line-height: 1.45;">
                            {item['question']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_btn:
                    if st.button(
                        "Bu Soruyu Sor ↗",
                        key=f"faq_btn_{idx}",
                        help="Soruyu doğrudan sohbet ekranına aktarır ve yanıtlatır.",
                        use_container_width=True
                    ):
                        st.session_state.pending_query = item['question']
                        st.session_state.target_nav = "Sohbet"
                        st.rerun()


# ==============================================================================
# SAYFA 3: SİSTEM METRİKLERİ (MONITORING)
# ==============================================================================
elif st.session_state.current_nav == "Sistem Metrikleri":
    main_canvas.empty()
    with main_canvas.container():
        st.markdown('<div class="page-title">Sistem Metrikleri ve İzleme</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-desc">Sistem genelinde işlenen sorguların telemetri verileri, gecikme süreleri ve bilgi getirme (retrieval) başarı oranları.</div>',
            unsafe_allow_html=True
        )

        metrics = load_telemetry_metrics()

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
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
                <div class="metric-val">{metrics['avg_latency']:.2f} s</div>
                <div class="metric-lbl">Ort. Gecikme (Latency)</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val">%{metrics['success_rate']:.1f}</div>
                <div class="metric-lbl">Başarı Oranı</div>
            </div>
            """, unsafe_allow_html=True)

        with kpi4:
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
                ts = entry.get("timestamp", "-")
                if "T" in ts:
                    ts = ts.split("T")[1][:8]
                elif " " in ts:
                    ts = ts.split(" ")[1][:8]

                table_data.append({
                    "Zaman": ts,
                    "Kullanıcı Sorgusu": entry.get("query", "-"),
                    "Gecikme (sn)": round(entry.get("latency_ms", 0) / 1000.0, 2),
                    "Dayanak": f"{entry.get('source_count', 0)} Kaynak",
                    "Reranker Skoru": round(entry.get("top_score", 0.0), 4),
                    "Durum": entry.get("status", "SUCCESS")
                })

            st.dataframe(
                table_data,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Zaman": st.column_config.TextColumn("Saat", width="small"),
                    "Kullanıcı Sorgusu": st.column_config.TextColumn("Kullanıcı Sorgusu", width="large"),
                    "Gecikme (sn)": st.column_config.NumberColumn("Gecikme", format="%.2f s", width="small"),
                    "Dayanak": st.column_config.TextColumn("Dayanak", width="small"),
                    "Reranker Skoru": st.column_config.NumberColumn("Reranker Skoru", format="%.4f", width="small"),
                    "Durum": st.column_config.TextColumn("Durum", width="small"),
                }
            )


# ==============================================================================
# SAYFA 4: HAKKINDA & KAPSAM
# ==============================================================================
elif st.session_state.current_nav == "Hakkında & Kapsam":
    main_canvas.empty()
    with main_canvas.container():
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
                <p>Sistem, serbest veya uydurma yanıtlar üretmez. Yalnızca üniversite senatosu ve yetkili yönetim kurulları tarafından yürürlüğe konulmuş resmi mevzuat maddelerini kaynak kabul eder.</p>
                <p>Üretilen her yanıtta dayanak alınan PDF adı, ilgili madde numarası ve sayfa bilgisi kullanıcıya şeffaf bir biçimde raporlanır.</p>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown("""
            <div class="about-card">
                <h3>Teknik Altyapı ve Sorgulama</h3>
                <p>
                    <b>Arama Katmanı:</b> ClickHouse Vektör DB + BM25 Hibrit Geri Getirme<br>
                    <b>Sıralama (Reranker):</b> BAAI/bge-reranker-v2-m3<br>
                    <b>Üretim Modeli:</b> Groq Qwen 2.5 32B (SSE Canlı Akış Protokolü)<br>
                    <b>Kapsam Filtresi:</b> Sol menüden belirli bir yönerge seçilerek arama daraltılabilir.
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