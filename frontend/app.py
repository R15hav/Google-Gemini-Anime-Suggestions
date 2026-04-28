import os
import time
from datetime import datetime, timezone, timedelta

import requests
import streamlit as st
from streamlit_javascript import st_javascript

# ─── Constants ────────────────────────────────────────────────────────────────
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

FREE_TIER = {
    "gemini-2.5-flash-lite": {"rpd": 1500, "rpm": 30},
    "gemini-2.5-flash":      {"rpd": 500,  "rpm": 10},
    "gemini-2.5-pro":        {"rpd": 25,   "rpm": 5},
    "gemini-2.0-flash":      {"rpd": 1500, "rpm": 15},
    "gemini-2.0-flash-lite": {"rpd": 1500, "rpm": 30},
}

MODEL_FALLBACK_ORDER = [
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]

# ─── Helpers ──────────────────────────────────────────────────────────────────
def seconds_until_midnight_utc() -> int:
    now = datetime.now(timezone.utc)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((midnight - now).total_seconds())

def fmt_duration(s: int) -> str:
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}h {m}m {sec}s"

def next_fallback_model(current: str) -> str:
    try:
        idx = MODEL_FALLBACK_ORDER.index(current)
        return MODEL_FALLBACK_ORDER[(idx + 1) % len(MODEL_FALLBACK_ORDER)]
    except ValueError:
        return MODEL_FALLBACK_ORDER[0]

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Anime Sensei",
    page_icon="🏯",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Base reset ─────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stApp"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    background: #08071a !important;
    color: #e2e8f0 !important;
    -webkit-font-smoothing: antialiased;
}

/* ── Animated background ────────────────────────────────────────────────── */
[data-testid="stApp"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 70% 55% at 15% 15%,  rgba(124,58,237,0.22) 0%, transparent 55%),
        radial-gradient(ellipse 55% 45% at 85% 85%,  rgba(37,99,235,0.18) 0%,  transparent 55%),
        radial-gradient(ellipse 45% 40% at 55% 5%,   rgba(219,39,119,0.10) 0%, transparent 45%),
        radial-gradient(ellipse 60% 50% at 50% 100%, rgba(5,150,105,0.08)  0%, transparent 50%),
        linear-gradient(160deg, #08071a 0%, #0f0d2e 45%, #0a1628 100%);
    pointer-events: none;
    z-index: 0;
}

/* ── Scrollbar ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.03); }
::-webkit-scrollbar-thumb { background: rgba(124,58,237,0.45); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: rgba(124,58,237,0.7); }

/* ── Hide Streamlit chrome ──────────────────────────────────────────────── */
#MainMenu, footer, [data-testid="stDecoration"],
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stHeader"] {
    background: transparent !important;
    height: 0 !important;
    min-height: 0 !important;
}

/* ── Main content container ─────────────────────────────────────────────── */
[data-testid="stMainBlockContainer"] {
    padding-top: 2rem    !important;
    padding-bottom: 4rem !important;
    max-width: 740px     !important;
}

/* ── Sidebar ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: rgba(8, 7, 26, 0.72) !important;
    backdrop-filter: blur(32px) saturate(160%) !important;
    -webkit-backdrop-filter: blur(32px) saturate(160%) !important;
    border-right: 1px solid rgba(255,255,255,0.07) !important;
}
[data-testid="stSidebar"] > div { background: transparent !important; }
[data-testid="stSidebarContent"] { padding: 1.5rem 1.25rem 2rem !important; }

/* Sidebar headings */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: rgba(255,255,255,0.55) !important;
    font-size: 0.68rem    !important;
    font-weight: 700      !important;
    letter-spacing: 0.13em !important;
    text-transform: uppercase !important;
    margin: 1.4rem 0 0.55rem !important;
}

