import streamlit as st
from pathlib import Path
import sys

# Kök dizini yola ekle
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from src.pipeline.rag_engine import RAGEngine

st.set_page_config(
    page_title="ODTÜ Mevzuat Danışmanı",
    page_icon="🎓",
    layout="wide"
)

# Özel Stil / CSS (Daha canlı ODTÜ kırmızısı: #D31145)
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
        color: #555;
        margin-bottom: 1.5rem;
    }
    .source-box {
        background-color: #f8f9fa;
        border-left: 4px solid #D31145;
        padding: 10px 14px;
        margin-bottom: 8px;
        border-radius: 4px;
        font-size: 0.88rem;
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

@st.cache_resource(show_spinner="Modeller ve hibrit arama motoru yükleniyor...")
def get_rag_engine():
    return RAGEngine(candidate_k=15, final_k=4)

engine = get_rag_engine()

# Kenar Çubuğu (Sidebar)
with st.sidebar:
    logo_path = BASE_DIR / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), width=120)
    
    st.title("Sistem Ayarları")
    
    doc_filter = st.selectbox(
        "Kapsam Filtresi",
        options=[
            "Tüm Mevzuat",
            "lisans_yonetmeligi.pdf",
            "lisansustu_yonetmelik.pdf",
            "yaz_okulu_yonergesi.pdf",
            "cap_yonergesi.pdf",
            "yandal_yonergesi.pdf",
            "yurtlar_yonetmeligi.pdf",
            "burs_yardim_yonergesi.pdf",
            "disiplin_yonetmeligi.pdf"
        ],
        index=0
    )
    
    selected_doc = None if doc_filter == "Tüm Mevzuat" else doc_filter

    st.markdown("---")
    st.markdown("""
    **Arama Altyapısı:**
    -  Hibrit Arama (Dense + BM25)
    -  Reciprocal Rank Fusion (RRF)
    -  Cross-Encoder Reranker
    -  Groq Qwen-27B (Streaming)
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
        
        # Varsa kaynakları listele
        if "sources" in msg and msg["sources"]:
            with st.expander("📚 Dayanak Alınan Mevzuat Maddeleri", expanded=False):
                for s in msg["sources"]:
                    st.markdown(f"""
                    <div class="source-box">
                        <b>{s['source']}</b> — <b>{s['madde']}</b> (Sayfa: {s['pages']})<br>
                        <small>Uygunluk Skoru: {s['score']:.4f}</small><br>
                        <i style="color:#666;">"{s['text'][:250]}..."</i>
                    </div>
                    """, unsafe_allow_html=True)

# Yeni Soru Girişi
if user_prompt := st.chat_input("Mevzuatla ilgili sorunuzu buraya yazın..."):
    # 1. Kullanıcı mesajını arayüze ekle
    st.chat_message("user").markdown(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # 2. Asistan cevabını canlı (streaming) oluştur
    with st.chat_message("assistant"):
        with st.spinner("Mevzuat taranıyor ve bağlam oluşturuluyor..."):
            stream_gen, sources, rewritten_query = engine.answer_query_stream(
                query=user_prompt,
                source_filter=selected_doc,
                chat_history=st.session_state.messages[:-1]
            )

        if rewritten_query and rewritten_query.strip().lower() != user_prompt.strip().lower():
            st.markdown(
                f"""<div class="rewritten-query-box">
                <details open>
                    <summary>🔍 Aranan Bağlamsal Sorgu</summary>
                    <p>{rewritten_query}</p>
                </details>
                </div>""",
                unsafe_allow_html=True
            )

        # Yanıtı ekrana token token canlı akıt
        full_response = st.write_stream(stream_gen)

        # Kaynakları göster
        if sources:
            with st.expander("📚 Dayanak Alınan Mevzuat Maddeleri", expanded=False):
                for s in sources:
                    st.markdown(f"""
                    <div class="source-box">
                        <b>{s['source']}</b> — <b>{s['madde']}</b> (Sayfa: {s['pages']})<br>
                        <small>Uygunluk Skoru: {s['score']:.4f}</small><br>
                        <i style="color:#666;">"{s['text'][:250]}..."</i>
                    </div>
                    """, unsafe_allow_html=True)

    # 3. Asistan mesajını hafızaya kaydet
    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response,
        "sources": sources,
        "rewritten_query": rewritten_query if rewritten_query != user_prompt else None
    })