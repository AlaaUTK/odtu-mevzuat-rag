import sys
import json
import time
import requests
from pathlib import Path
import streamlit as st

# Kök dizini yola ekle
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

API_BASE_URL = "http://127.0.0.1:8000"

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

# Sıkça Sorulan Sorular
FAQ_ITEMS = [
    {
        "category": "Yaz Okulu",
        "question": "Yaz okulunda en fazla kaç ders alabilirim ve başka üniversiteden ders alabilir miyim?",
        "summary": "Öğrenciler bir yaz döneminde en fazla 2 ders alabilir. İlgili bölümün onayı ile diğer yükseköğretim kurumlarından ders alma şartları ilgili yönerge hükümleri çerçevesinde yürütülür."
    },
    {
        "category": "Öğrenim Süresi",
        "question": "4 yıllık lisans programında azami süre ne kadardır, süre bitince ek sınav hakkı verilir mi?",
        "summary": "Azami süre 7 yıldır (14 yarıyıl). Süre sonunda mezun olamayan öğrencilere başarısız oldukları tüm dersler için iki ek sınav hakkı tanınır."
    },
    {
        "category": "Çift Anadal (ÇAP)",
        "question": "Çift anadal programına (ÇAP) başvurmak için genel not ortalaması en az kaç olmalı?",
        "summary": "Öğrencinin başvurduğu yarıyıla kadar tüm kredili dersleri tamamlamış olması ve genel not ortalamasının en az 3.00 (veya sınıfında ilk %20 diliminde) olması gerekir."
    },
    {
        "category": "Yurt İşlemleri",
        "question": "Yurtlara kesin kayıt yaptırmak için gerekli belgeler ve şartlar nelerdir?",
        "summary": "Kayıt takviminde ilan edilen öğrenci belgesi, adli sicil kaydı, sağlık durum beyanı ve kimlik evrakları Yurtlar Müdürlüğüne teslim edilir."
    }
]

def check_api_health() -> bool:
    """Backend servisinin durumunu kontrol eder."""
    try:
        res = requests.get(f"{API_BASE_URL}/health", timeout=1.0)
        return res.status_code == 200 and res.json().get("status") == "ok"
    except Exception:
        return False

# Kurumsal Stil ve Menü Vurgusu (Dark/Light Uyumlu CSS)
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
    
    /* Sıkça Sorulan Sorular Kartları */
    .faq-card {
        background-color: #1a1d24;
        border: 1px solid #2a2e39;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .faq-badge {
        font-size: 0.75rem;
        background-color: #2a2e39;
        color: #ff6b81;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 4px;
        display: inline-block;
        margin-bottom: 6px;
    }
    .faq-title {
        font-size: 0.98rem;
        font-weight: 600;
        color: #f3f4f6;
        margin-bottom: 6px;
    }
    .faq-summary {
        font-size: 0.86rem;
        color: #9ca3af;
        line-height: 1.45;
    }

    /* Hakkında Kartları (Koyu Mat Gri ve Birebir Eşit Yükseklik) */
    .about-card {
        background-color: #1a1d24;
        border: 1px solid #2a2e39;
        border-radius: 6px;
        padding: 20px;
        margin-bottom: 18px;
        box-sizing: border-box;
    }
    .about-card-top {
        height: 270px;
        overflow-y: auto;
    }
    .about-card-bottom {
        height: 260px;
        overflow-y: auto;
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

    /* Sidebar Navigasyon Buton Görünümü - Daire/Tik Tamamen Gizlendi */
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
    /* Streamlit'in radyo dairesini ve ikonunu tamamen yok et */
    div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] {
        margin-left: 0 !important;
    }
    div[data-testid="stRadio"] label > div:first-child {
        display: none !important;
    }
    /* Aktif olan sekmenin arka planını hafif aydınlık füme yap, soluna kırmızı çizgi çek */
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

