import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import streamlit as st
from src.pipeline.rag_engine import RAGEngine

st.set_page_config(
    page_title="ODTÜ Mevzuat Asistanı",
    layout="wide"
)

# Kurumsal ODTÜ Arayüz Stili
st.markdown("""
<style>
    .main-title {
        color: #C8102E;
        font-weight: 700;
        margin-bottom: 0px;
    }
    .sub-title {
        color: #666666;
        font-size: 1.05rem;
        margin-bottom: 20px;
    }
    .source-card {
        background-color: #f1f3f5;
        border-left: 4px solid #C8102E;
        padding: 12px 16px;
        margin-bottom: 10px;
        border-radius: 4px;
        color: #1e1e1e !important;
        font-size: 0.92rem;
        line-height: 1.5;
    }
    .source-card b {
        color: #0b0c10 !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource(show_spinner="ODTÜ Mevzuat RAG Motoru Hazırlanıyor...")
def load_rag_engine():
    return RAGEngine(candidate_k=15, final_k=3)

rag_engine = load_rag_engine()

# YAN PANEL
with st.sidebar:
    logo_path = BASE_DIR / "logo.png"
    if not logo_path.exists():
        logo_path = BASE_DIR / "odtu-logo.png"

    if logo_path.exists():
        st.image(str(logo_path), width=200)
    else:
        st.write("**ODTÜ Bilgi İşlem**")

    st.title("Sistem Ayarları")
    st.caption("İki Aşamalı Getirme & Groq LLM")
    st.divider()

    doc_filter_options = {
        "Tüm Mevzuat (Filtresiz)": None,
        "Lisans Yönetmeliği": "lisans_yonetmeligi.pdf",
        "Lisansüstü Yönetmeliği": "lisansustu_yonetmeligi.pdf",
        "Çift Anadal (ÇAP) Yönergesi": "cap_yonergesi.pdf",
        "Yan Dal Yönergesi": "yan_dal_yonergesi.pdf",
        "Yurtlar Yönetmeliği": "yurtlar_yonetmeligi.pdf",
        "Öğrenci Disiplin Yönetmeliği": "ogrenci_disiplin_yonetmeligi.pdf",
        "Yaz Okulu Yönergesi": "yaz_okulu_yonergesi.pdf",
        "Burs ve Yardım Yönergesi": "burs_yardim_yonergesi.pdf"
    }
    selected_doc_label = st.selectbox("Hedef Mevzuat Filtresi", list(doc_filter_options.keys()))
    active_source_filter = doc_filter_options[selected_doc_label]

    candidate_k = st.slider("Aday Havuzu (Candidate-K)", min_value=5, max_value=30, value=15, step=5)
    final_k = st.slider("Getirilecek Madde Sayısı (Final-K)", min_value=1, max_value=5, value=3)

    rag_engine.candidate_k = candidate_k
    rag_engine.final_k = final_k

    st.divider()
    if st.button("Sohbet Geçmişini Temizle", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ANA EKRAN
st.markdown("<h1 class='main-title'>ODTÜ Mevzuat Asistanı</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Akademik ve İdari Yönetmelikler İçin Doğrulanmış Yapay Zekâ Danışmanı</p>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Merhaba! ODTÜ Lisans, Lisansüstü, ÇAP, Yan Dal, Yurtlar, Disiplin, Yaz Okulu veya Burs yönetmelikleri hakkında sormak istediğiniz konuyu yazabilirsiniz.",
            "sources": []
        }
    ]

# Sohbet Geçmişi
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("Yararlanılan Mevzuat Maddeleri"):
                for s in msg["sources"]:
                    st.markdown(f"""
                    <div class='source-card'>
                        <b>Belge:</b> {s['source']}<br>
                        <b>İlgili Madde:</b> {s['madde']} &nbsp;|&nbsp; <b>Sayfa Aralığı:</b> {s['pages']}<br>
                        <b>Skor:</b> {s['score']:.3f}
                        <hr style='margin: 8px 0; border: none; border-top: 1px solid #e0e0e0;'>
                        {s['text']}
                    </div>
                    """, unsafe_allow_html=True)

# Soru Giriş Alanı
if user_prompt := st.chat_input("Mevzuatla ilgili sorunuzu buraya yazın..."):
    st.session_state.messages.append({"role": "user", "content": user_prompt, "sources": []})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Mevzuat taranıyor ve cevap hazırlanıyor..."):
            result = rag_engine.answer_query(query=user_prompt, source_filter=active_source_filter)
            answer_text = result["answer"]
            sources_list = result["sources"]

            st.markdown(answer_text)

            if sources_list:
                with st.expander("Yararlanılan Mevzuat Maddeleri"):
                    for s in sources_list:
                        st.markdown(f"""
                        <div class='source-card'>
                            <b>Belge:</b> {s['source']}<br>
                            <b>İlgili Madde:</b> {s['madde']} &nbsp;|&nbsp; <b>Sayfa Aralığı:</b> {s['pages']}<br>
                            <b>Skor:</b> {s['score']:.3f}
                            <hr style='margin: 8px 0; border: none; border-top: 1px solid #e0e0e0;'>
                            {s['text']}
                        </div>
                        """, unsafe_allow_html=True)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer_text,
        "sources": sources_list
    })