/* ── Labels ─────────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label {
    color: rgba(255,255,255,0.5) !important;
    font-size: 0.68rem    !important;
    font-weight: 600      !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    margin-bottom: 5px   !important;
}

/* ── Text inputs ─────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input {
    background:  rgba(255,255,255,0.06) !important;
    border:      1px solid rgba(255,255,255,0.1) !important;
    border-radius: 13px  !important;
    color:       #f1f5f9 !important;
    font-size:   0.95rem !important;
    padding:     0.65rem 0.9rem !important;
    min-height:  46px    !important;
    backdrop-filter: blur(8px) !important;
    transition:  border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: rgba(124,58,237,0.65) !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.18), 0 0 18px rgba(124,58,237,0.12) !important;
    outline: none !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: rgba(255,255,255,0.22) !important;
}

/* ── Selectbox ──────────────────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background:    rgba(255,255,255,0.06) !important;
    border:        1px solid rgba(255,255,255,0.1) !important;
    border-radius: 13px !important;
    color:         #f1f5f9 !important;
    min-height:    46px !important;
    backdrop-filter: blur(8px) !important;
}
[data-testid="stSelectbox"] span { color: #f1f5f9 !important; }
[data-testid="stSelectbox"] svg  { fill: rgba(255,255,255,0.4) !important; }

/* ── Primary button ──────────────────────────────────────────────────────── */
.stButton > button[kind="primary"],
.stButton > button {
    background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 55%, #2563eb 100%) !important;
    color:       #fff  !important;
    border:      none  !important;
    border-radius: 15px !important;
    font-weight: 650   !important;
    font-size:   0.97rem !important;
    letter-spacing: 0.015em !important;
    min-height:  54px  !important;
    width:       100%  !important;
    box-shadow:  0 0 28px rgba(124,58,237,0.38), 0 4px 18px rgba(0,0,0,0.45) !important;
    transition:  transform 0.18s ease, box-shadow 0.18s ease !important;
    position:    relative !important;
    overflow:    hidden !important;
}
.stButton > button::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(255,255,255,0.1) 0%, transparent 60%);
    border-radius: 15px;
    pointer-events: none;
}
.stButton > button:hover:not(:disabled) {
    transform: translateY(-2px) !important;
    box-shadow: 0 0 42px rgba(124,58,237,0.58), 0 8px 28px rgba(0,0,0,0.55) !important;
}
.stButton > button:active:not(:disabled) { transform: translateY(1px) !important; }
.stButton > button:disabled {
    background: rgba(255,255,255,0.07) !important;
    color: rgba(255,255,255,0.28) !important;
    box-shadow: none !important;
    cursor: not-allowed !important;
}

/* ── Alert boxes ─────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    background: rgba(255,255,255,0.05) !important;
    backdrop-filter: blur(18px) !important;
    -webkit-backdrop-filter: blur(18px) !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    font-size: 0.875rem !important;
    padding: 0.7rem 0.9rem !important;
}
[data-testid="stAlert"] p,
[data-testid="stAlert"] span { color: rgba(255,255,255,0.82) !important; }
[data-testid="stAlert"] a    { color: #a78bfa !important; text-decoration: none !important; }
[data-testid="stAlert"] a:hover { text-decoration: underline !important; }

/* ── Expander ────────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(16px) !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] p {
    color: rgba(255,255,255,0.7) !important;
    font-size: 0.83rem !important;
}
[data-testid="stExpander"] svg { fill: rgba(255,255,255,0.35) !important; }

/* ── Divider ─────────────────────────────────────────────────────────────── */
hr { border-color: rgba(255,255,255,0.07) !important; margin: 1.1rem 0 !important; }

