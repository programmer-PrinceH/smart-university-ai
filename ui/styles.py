"""CSS for the Smart University AI interface (light and dark themes)."""

import streamlit as st

from ui.icons import icon_css

LIGHT = {
    "bg": "#F7F8FC",
    "surface": "#FFFFFF",
    "sidebar": "#F1F2F9",
    "text": "#1D1D1F",
    "muted": "#6E6E73",
    "border": "#E4E6F0",
    "accent": "#5B5BF0",
    "accent-soft": "#ECECFE",
    "shadow": "rgba(30, 30, 90, 0.07)",
}

DARK = {
    "bg": "#0F1117",
    "surface": "#181B24",
    "sidebar": "#12141C",
    "text": "#F5F5F7",
    "muted": "#9AA0B4",
    "border": "#2A2E3B",
    "accent": "#8484FF",
    "accent-soft": "#23253A",
    "shadow": "rgba(0, 0, 0, 0.35)",
}

BASE_CSS = """
html, body, .stApp, button, input, textarea {
    font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif;
}
.stApp { background: var(--bg); color: var(--text); }
.stApp p, .stApp label, .stApp li { color: inherit; }
[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1000px; padding-top: 2.5rem; padding-bottom: 7rem; }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: var(--sidebar);
    border-right: 1px solid var(--border);
}
.brand { display: flex; align-items: center; gap: .7rem; margin: .3rem 0 1rem; }
.brand-logo .ico { width: 22px; height: 22px; color: #fff; }
.brand-logo {
    width: 40px; height: 40px; border-radius: 12px;
    background: linear-gradient(135deg, #4F8BFF, #8B5CF6);
    display: flex; align-items: center; justify-content: center; font-size: 1.2rem;
}
.brand-name { font-weight: 700; font-size: 1.05rem; line-height: 1.2; }
.brand-sub { color: var(--muted); font-size: .78rem; }
.side-label {
    color: var(--muted); font-size: .72rem; font-weight: 600;
    letter-spacing: .06em; text-transform: uppercase; margin: 1.4rem 0 .5rem .3rem;
}
.side-group { color: var(--muted); font-size: .74rem; font-weight: 600; margin: .8rem 0 .2rem .4rem; }
[data-testid="stSidebar"] .stButton > button {
    width: 100%; justify-content: flex-start; text-align: left;
    background: transparent; border: none; box-shadow: none;
    color: var(--text); border-radius: 12px; padding: .5rem .8rem; font-weight: 500;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--accent-soft); color: var(--accent);
}
[class*="st-key-convo_"] button { font-size: .88rem !important; padding: .4rem .7rem !important; }
[class*="st-key-delc_"] button {
    justify-content: center !important; padding: .4rem .2rem !important; opacity: .55;
}
[class*="st-key-delc_"] button:hover { opacity: 1; }
.st-key-new_chat button {
    background: var(--accent) !important; color: #fff !important;
    justify-content: center !important; font-weight: 600 !important;
    box-shadow: 0 6px 16px rgba(91, 91, 240, .28) !important;
}
.st-key-new_chat button:hover { filter: brightness(1.08); color: #fff !important; }
.profile {
    display: flex; align-items: center; gap: .7rem; padding: .7rem;
    border: 1px solid var(--border); border-radius: 14px;
    background: var(--surface); margin-top: 1rem;
}
.avatar {
    width: 36px; height: 36px; border-radius: 50%; background: var(--accent);
    color: #fff; display: flex; align-items: center; justify-content: center;
    font-weight: 600; font-size: .8rem;
}
.profile-name { font-weight: 600; font-size: .9rem; line-height: 1.2; }
.profile-sub { color: var(--muted); font-size: .75rem; }

/* ---------- Home ---------- */
.hero { text-align: center; padding: .5rem 0 2rem; }
.hero-logo {
    width: 72px; height: 72px; border-radius: 22px; margin: 0 auto;
    background: linear-gradient(135deg, #4F8BFF, #8B5CF6);
    display: flex; align-items: center; justify-content: center; font-size: 2rem;
    box-shadow: 0 12px 30px rgba(99, 102, 241, .35);
}
.hero-logo .ico { width: 34px; height: 34px; color: #fff; }
.hero-title { font-size: 2.6rem; font-weight: 700; letter-spacing: -.02em; margin: .9rem 0 .2rem; }
.hero-sub { font-size: 1.25rem; color: var(--muted); }
.section-title { font-weight: 600; font-size: 1.05rem; margin: 2rem 0 .8rem; }

/* ---------- Feature cards ---------- */
[class*="st-key-card_"] {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 20px; padding: 1.2rem 1.3rem; gap: .35rem;
    box-shadow: 0 4px 18px var(--shadow);
    transition: transform .15s ease, box-shadow .15s ease;
}
[class*="st-key-card_"]:hover { transform: translateY(-2px); box-shadow: 0 10px 28px var(--shadow); }
[class*="st-key-card_"] .stButton > button {
    background: var(--accent-soft); color: var(--accent); border: none;
    border-radius: 999px; padding: .3rem 1rem; font-size: .85rem; font-weight: 600;
}
.card-icon {
    width: 44px; height: 44px; border-radius: 14px; margin-bottom: .6rem;
    display: flex; align-items: center; justify-content: center; font-size: 1.3rem;
}
.card-icon .ico { width: 22px; height: 22px; }
.card-title { font-weight: 600; font-size: 1.02rem; }
.card-desc { color: var(--muted); font-size: .9rem; line-height: 1.45; min-height: 2.6rem; }

/* ---------- Empty states ---------- */
.empty-state {
    border: 1px dashed var(--border); border-radius: 16px; padding: 1.2rem;
    text-align: center; color: var(--muted); background: var(--surface); font-size: .9rem;
}
.empty-state b { color: var(--text); display: block; margin-bottom: .2rem; }

/* ---------- Message composer ---------- */
[data-testid="stBottom"] > div { background: transparent; }
[data-testid="stChatInput"] {
    border-radius: 26px; border: 1px solid var(--border);
    background: var(--surface); box-shadow: 0 8px 30px var(--shadow);
}
[data-testid="stChatInput"] > div { background: var(--surface); }
[data-testid="stChatInput"] textarea { color: var(--text); }

/* ---------- Documents ---------- */
[data-testid="stFileUploaderDropzone"] {
    border-radius: 16px; background: var(--surface);
    border: 1.5px dashed var(--border);
}
[class*="st-key-doc_"] {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; padding: .9rem 1.1rem; margin-bottom: .6rem;
    box-shadow: 0 2px 10px var(--shadow);
}
.doc-name { font-weight: 600; font-size: .98rem; overflow-wrap: anywhere; }
.doc-name > .ico { color: var(--accent); margin-right: .45rem; }
.doc-meta { color: var(--muted); font-size: .82rem; margin-top: .15rem; }
.pill-ready .ico { width: .95em; height: .95em; vertical-align: -0.14em; margin-right: .25rem; }
.pill-ready {
    display: inline-block; background: rgba(16, 185, 129, .14); color: #059669;
    border-radius: 999px; padding: .05rem .6rem; font-size: .75rem;
    font-weight: 600; margin-left: .5rem;
}
.pill-warn { background: rgba(245, 158, 11, .16); color: #B45309; }
[class*="st-key-doc_"] .stButton > button { border-radius: 10px; font-size: .85rem; }

/* ---------- Smaller screens ---------- */
@media (max-width: 900px) {
    .block-container { padding: 2rem 1rem 7rem; }
    .hero-logo .ico { width: 34px; height: 34px; color: #fff; }
.hero-title { font-size: 2rem; }
}
"""


def build_css(theme: str) -> str:
    """Return the full <style> block for the chosen theme ('light' or 'dark')."""
    colors = DARK if theme == "dark" else LIGHT
    variables = "\n".join(f"--{name}: {value};" for name, value in colors.items())
    return (
        "<style>"
        "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');"
        f":root {{ {variables} }}"
        f"{BASE_CSS}"
        f"{icon_css()}"
        "</style>"
    )


def apply_styles(theme: str) -> None:
    """Inject the CSS into the current Streamlit page."""
    st.markdown(build_css(theme), unsafe_allow_html=True)
