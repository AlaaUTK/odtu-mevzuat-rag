import sys
import json
from pathlib import Path
import requests
import streamlit as st

# Kök dizini yola ekle
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="ODTÜ Mevzuat Danışmanı",
    page_icon="🎓",
    layout="wide"
)

# Kapsam Filtresi için Mevzuat Dokümanı
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

def check_api_health():
    """Backend servisinin ayakta olup olmadığını kontrol eder."""
    try:
        res = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return res.status_code == 200
    except Exception:
        return False

# Özel Stil / CSS (ODTÜ kırmızısı: #D31145)
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #D31145;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #555555;
        margin-bottom: 1.5rem;
    }
    .source-box {
        background-color: #f8f9fa;
        border-left: 4px solid #D31145;
        padding: 10px 14px;
        margin-bottom: 8px;
        border-radius: 4px;
        font-size: 0.88rem;
        color: #212529;
    }
    .rewritten-query-box {
        margin-bottom: 12px;
        font-size: 0.85rem;
    }
    .rewritten-query-box details {
        background: #f1f3f5;
        padding: 6px 12px;
        border-radius: 6px;
        border: 1px solid #e9ecef;
        cursor: pointer;
    }
    .rewritten-query-box summary {
        font-weight: 600;
        color: #495057;
        outline: none;
    }
    .rewritten-query-box p {
        margin-top: 6px;
        margin-bottom: 0;
        color: #212529;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

# Kenar Çubuğu (Sidebar)
with st.sidebar:
    logo_path = BASE_DIR / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), width=120)

    st.title("Sistem Ayarları")

    # API Durum Göstergesi (Arka plansız, sadece metin rengi)
    api_online = check_api_health()
    if api_online:
        st.markdown(
            '<div style="color: #28a745; font-weight: 600; font-size: 0.92rem; margin-bottom: 12px;">'
            '● API Servisi Bağlı (Port 8000)</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="color: #dc3545; font-weight: 600; font-size: 0.92rem; margin-bottom: 12px;">'
            '● API Servisi Çevrimdışı (Port 8000)</div>',
            unsafe_allow_html=True
        )

    # Güncellenmiş Kapsam Filtresi
    doc_filter = st.selectbox(
        "Kapsam Filtresi",
        options=ALL_DOCUMENTS,
        index=0
    )
    selected_doc = None if doc_filter == "Tüm Mevzuat" else doc_filter

    st.markdown("---")
    st.markdown("""
    **Sistem Mimarisi:**
    - **Frontend:** Streamlit (Hafif İstemci)
    - **Backend:** FastAPI Microservice
    - **Protokol:** Server-Sent Events (SSE)
    - **Getirme:** ClickHouse + BM25 + BGE Reranker
    - **Model:** Groq Qwen-27B
    """)

    if st.button("🧹 Sohbeti Temizle", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Ana Ekran Başlığı
st.markdown('<div class="main-header">🎓 ODTÜ Mevzuat Danışmanı</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Öğrenci işleri, burslar, yurtlar, sınavlar ve disiplin yönetmelikleri hakkında anında ve doğrulanabilir bilgi alın.</div>', unsafe_allow_html=True)

# Sohbet Geçmişi İlklendirme
if "messages" not in st.session_state:
    st.session_state.messages = []

# Geçmiş Mesajları Listele
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("rewritten_query"):
            st.markdown(
                f"""<div class="rewritten-query-box">
                <details>
                    <summary>🔍 Aranan Bağlamsal Sorgu</summary>
                    <p>{msg["rewritten_query"]}</p>
                </details>
                </div>""",
                unsafe_allow_html=True
            )

        st.markdown(msg["content"])

        if "sources" in msg and msg["sources"]:
            with st.expander("📚 Dayanak Alınan Mevzuat Maddeleri", expanded=False):
                for s in msg["sources"]:
                    st.markdown(f"""
                    <div class="source-box">
                        <b>{s.get('source')}</b> — <b>{s.get('madde')}</b> (Sayfa: {s.get('pages')})<br>
                        <small>Uygunluk Skoru: {s.get('score', 0):.4f}</small><br>
                        <i style="color:#666666;">"{s.get('text', '')[:250]}..."</i>
                    </div>
                    """, unsafe_allow_html=True)


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
                yield f"⚠️ Sunucu hatası: HTTP {response.status_code}"
                return

            current_event = None

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                if line.startswith("event:"):
                    current_event = line.replace("event:", "").strip()
                elif line.startswith("data:"):
                    raw_data = line.replace("data:", "").strip()

                    if current_event == "metadata":
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
                            yield f"\n\n⚠️ {err_data.get('error', 'Bilinmeyen bir hata oluştu.')}"
                        except Exception:
                            yield f"\n\n⚠️ {raw_data}"
                        break

    except requests.exceptions.ConnectionError:
        yield "⚠️ **FastAPI backend servisine ulaşılamadı.** Lütfen arka planda `uvicorn` sunucusunun (Port 8000) çalıştığından emin olun."
    except Exception as e:
        yield f"⚠️ Beklenmeyen bir bağlantı hatası oluştu: {str(e)}"


# Yeni Soru Girişi
if user_prompt := st.chat_input("Mevzuatla ilgili sorunuzu buraya yazın..."):
    if not api_online:
        st.error("FastAPI backend servisi kapalı olduğu için sorgu gönderilemedi. Lütfen sunucuyu başlatın.")
    else:
        # 1. Kullanıcı mesajını arayüze ekle
        st.chat_message("user").markdown(user_prompt)
        st.session_state.messages.append({"role": "user", "content": user_prompt})

        # 2. Asistan cevabını canlı (streaming) oluştur
        with st.chat_message("assistant"):
            response_holder = {"sources": [], "rewritten_query": user_prompt}

            with st.spinner("Mevzuat taranıyor ve bağlam oluşturuluyor..."):
                token_stream = sse_stream_generator(
                    query=user_prompt,
                    source_filter=selected_doc,
                    history=st.session_state.messages[:-1],
                    response_holder=response_holder
                )

                # Yanıtı ekrana token token canlı akıt
                full_response = st.write_stream(token_stream)

            # Yeniden yazılmış sorgu varsa göster
            rewritten = response_holder.get("rewritten_query")
            if rewritten and rewritten.strip().lower() != user_prompt.strip().lower():
                st.markdown(
                    f"""<div class="rewritten-query-box">
                    <details open>
                        <summary>🔍 Aranan Bağlamsal Sorgu</summary>
                        <p>{rewritten}</p>
                    </details>
                    </div>""",
                    unsafe_allow_html=True
                )

            # Kaynakları göster
            sources = response_holder.get("sources", [])
            if sources:
                with st.expander("📚 Dayanak Alınan Mevzuat Maddeleri", expanded=False):
                    for s in sources:
                        st.markdown(f"""
                        <div class="source-box">
                            <b>{s.get('source')}</b> — <b>{s.get('madde')}</b> (Sayfa: {s.get('pages')})<br>
                            <small>Uygunluk Skoru: {s.get('score', 0):.4f}</small><br>
                            <i style="color:#666666;">"{s.get('text', '')[:250]}..."</i>
                        </div>
                        """, unsafe_allow_html=True)

        # 3. Asistan mesajını hafızaya kaydet
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "sources": response_holder.get("sources", []),
            "rewritten_query": response_holder.get("rewritten_query") if response_holder.get("rewritten_query") != user_prompt else None
        })