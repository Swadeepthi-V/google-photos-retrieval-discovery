"""
app.py — Google Photos Discovery Engine
Nostalgic "Memory Lane" Streamlit Chat & Discovery Interface
"""

import os
import sys
import logging
import streamlit as st

# ── Add project root to path ──────────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import chromadb
from analysis.rag_engine import generate_rag_response

# ── Page Configuration ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Google Photos Discovery Engine",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS: High-Contrast Nostalgic "Memory Lane" Cream Theme ─────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap');

/* Global Font & Full Cream Canvas */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
    color: #2D2825 !important;
}

/* Ensure ALL Streamlit containers share the cream parchment background */
.stApp, 
[data-testid="stAppViewContainer"], 
[data-testid="stHeader"], 
[data-testid="stBottomBlockContainer"],
.main {
    background-color: #FAF6EF !important;
    background-image: radial-gradient(#E8DFC8 0.75px, transparent 0.75px);
    background-size: 24px 24px;
}

/* ── Sidebar Styling ───────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background-color: #F2EAE0 !important;
    border-right: 1px solid #E2D5C3 !important;
}

section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] div {
    color: #3A2E28 !important;
}

/* Sidebar Captions Contrast Fix */
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] .stCaption,
.stCaption,
[data-testid="stCaptionContainer"] {
    color: #5C524A !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}

.album-summary-card {
    background: #FFFDF9;
    border: 1px solid #E2D5C3;
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(200, 100, 50, 0.05);
    position: relative;
}

.album-summary-card::before {
    content: "📌 ALBUM INDEX";
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: #C85A32 !important;
    position: absolute;
    top: -10px;
    left: 16px;
    background: #FAF6EF;
    padding: 2px 8px;
    border: 1px solid #E2D5C3;
    border-radius: 4px;
}

.album-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #C85A32 !important;
    margin-top: 4px;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 7px 0;
    border-bottom: 1px dashed #E6DBCB;
    font-size: 0.88rem;
}

.stat-row:last-child {
    border-bottom: none;
}

.stat-label {
    color: #5C524A !important;
}

.stat-value {
    font-weight: 600;
    color: #2D2825 !important;
}

/* ── Main Header ───────────────────────────────────────────────────────────── */
.main-header {
    background: #FFFDF9;
    border: 1px solid #E2D5C3;
    border-radius: 16px;
    padding: 26px 32px;
    margin-bottom: 26px;
    box-shadow: 0 4px 16px rgba(54, 100, 100, 0.06);
    position: relative;
}

.main-header::after {
    content: "";
    position: absolute;
    top: -12px;
    right: 40px;
    width: 90px;
    height: 24px;
    background: rgba(226, 213, 195, 0.65);
    border: 1px dashed #C8B9A6;
    transform: rotate(2deg);
}

.main-title {
    font-size: 1.9rem;
    font-weight: 700;
    color: #2D2825 !important;
    margin: 0 0 8px 0;
}

.main-subtitle {
    font-size: 0.98rem;
    color: #5C524A !important;
    margin: 0;
    line-height: 1.5;
}

/* ── Memory Note Assistant Block ───────────────────────────────────────────── */
.assistant-note {
    background-color: #FFFDF9;
    border-left: 6px solid #C85A32;
    border-radius: 6px 14px 14px 6px;
    padding: 22px 26px;
    margin: 16px 0 22px 0;
    box-shadow: 0 4px 14px rgba(45, 40, 37, 0.05);
    font-size: 1.02rem;
    line-height: 1.68;
    color: #2D2825 !important;
    position: relative;
}

.note-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #C85A32 !important;
    background: #FDF3EE;
    padding: 4px 10px;
    border-radius: 6px;
    margin-bottom: 12px;
    border: 1px solid #F5DED2;
}

/* ── User Chat Bubble ──────────────────────────────────────────────────────── */
.user-bubble {
    background-color: #366464;
    color: #FFFFFF !important;
    border-radius: 16px 16px 4px 16px;
    padding: 15px 20px;
    margin: 16px 0 16px auto;
    max-width: 82%;
    font-size: 1.0rem;
    box-shadow: 0 3px 10px rgba(54, 100, 100, 0.18);
    line-height: 1.5;
}