# Kenar Çubuğu (Sidebar)
with st.sidebar:
    logo_path = BASE_DIR / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), width=120)

    st.markdown("### ODTÜ Danışmanı")
    
    # Doğrudan st.session_state.current_nav anahtarına bağlı gecikmesiz radyo menü
    st.radio(
        "Menü",
        options=["Sohbet", "Sıkça Sorulan Sorular", "Hakkında & Kapsam"],
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
        st.session_state.current_nav = "Sohbet"
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


# ==============================================================================
# SAYFA 1: SOHBET (CHAT)
# ==============================================================================
if st.session_state.current_nav == "Sohbet":
    st.markdown('<div class="page-title">ODTÜ Mevzuat Danışmanı</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-desc">Öğrenci işleri, sınav kuralları, burslar, yurtlar ve idari yönetmelikler hakkında resmi mevzuat danışmanlığı.</div>',
        unsafe_allow_html=True
    )

    # Sohbet Akışı
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
                            <i style="color:#495057;">"{s.get('text', '')[:250]}..."</i>
                        </div>
                        """, unsafe_allow_html=True)

    # Giriş Denetimi (Chat Input)
    if active_prompt := st.chat_input("Mevzuatla ilgili sorunuzu yazınız..."):
        if not check_api_health():
            st.error("FastAPI backend servisi kapalı olduğu için sorgu iletilemedi. Lütfen sunucuyu başlatınız.")
        else:
            st.chat_message("user").markdown(active_prompt)
            st.session_state.messages.append({"role": "user", "content": active_prompt})

            with st.chat_message("assistant"):
                response_holder = {
                    "sources": [],
                    "rewritten_query": active_prompt,
                    "status_text": "Mevzuat belgeleri taranıyor..."
                }
                status_box = st.empty()

                token_stream = sse_stream_generator(
                    query=active_prompt,
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

                rewritten = response_holder.get("rewritten_query")
                if rewritten and rewritten.strip().lower() != active_prompt.strip().lower():
                    st.markdown(
                        f"""<div class="rewritten-query-box">
                        <details open>
                            <summary>Aranan Bağlamsal Sorgu</summary>
                            <p>{rewritten}</p>
                        </details>
                        </div>""",
                        unsafe_allow_html=True
                    )

                sources = response_holder.get("sources", [])
                if sources:
                    with st.expander("Dayanak Alınan Mevzuat Maddeleri", expanded=False):
                        for s in sources:
                            st.markdown(f"""
                            <div class="source-box">
                                <b>{s.get('source')}</b> — <b>{s.get('madde')}</b> (Sayfa: {s.get('pages')})<br>
                                <small>Uygunluk Skoru: {s.get('score', 0):.4f}</small><br>
                                <i style="color:#495057;">"{s.get('text', '')[:250]}..."</i>
                            </div>
                            """, unsafe_allow_html=True)

            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response,
                "sources": response_holder.get("sources", []),
                "rewritten_query": response_holder.get("rewritten_query") if response_holder.get("rewritten_query") != active_prompt else None
            })
            st.rerun()


# ==============================================================================
# SAYFA 2: SIKÇA SORULAN SORULAR (FAQ)
# ==============================================================================
elif st.session_state.current_nav == "Sıkça Sorulan Sorular":
    st.markdown('<div class="page-title">Sıkça Sorulan Sorular</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-desc">Öğrencilerin ve personelin sıklıkla karşılaştığı mevzuat durumları ve ilgili düzenlemelerin kısa özetleri.</div>',
        unsafe_allow_html=True
    )

    for item in FAQ_ITEMS:
        st.markdown(f"""
        <div class="faq-card">
            <span class="faq-badge">{item['category']}</span>
            <div class="faq-title">{item['question']}</div>
            <div class="faq-summary">{item['summary']}</div>
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# SAYFA 3: HAKKINDA & KAPSAM
# ==============================================================================
elif st.session_state.current_nav == "Hakkında & Kapsam":
    st.markdown('<div class="page-title">Sistem Hakkında ve Mevzuat Kapsamı</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-desc">ODTÜ Mevzuat Danışmanı mimarisi, bilgi kaynakları ve doğruluk ilkeleri.</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("""
        <div class="about-card about-card-top">
            <h3>Doğrulanabilirlik ve Halüsinasyon Koruması</h3>
            <p>Sistem, serbest veya uydurma yanıtlar üretmez. Yalnızca üniversite senatosu ve yetkili yönetim kurulları tarafından yürürlüğe konulmuş resmi mevzuat maddelerini kaynak kabul eder.</p>
            <p>Üretilen her yanıtta dayanak alınan PDF adı, ilgili madde numarası ve sayfa bilgisi kullanıcıya şeffaf bir biçimde raporlanır.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="about-card about-card-bottom">
            <h3>Sorgulama Tavsiyeleri</h3>
            <ul>
                <li>Durumunuzu belirten net sorular yöneltin (Örn: <i>"2. sınıf öğrencisiyim, yaz okulunda kaç ders alabilirim?"</i>).</li>
                <li>Sorunuz tek bir alanı ilgilendiriyorsa sol menüdeki <b>Mevzuat Kapsam Filtresi</b> üzerinden ilgili yönergeyi seçerek aramayı daraltabilirsiniz.</li>
                <li>Yaptığınız resmi yazışmaları sol menüdeki <b>Sohbeti Dışa Aktar</b> butonuyla Markdown formatında indirebilirsiniz.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="about-card about-card-top">
            <h3>Kapsam Dahilindeki Belgeler (22 Doküman)</h3>
            <p>Sistem veri tabanında indekslenmiş temel düzenlemeler:</p>
            <ul>
                <li>Lisans ve Lisansüstü Eğitim-Öğretim Yönetmelikleri</li>
                <li>Yaz Okulu Yönergesi ve Azami Süre Esasları</li>
                <li>Çift Anadal (ÇAP) ve Yan Dal Yönergeleri</li>
                <li>Yurtlar Yönetmeliği ve Burs/Yardım Yönergesi</li>
                <li>Sınav Kuralları, Bütünleme ve Mazeret Esasları</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="about-card about-card-bottom">
            <h3>Teknik Altyapı Özeti</h3>
            <p>
                <b>Arama Katmanı:</b> ClickHouse Vektör DB + BM25 Hibrit Geri Getirme<br>
                <b>Sıralama (Reranker):</b> BAAI/bge-reranker-v2-m3<br>
                <b>Üretim Modeli:</b> Groq Qwen 2.5 32B (SSE Canlı Akış Protokolü)<br>
                <b>İstemci:</b> Streamlit Arayüzü
            </p>
        </div>
        """, unsafe_allow_html=True)