/* ── Spinner ─────────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] > div > div { border-top-color: #7c3aed !important; }

/* ── Markdown text ───────────────────────────────────────────────────────── */
h1, h2, h3 { color: #f1f5f9 !important; }
.stMarkdown p,
.stMarkdown li { color: rgba(255,255,255,0.75) !important; }
[data-testid="stCaptionContainer"] p { color: rgba(255,255,255,0.38) !important; font-size: 0.78rem !important; }

/* ── Mobile ──────────────────────────────────────────────────────────────── */
@media (max-width: 640px) {
    .hero-title   { font-size: 2.1rem !important; }
    .hero-sub     { font-size: 0.9rem !important; }
    .rec-inner    { padding: 1rem 1.1rem !important; }
    .rec-title    { font-size: 1rem !important; }
    .rec-reason   { font-size: 0.83rem !important; }
    [data-testid="stMainBlockContainer"] {
        padding-left: 0.75rem  !important;
        padding-right: 0.75rem !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ─── Session state defaults ────────────────────────────────────────────────────
for _k, _v in [
    ("quota_error_model", None),
    ("quota_error_ts", None),
    ("validation_result", None),
    ("last_validated_user", None),
    ("recommendations", None),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─── Hero header ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding: 1.5rem 0 2rem;">
    <div style="font-size:3.2rem; margin-bottom:0.6rem;
                filter: drop-shadow(0 0 24px rgba(124,58,237,0.55));">🏯</div>
    <h1 class="hero-title" style="
        font-size: 2.6rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1.15;
        background: linear-gradient(135deg, #f8fafc 0%, #c4b5fd 45%, #93c5fd 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; margin-bottom: 0.5rem;">
        Anime Sensei
    </h1>
    <p class="hero-sub" style="
        color: rgba(255,255,255,0.45); font-size: 1rem; font-weight: 400;
        letter-spacing: 0.01em; max-width: 380px; margin: 0 auto;">
        Discover your next obsession, powered by AI&nbsp;&amp;&nbsp;your AniList history
    </p>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 0.5rem 0 1rem;">
        <span style="font-size:1.6rem;">🏯</span>
        <div style="font-size:0.7rem; font-weight:700; letter-spacing:0.15em;
                    text-transform:uppercase; color:rgba(255,255,255,0.35); margin-top:4px;">
            Anime Sensei
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.header("Gemini API Key")

    saved_key = st_javascript("localStorage.getItem('animeSenseiGeminiKey') ?? ''")
    if "api_key_input" not in st.session_state:
        st.session_state["api_key_input"] = saved_key if isinstance(saved_key, str) else ""

    user_api_key = st.text_input(
        "API Key",
        value=st.session_state["api_key_input"],
        type="password",
        key="api_key_widget",
        placeholder="AIza...",
        label_visibility="collapsed",
    )

    if user_api_key != st.session_state["api_key_input"]:
        st.session_state["api_key_input"] = user_api_key
        safe_key = user_api_key.replace("'", "\\'")
        if user_api_key:
            st_javascript(f"localStorage.setItem('animeSenseiGeminiKey', '{safe_key}')")
        else:
            st_javascript("localStorage.removeItem('animeSenseiGeminiKey')")

    if user_api_key:
        st.success("Key saved to this browser.", icon="✅")
        if st.button("Clear key", use_container_width=True):
            st.session_state["api_key_input"] = ""
            st_javascript("localStorage.removeItem('animeSenseiGeminiKey')")
            st.rerun()
    else:
        st.markdown("""
        <div style="background:rgba(124,58,237,0.12); border:1px solid rgba(124,58,237,0.28);
                    border-radius:12px; padding:0.7rem 0.85rem; font-size:0.82rem;
                    color:rgba(255,255,255,0.7); line-height:1.5;">
            🔑 Required to use the app.<br>
            <a href="https://aistudio.google.com/app/apikey" target="_blank"
               style="color:#a78bfa; text-decoration:none; font-weight:600;">
               Get your free key →
            </a>
        </div>
        """, unsafe_allow_html=True)

    st.header("AniList Profile")

    username = st.text_input(
        "Username",
        placeholder="your_username",
        label_visibility="collapsed",
    )

    if username and username != st.session_state["last_validated_user"]:
        with st.spinner("Checking profile…"):
            try:
                r = requests.get(f"{BACKEND_URL}/validate/{username}", timeout=8)
                if r.status_code == 200:
                    count = r.json().get("completed_count", 0)
                    st.session_state["validation_result"] = ("ok", f"{count} completed anime found.")
                else:
                    detail = r.json().get("detail", "Unknown error")
                    st.session_state["validation_result"] = ("error", detail)
            except Exception:
                st.session_state["validation_result"] = ("warn", "Cannot reach backend.")
        st.session_state["last_validated_user"] = username

    if st.session_state["validation_result"]:
        status, msg = st.session_state["validation_result"]
        icons = {"ok": "✅", "error": "🚫", "warn": "⚠️"}
        colors = {
            "ok":   ("rgba(16,185,129,0.12)", "rgba(16,185,129,0.35)", "#6ee7b7"),
            "error":("rgba(239,68,68,0.12)",  "rgba(239,68,68,0.35)",  "#fca5a5"),
            "warn": ("rgba(245,158,11,0.12)", "rgba(245,158,11,0.35)", "#fcd34d"),
        }
        bg, border, text = colors.get(status, colors["warn"])
        st.markdown(f"""
        <div style="background:{bg}; border:1px solid {border}; border-radius:12px;
                    padding:0.6rem 0.85rem; font-size:0.82rem; color:{text};
                    display:flex; gap:6px; align-items:flex-start; line-height:1.45;">
            <span>{icons.get(status,'ℹ️')}</span><span>{msg}</span>
        </div>
        """, unsafe_allow_html=True)

    st.header("Model")

    model_choice = st.selectbox(
        "Model",
        options=MODELS,
        index=0,
        label_visibility="collapsed",
    )

    if st.session_state["quota_error_model"] == model_choice:
        suggested = next_fallback_model(model_choice)
        st.markdown(f"""
        <div style="background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.28);
                    border-radius:12px; padding:0.6rem 0.85rem; font-size:0.8rem;
                    color:#fcd34d; line-height:1.5;">
            ⚠️ Quota hit. Try <strong>{suggested}</strong>.
        </div>
        """, unsafe_allow_html=True)

    with st.expander("📊 Daily limits"):
        rows = ""
        for m, lim in FREE_TIER.items():
            active = "font-weight:600; color:#c4b5fd;" if m == model_choice else "color:rgba(255,255,255,0.5);"
            rows += f"""
            <div style="display:flex; justify-content:space-between; align-items:center;
                        padding:4px 0; border-bottom:1px solid rgba(255,255,255,0.05); {active}">
                <span style="font-size:0.75rem;">{m}</span>
                <span style="font-size:0.75rem; opacity:0.7;">~{lim['rpd']//2} recs/day</span>
            </div>"""
        st.markdown(f"""
        <div style="padding:0.25rem 0 0.5rem;">
            {rows}
            <div style="font-size:0.7rem; color:rgba(255,255,255,0.3); margin-top:8px;">
                Resets at midnight UTC · 2 calls per request
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:1.5rem; background:rgba(255,255,255,0.04);
                border:1px solid rgba(255,255,255,0.07); border-radius:12px;
                padding:0.65rem 0.85rem; font-size:0.78rem; color:rgba(255,255,255,0.4);
                line-height:1.5;">
        ℹ️ Your AniList profile must be set to <strong style="color:rgba(255,255,255,0.6);">public</strong>.
    </div>
    """, unsafe_allow_html=True)

# ─── Quota countdown state ────────────────────────────────────────────────────
quota_lock_msg = ""
if st.session_state["quota_error_ts"]:
    secs = seconds_until_midnight_utc()
    if secs > 0:
        quota_lock_msg = fmt_duration(secs)

# ─── Status strip (inline chips) ─────────────────────────────────────────────
profile_ok = st.session_state.get("validation_result", ("", ""))[0] == "ok"

key_chip   = ('<span style="color:#6ee7b7;">● Key ready</span>' if user_api_key
              else '<span style="color:#fca5a5;">● No key</span>')
user_chip  = (f'<span style="color:#6ee7b7;">● {username}</span>' if profile_ok
              else ('<span style="color:#fcd34d;">● Enter username</span>' if not username
                   else '<span style="color:#fca5a5;">● Invalid profile</span>'))
model_chip = f'<span style="color:#c4b5fd;">● {model_choice}</span>'

st.markdown(f"""
<div style="display:flex; flex-wrap:wrap; gap:10px; justify-content:center;
            margin-bottom:1.5rem; font-size:0.78rem; font-weight:500;
            letter-spacing:0.02em;">
    {key_chip} {user_chip} {model_chip}
</div>
""", unsafe_allow_html=True)

# ─── CTA Button ───────────────────────────────────────────────────────────────
button_disabled = not user_api_key or not username or not profile_ok

if st.button("✦ Get Recommendations", disabled=button_disabled,
             type="primary", use_container_width=True):
    st.session_state["recommendations"] = None
    with st.spinner(f"Reading {username}'s taste…"):
        try:
            resp = requests.get(
                f"{BACKEND_URL}/recommend/{username}",
                params={"model_choice": model_choice},
                headers={"x-gemini-api-key": user_api_key},
                timeout=60,
            )

            if resp.status_code == 200:
                st.session_state["recommendations"] = resp.json()
                st.session_state["quota_error_model"] = None
                st.session_state["quota_error_ts"] = None

            elif resp.status_code == 429:
                detail = resp.json().get("detail", "Quota exceeded.")
                st.session_state["quota_error_model"] = model_choice
                st.session_state["quota_error_ts"] = time.time()
                secs = seconds_until_midnight_utc()
                suggested = next_fallback_model(model_choice)
                st.markdown(f"""
                <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.25);
                            border-radius:16px; padding:1.1rem 1.25rem; margin:1rem 0;">
                    <div style="font-size:0.95rem; font-weight:600; color:#fca5a5; margin-bottom:6px;">
                        ⏱ Quota reached
                    </div>
                    <div style="font-size:0.85rem; color:rgba(255,255,255,0.6); line-height:1.6;">
                        {detail}<br>
                        Resets in <strong style="color:#fcd34d;">{fmt_duration(secs)}</strong> (midnight UTC).<br>
                        Try switching to <strong style="color:#c4b5fd;">{suggested}</strong> in the sidebar.
                    </div>
                </div>
                """, unsafe_allow_html=True)

            elif resp.status_code in (400, 401, 403, 404):
                detail = resp.json().get("detail", "Request failed.")
                st.markdown(f"""
                <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.22);
                            border-radius:16px; padding:1rem 1.2rem; margin:1rem 0;
                            font-size:0.88rem; color:#fca5a5;">
                    🚫 {detail}
                </div>
                """, unsafe_allow_html=True)

            else:
                st.error(f"Unexpected error (HTTP {resp.status_code}). Try again.")

        except requests.exceptions.ConnectionError:
            st.error("Cannot reach the backend.")
        except requests.exceptions.Timeout:
            st.error("Request timed out — try a faster model like gemini-2.5-flash-lite.")
        except Exception as e:
            st.error(f"Something went wrong: {e}")

# ─── Recommendation cards ─────────────────────────────────────────────────────
recs = st.session_state.get("recommendations")
if recs:
    st.markdown(f"""
    <div style="text-align:center; margin: 1.75rem 0 1.25rem;">
        <div style="font-size:0.7rem; font-weight:700; letter-spacing:0.15em;
                    text-transform:uppercase; color:rgba(255,255,255,0.35);
                    margin-bottom:6px;">For {username}</div>
        <div style="font-size:1.45rem; font-weight:700; color:#f1f5f9;">
            Your Picks
        </div>
    </div>
    """, unsafe_allow_html=True)

    cards_html = ""
    for i, rec in enumerate(recs):
        title  = rec.get("title", "Unknown")
        reason = rec.get("reason", "")
        score  = rec.get("match_score")

        if isinstance(score, int):
            if score >= 85:
                sc, sb = "#86efac", "rgba(134,239,172,0.12)"
            elif score >= 70:
                sc, sb = "#fde68a", "rgba(253,230,138,0.12)"
            else:
                sc, sb = "#fca5a5", "rgba(252,165,165,0.12)"
            score_html = f"""
            <div style="display:inline-flex; align-items:center; gap:4px;
                        padding:3px 11px; border-radius:50px;
                        border:1px solid {sc}55; background:{sb};
                        color:{sc}; font-weight:700; font-size:0.88rem;">
                {score}%
                <span style="font-size:0.65rem; font-weight:500;
                             opacity:0.65; text-transform:uppercase; letter-spacing:0.06em;">
                    match
                </span>
            </div>"""
        else:
            score_html = ""

        cards_html += f"""
        <div style="
            background: rgba(255,255,255,0.045);
            backdrop-filter: blur(28px) saturate(180%);
            -webkit-backdrop-filter: blur(28px) saturate(180%);
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 22px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.07);
            margin-bottom: 0.85rem;
            animation: fadeUp 0.45s ease {i*0.07}s both;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        " onmouseover="this.style.transform='translateY(-3px)';this.style.boxShadow='0 14px 40px rgba(0,0,0,0.38), 0 0 0 1px rgba(124,58,237,0.2)'"
           onmouseout="this.style.transform='';this.style.boxShadow='0 8px 32px rgba(0,0,0,0.28)'">
            <div style="height:2px; background:linear-gradient(90deg,#7c3aed,#4f46e5,#2563eb); opacity:0.65;"></div>
            <div class="rec-inner" style="padding:1.2rem 1.45rem;">
                <div style="display:flex; justify-content:space-between;
                            align-items:center; margin-bottom:0.55rem;">
                    <span style="font-size:0.68rem; font-weight:700; letter-spacing:0.12em;
                                 text-transform:uppercase; color:rgba(124,58,237,0.75);">
                        #{i+1}
                    </span>
                    {score_html}
                </div>
                <h3 class="rec-title" style="
                    font-size:1.08rem; font-weight:700; color:#f1f5f9;
                    margin:0 0 0.45rem; line-height:1.3;">
                    {title}
                </h3>
                <p class="rec-reason" style="
                    font-size:0.865rem; color:rgba(226,232,240,0.62);
                    line-height:1.65; margin:0;">
                    {reason}
                </p>
            </div>
        </div>
        """

    st.markdown(f"""
    <style>
    @keyframes fadeUp {{
        from {{ opacity:0; transform:translateY(18px); }}
        to   {{ opacity:1; transform:translateY(0);    }}
    }}
    </style>
    {cards_html}
    """, unsafe_allow_html=True)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding:2.5rem 0 0.5rem;">
    <div style="width:40px; height:1px; background:rgba(255,255,255,0.1);
                margin:0 auto 1rem;"></div>
    <div style="font-size:0.75rem; color:rgba(255,255,255,0.25); letter-spacing:0.06em;">
        FastAPI &nbsp;·&nbsp; Google Gemini &nbsp;·&nbsp; AniList &nbsp;·&nbsp; Streamlit
    </div>
</div>
""", unsafe_allow_html=True)