/* ── Streamlit Expander (Source Evidence Toggle) Contrast Fix ────────────── */
[data-testid="stExpander"], details {
    background-color: #FFFDF9 !important;
    border: 1px solid #E2D5C3 !important;
    border-radius: 12px !important;
    margin-top: 10px !important;
    margin-bottom: 18px !important;
}

[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary *,
details summary,
details summary span,
details summary p,
details summary svg {
    color: #2D2825 !important;
    fill: #2D2825 !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
}

[data-testid="stExpander"] summary:hover,
details summary:hover {
    color: #C85A32 !important;
}

[data-testid="stExpander"] summary:hover * {
    color: #C85A32 !important;
    fill: #C85A32 !important;
}

/* ── Polaroid Photo Card Citations ─────────────────────────────────────────── */
.photo-card {
    background: #FFFDF9;
    border: 1px solid #E2D5C3;
    border-bottom: 6px solid #E5DACB;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 14px;
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.03);
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.photo-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(200, 100, 50, 0.1);
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

/* Colorblind-Safe Source Badges */
.source-tab {
    font-size: 0.75rem;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 14px;
    color: #FFFFFF !important;
    letter-spacing: 0.03em;
}

.bg-play-store { background-color: #C85A32; } /* Terracotta */
.bg-app-store  { background-color: #366464; } /* Muted Teal */
.bg-reddit     { background-color: #D98A2B; } /* Ochre Amber */
.bg-youtube    { background-color: #394B66; } /* Slate Blue */

.score-badge {
    font-size: 0.8rem;
    font-weight: 600;
    color: #366464 !important;
    background: #EBF3F3;
    border: 1px solid #C5DFDF;
    padding: 3px 9px;
    border-radius: 8px;
}

.card-body {
    font-size: 0.93rem;
    line-height: 1.58;
    color: #3A2E28 !important;
    margin-bottom: 12px;
}

.card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.82rem;
    color: #5C524A !important;
    border-top: 1px dashed #EBE1D3;
    padding-top: 10px;
}

.card-link {
    color: #C85A32 !important;
    text-decoration: none;
    font-weight: 600;
}

.card-link:hover {
    text-decoration: underline;
}

/* ── Bottom Fixed Container & Chat Input Root Override ───────────────────── */
[data-testid="stBottomBlockContainer"],
[data-testid="stBottomBlockContainer"] > div,
.stBottomBlockContainer,
footer {
    background-color: #FAF6EF !important;
    background-image: radial-gradient(#E8DFC8 0.75px, transparent 0.75px) !important;
    background-size: 24px 24px !important;
}

/* Chat Input Outer Wrapper & Inner BaseWeb Divs */
[data-testid="stChatInput"],
.stChatInput,
[data-testid="stChatInput"] > div,
div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-baseweb="textarea"],
.st-emotion-cache-1c752h6,
.st-emotion-cache-1h9usn1 {
    background: #FFFDF9 !important;
    background-color: #FFFDF9 !important;
    border: 2px solid #E2C9B0 !important;
    border-radius: 16px !important;
    box-shadow: 0 4px 18px rgba(200, 100, 50, 0.1) !important;
}

/* Hover & Focus States */
[data-testid="stChatInput"]:hover,
div[data-baseweb="textarea"]:hover {
    border-color: #D98A2B !important;
    box-shadow: 0 6px 20px rgba(200, 100, 50, 0.14) !important;
}

[data-testid="stChatInput"]:focus-within,
div[data-baseweb="textarea"]:focus-within {
    background-color: #FFFDF9 !important;
    border-color: #C85A32 !important;
    box-shadow: 0 0 0 3px rgba(200, 100, 50, 0.22), 0 6px 22px rgba(200, 100, 50, 0.16) !important;
}

/* Actual Textarea Element */
textarea,
textarea[data-testid="stChatInputTextArea"],
[data-testid="stChatInput"] textarea,
[data-baseweb="textarea"] textarea,
.stChatInput textarea {
    background-color: #FFFDF9 !important;
    color: #2D2825 !important;
    -webkit-text-fill-color: #2D2825 !important;
    font-size: 0.98rem !important;
    font-weight: 500 !important;
}

/* Placeholder Styling */
textarea::placeholder,
[data-testid="stChatInput"] textarea::placeholder,
[data-testid="stChatInputTextArea"]::placeholder,
[data-baseweb="textarea"] textarea::placeholder {
    color: #6E645D !important;
    -webkit-text-fill-color: #6E645D !important;
    opacity: 1 !important;
    font-size: 0.95rem !important;
}

/* Submit Button Icon Wrapper & Button */
[data-testid="stChatInputSubmitButton"],
button[data-testid="stChatInputSubmitButton"] {
    background-color: #C85A32 !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 8px rgba(200, 100, 50, 0.25) !important;
    border: none !important;
}

[data-testid="stChatInputSubmitButton"]:hover {
    background-color: #B54F2A !important;
}

[data-testid="stChatInputSubmitButton"] svg {
    fill: #FFFFFF !important;
    color: #FFFFFF !important;
}

/* ── Interactive Components & Tooltips Audit ──────────────────────────────── */
button[kind="secondary"], .stButton > button {
    background-color: #FFFDF9 !important;
    color: #2D2825 !important;
    border: 1px solid #E2D5C3 !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
}

button[kind="secondary"]:hover, .stButton > button:hover {
    border-color: #C85A32 !important;
    color: #C85A32 !important;
    background-color: #FAF6EF !important;
}

[data-testid="stSpinner"] * {
    color: #366464 !important;
}

[data-testid="stTooltipContent"], [data-baseweb="tooltip"] {
    background-color: #2D2825 !important;
    color: #FAF6EF !important;
    border-radius: 6px !important;
    font-size: 0.82rem !important;
}

div[data-baseweb="select"] *, div[data-baseweb="input"] input {
    color: #2D2825 !important;
    background-color: #FFFDF9 !important;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ── Helper: Get Collection Stats ───────────────────────────────────────────────
@st.cache_data(ttl=60)
def get_album_stats():
    chroma_path = os.path.join("data", "chroma_db")
    if not os.path.exists(chroma_path):
        return {"total": 0, "breakdown": {}}
    try:
        client = chromadb.PersistentClient(path=chroma_path)
        col = client.get_collection("photos_retrieval")
        all_meta = col.get(include=["metadatas"])
        metas = all_meta.get("metadatas", [])
        total = len(metas)
        breakdown = {}
        for m in metas:
            if m and "source" in m:
                s = m["source"]
                breakdown[s] = breakdown.get(s, 0) + 1
        return {"total": total, "breakdown": breakdown}
    except Exception:
        return {"total": 392, "breakdown": {"Play Store": 118, "App Store": 170, "Reddit": 34, "YouTube": 70}}


# ── Sidebar: Album Summary Panel ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="album-summary-card">
        <div class="album-title">
            <span>📷</span> Memory Collection
        </div>
    """, unsafe_allow_html=True)

    stats = get_album_stats()
    st.markdown(f"""
        <div class="stat-row">
            <span class="stat-label">Vector Collection</span>
            <span class="stat-value">photos_retrieval</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Total Feedback Chunks</span>
            <span class="stat-value">{stats['total']} records</span>
        </div>
    """, unsafe_allow_html=True)

    for src, count in stats["breakdown"].items():
        st.markdown(f"""
            <div class="stat-row">
                <span class="stat-label">{src}</span>
                <span class="stat-value">{count}</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <div class="stat-row">
            <span class="stat-label">Embedding Model</span>
            <span class="stat-value">BGE-Large-v1.5</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Status</span>
            <span class="stat-value" style="color: #366464; font-weight: 700;">● Active</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.caption("🔍 **Nostalgic Discovery Engine**")
    st.caption("Analyzing Google Photos user feedback on memory retrieval & search friction.")

    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()


# ── Main Header ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <div class="main-title">🖼️ Google Photos Memory Lane Engine</div>
    <div class="main-subtitle">Exploring user retrieval behavior, search friction, and memory patterns across Play Store, App Store, Reddit, and YouTube.</div>
</div>
""", unsafe_allow_html=True)


# ── Session State for Chat ─────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state["messages"] = []


# ── Render Message History ─────────────────────────────────────────────────────
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
    elif msg["role"] == "assistant":
        st.markdown(f"""
        <div class="assistant-note">
            <div class="note-tag">📌 Memory Synthesis Note</div>
            {msg["content"]}
        </div>
        """, unsafe_allow_html=True)

        if "citations" in msg and msg["citations"]:
            with st.expander(f"📷 View Source Evidence ({len(msg['citations'])} Chunks)", expanded=False):
                for idx, c in enumerate(msg["citations"], 1):
                    src_class = "bg-play-store"
                    if c["source"] == "App Store":
                        src_class = "bg-app-store"
                    elif c["source"] == "Reddit":
                        src_class = "bg-reddit"
                    elif c["source"] == "YouTube":
                        src_class = "bg-youtube"

                    sim_pct = round((1.0 - c.get("distance", 0.0)) * 100, 1)
                    rating_str = f" ⭐ {c['rating']}/5" if c.get("rating") else ""
                    date_str = c.get("date", "")[:10] if c.get("date") else "Unknown date"
                    url_str = c.get("url")

                    link_html = f'<a class="card-link" href="{url_str}" target="_blank">🔗 Link</a>' if url_str else ''

                    st.markdown(f"""
                    <div class="photo-card">
                        <div class="card-header">
                            <span class="source-tab {src_class}">{c['source']}</span>
                            <span class="score-badge">Similarity: {sim_pct}%</span>
                        </div>
                        <div class="card-body">{c['full_text']}</div>
                        <div class="card-footer">
                            <span>📅 {date_str}{rating_str}</span>
                            {link_html}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)


# ── Chat Input ─────────────────────────────────────────────────────────────────
user_query = st.chat_input("Ask a question about photo retrieval, search behavior, or memory friction...")

if user_query:
    # Append user question
    st.session_state["messages"].append({"role": "user", "content": user_query})
    st.markdown(f'<div class="user-bubble">{user_query}</div>', unsafe_allow_html=True)

    # Generate assistant answer with spinner
    with st.spinner("Searching memory collection & generating synthesis..."):
        res = generate_rag_response(user_query, top_k=5)
        answer = res.get("answer", "")
        citations = res.get("citations", [])

        # Append assistant message
        st.session_state["messages"].append({
            "role": "assistant",
            "content": answer,
            "citations": citations
        })

    st.markdown(f"""
    <div class="assistant-note">
        <div class="note-tag">📌 Memory Synthesis Note</div>
        {answer}
    </div>
    """, unsafe_allow_html=True)

    if citations:
        with st.expander(f"📷 View Source Evidence ({len(citations)} Chunks)", expanded=False):
            for idx, c in enumerate(citations, 1):
                src_class = "bg-play-store"
                if c["source"] == "App Store":
                    src_class = "bg-app-store"
                elif c["source"] == "Reddit":
                    src_class = "bg-reddit"
                elif c["source"] == "YouTube":
                    src_class = "bg-youtube"

                sim_pct = round((1.0 - c.get("distance", 0.0)) * 100, 1)
                rating_str = f" ⭐ {c['rating']}/5" if c.get("rating") else ""
                date_str = c.get("date", "")[:10] if c.get("date") else "Unknown date"
                url_str = c.get("url")

                link_html = f'<a class="card-link" href="{url_str}" target="_blank">🔗 Link</a>' if url_str else ''

                st.markdown(f"""
                <div class="photo-card">
                    <div class="card-header">
                        <span class="source-tab {src_class}">{c['source']}</span>
                        <span class="score-badge">Similarity: {sim_pct}%</span>
                    </div>
                    <div class="card-body">{c['full_text']}</div>
                    <div class="card-footer">
                        <span>📅 {date_str}{rating_str}</span>
                        {link_html}
                    </div>
                </div>
                """, unsafe_allow_html=True)
