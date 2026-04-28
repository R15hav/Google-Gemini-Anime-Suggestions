import os
import time
from datetime import datetime, timezone, timedelta

import requests
import streamlit as st
import streamlit.components.v1 as components
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
    initial_sidebar_state="collapsed",
)

# ─── Session state ────────────────────────────────────────────────────────────
for _k, _v in [
    ("cfg_api_key",          ""),
    ("cfg_username",         ""),
    ("cfg_model",            "gemini-2.5-flash-lite"),
    ("cfg_key_loaded",       False),
    ("quota_error_model",    None),
    ("quota_error_ts",       None),
    ("validation_result",    None),
    ("last_validated_user",  None),
    ("recommendations",      None),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─── Load API key from localStorage on first page load ───────────────────────
# Runs once so the key is available before the settings modal is ever opened.
if not st.session_state["cfg_key_loaded"]:
    _saved = st_javascript("localStorage.getItem('animeSenseiGeminiKey') ?? ''")
    # st_javascript returns 0 (int) on the first render before JS has executed.
    # Only mark loaded once we receive an actual string so the rerun captures the real value.
    if isinstance(_saved, str):
        if _saved:
            st.session_state["cfg_api_key"] = _saved
        st.session_state["cfg_key_loaded"] = True

# ─── Settings modal ───────────────────────────────────────────────────────────
@st.dialog("Settings", width="small")
def settings_dialog():
    st.markdown("""
    <style>
    /* Glass morphism for the dialog */
    [data-testid="stModal"] > div,
    [data-testid="stModal"] > div > div {
        background: rgba(12,10,35,0.88) !important;
        backdrop-filter: blur(36px) saturate(160%) !important;
        -webkit-backdrop-filter: blur(36px) saturate(160%) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 24px !important;
        box-shadow: 0 24px 64px rgba(0,0,0,0.6), 0 0 0 1px rgba(124,58,237,0.15) !important;
    }
    /* Dialog header */
    [data-testid="stModal"] h2 {
        background: linear-gradient(135deg, #f8fafc 0%, #c4b5fd 50%, #93c5fd 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
        font-weight: 700 !important;
        font-size: 1.15rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── API Key ──────────────────────────────────────────────────────────────
    st.markdown(
        '<p style="font-size:.7rem;font-weight:700;letter-spacing:.1em;'
        'text-transform:uppercase;color:rgba(255,255,255,.5);margin-bottom:4px;">🔑 Gemini API Key</p>',
        unsafe_allow_html=True,
    )
    new_key = st.text_input(
        "key", value=st.session_state["cfg_api_key"],
        type="password", placeholder="AIza…",
        label_visibility="collapsed",
    )
    if new_key != st.session_state["cfg_api_key"]:
        st.session_state["cfg_api_key"] = new_key
        _safe = new_key.replace("'", "\\'")
        if new_key:
            st_javascript(f"localStorage.setItem('animeSenseiGeminiKey','{_safe}')")
        else:
            st_javascript("localStorage.removeItem('animeSenseiGeminiKey')")

    if st.session_state["cfg_api_key"]:
        col_s, col_c = st.columns([3, 1])
        with col_s:
            st.success("Saved to this browser.", icon="✅")
        with col_c:
            if st.button("Clear", use_container_width=True):
                st.session_state["cfg_api_key"] = ""
                st_javascript("localStorage.removeItem('animeSenseiGeminiKey')")
                st.rerun()
    else:
        st.markdown(
            '<div style="font-size:.82rem;color:rgba(255,255,255,.55);padding:4px 0;">'
            'Get a free key at <a href="https://aistudio.google.com/app/apikey" target="_blank" '
            'style="color:#a78bfa;text-decoration:none;font-weight:600;">aistudio.google.com →</a></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ── AniList Username ─────────────────────────────────────────────────────
    st.markdown(
        '<p style="font-size:.7rem;font-weight:700;letter-spacing:.1em;'
        'text-transform:uppercase;color:rgba(255,255,255,.5);margin-bottom:4px;">🎌 AniList Username</p>',
        unsafe_allow_html=True,
    )
    new_user = st.text_input(
        "user", value=st.session_state["cfg_username"],
        placeholder="your_username",
        label_visibility="collapsed",
    )
    if new_user != st.session_state["cfg_username"]:
        st.session_state["cfg_username"] = new_user
        st.session_state["validation_result"] = None
        st.session_state["last_validated_user"] = None

    if new_user and new_user != st.session_state["last_validated_user"]:
        with st.spinner("Checking profile…"):
            try:
                r = requests.get(f"{BACKEND_URL}/validate/{new_user}", timeout=8)
                if r.status_code == 200:
                    cnt = r.json().get("completed_count", 0)
                    st.session_state["validation_result"] = ("ok", f"{cnt} completed anime found.")
                else:
                    st.session_state["validation_result"] = ("error", r.json().get("detail", "Unknown error"))
            except Exception:
                st.session_state["validation_result"] = ("warn", "Cannot reach backend.")
        st.session_state["last_validated_user"] = new_user

    if st.session_state["validation_result"]:
        status, msg = st.session_state["validation_result"]
        {"ok": st.success, "error": st.error, "warn": st.warning}[status](msg)

    st.divider()

    # ── Model ────────────────────────────────────────────────────────────────
    st.markdown(
        '<p style="font-size:.7rem;font-weight:700;letter-spacing:.1em;'
        'text-transform:uppercase;color:rgba(255,255,255,.5);margin-bottom:4px;">🤖 Gemini Model</p>',
        unsafe_allow_html=True,
    )
    model_idx = MODELS.index(st.session_state["cfg_model"]) if st.session_state["cfg_model"] in MODELS else 0
    new_model = st.selectbox("model", options=MODELS, index=model_idx, label_visibility="collapsed")
    st.session_state["cfg_model"] = new_model

    if st.session_state["quota_error_model"] == new_model:
        st.warning(f"Quota hit. Try **{next_fallback_model(new_model)}**.", icon="⚠️")

    lim = FREE_TIER.get(new_model, {})
    if lim:
        st.caption(f"Free tier: {lim['rpd']} req/day (~{lim['rpd']//2} recs) · {lim['rpm']} rpm · Resets midnight UTC")

    st.divider()
    st.caption("ℹ️ Your AniList list must be **public**.")

# ─── Hidden native gear trigger ───────────────────────────────────────────────
# This button is hidden by the JS below. The floating gear clicks it to open
# the dialog without any Streamlit component needing to be inside an HTML onclick.
if st.button("⚙", key="__gear_trigger__"):
    settings_dialog()

# ─── Inject floating gear button via component iframe ────────────────────────
# components.html runs inside an iframe served on the same origin as Streamlit,
# so window.parent.document is accessible without CORS issues.
components.html("""
<script>
(function () {
    var pd = window.parent.document;

    function injectGear() {
        if (pd.getElementById('sensei-gear-fab')) return;
        var btn = pd.createElement('button');
        btn.id    = 'sensei-gear-fab';
        btn.title = 'Settings';
        btn.textContent = '⚙️';
        btn.style.cssText = [
            'position:fixed', 'bottom:1.75rem', 'right:1.75rem',
            'width:58px', 'height:58px', 'border-radius:50%',
            'background:linear-gradient(135deg,#7c3aed 0%,#4f46e5 55%,#2563eb 100%)',
            'border:1.5px solid rgba(255,255,255,0.22)',
            'color:white', 'font-size:1.4rem', 'line-height:1',
            'cursor:pointer', 'z-index:99999',
            'display:flex', 'align-items:center', 'justify-content:center',
            'box-shadow:0 4px 24px rgba(124,58,237,.55),0 2px 8px rgba(0,0,0,.35)',
            'transition:transform .22s cubic-bezier(.34,1.56,.64,1),box-shadow .18s ease',
            '-webkit-tap-highlight-color:transparent', 'outline:none'
        ].join(';');

        btn.addEventListener('mouseenter', function () {
            btn.style.transform  = 'scale(1.12) rotate(45deg)';
            btn.style.boxShadow  = '0 6px 36px rgba(124,58,237,.75)';
        });
        btn.addEventListener('mouseleave', function () {
            btn.style.transform  = '';
            btn.style.boxShadow  = '0 4px 24px rgba(124,58,237,.55),0 2px 8px rgba(0,0,0,.35)';
        });
        btn.addEventListener('click', function () {
            /* Find and click the hidden Streamlit gear trigger */
            var btns = pd.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                if (btns[i].textContent.trim() === '⚙') { /* ⚙ */
                    btns[i].click();
                    return;
                }
            }
        });

        pd.body.appendChild(btn);
    }

    function hideNativeTrigger() {
        var btns = pd.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim() === '⚙') { /* ⚙ */
                var wrap = btns[i].closest('[data-testid="stButton"]');
                if (wrap && wrap.style.position !== 'absolute') {
                    wrap.style.cssText =
                        'position:absolute;width:0;height:0;overflow:hidden;' +
                        'opacity:0;pointer-events:none;margin:0;padding:0;';
                }
            }
        }
    }

    /* Initial run */
    injectGear();
    hideNativeTrigger();

    /* Re-hide on every Streamlit re-render (Streamlit rewrites the DOM) */
    new MutationObserver(hideNativeTrigger)
        .observe(pd.body, { childList: true, subtree: true });
})();
</script>
""", height=0)

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stApp"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: #08071a !important;
    color: #e2e8f0 !important;
    -webkit-font-smoothing: antialiased;
}

[data-testid="stApp"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 70% 55% at 15% 15%,  rgba(124,58,237,.22)  0%, transparent 55%),
        radial-gradient(ellipse 55% 45% at 85% 85%,  rgba(37,99,235,.18)   0%, transparent 55%),
        radial-gradient(ellipse 45% 40% at 55% 5%,   rgba(219,39,119,.10)  0%, transparent 45%),
        linear-gradient(160deg, #08071a 0%, #0f0d2e 45%, #0a1628 100%);
    pointer-events: none;
    z-index: 0;
}

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,.03); }
::-webkit-scrollbar-thumb { background: rgba(124,58,237,.45); border-radius: 99px; }

#MainMenu, footer, [data-testid="stDecoration"],
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stHeader"] { background: transparent !important; height: 0 !important; min-height: 0 !important; }
[data-testid="stSidebar"] { display: none !important; }

/* Hide the 0-height component iframe */
[data-testid="stCustomComponentV1"] iframe { display: none !important; }

[data-testid="stMainBlockContainer"] {
    padding-top: 2rem !important;
    padding-bottom: 5rem !important;
    max-width: 740px !important;
}

/* ── Labels ── */
[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label {
    color: rgba(255,255,255,.5) !important;
    font-size: .68rem !important;
    font-weight: 600 !important;
    letter-spacing: .1em !important;
    text-transform: uppercase !important;
}

/* ── Inputs ── */
[data-testid="stTextInput"] input {
    background:  rgba(255,255,255,.06) !important;
    border:      1px solid rgba(255,255,255,.1) !important;
    border-radius: 13px !important;
    color:       #f1f5f9 !important;
    font-size:   .95rem !important;
    padding:     .65rem .9rem !important;
    min-height:  46px !important;
    backdrop-filter: blur(8px) !important;
    transition:  border-color .2s, box-shadow .2s !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: rgba(124,58,237,.65) !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,.18), 0 0 18px rgba(124,58,237,.12) !important;
    outline: none !important;
}
[data-testid="stTextInput"] input::placeholder { color: rgba(255,255,255,.22) !important; }

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background:    rgba(255,255,255,.06) !important;
    border:        1px solid rgba(255,255,255,.1) !important;
    border-radius: 13px !important;
    color:         #f1f5f9 !important;
    min-height:    46px !important;
    backdrop-filter: blur(8px) !important;
}
[data-testid="stSelectbox"] span { color: #f1f5f9 !important; }
[data-testid="stSelectbox"] svg  { fill: rgba(255,255,255,.4) !important; }

/* ── Primary button ── */
.stButton > button {
    background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 55%, #2563eb 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 15px !important;
    font-weight: 650 !important;
    font-size: .97rem !important;
    min-height: 54px !important;
    width: 100% !important;
    box-shadow: 0 0 28px rgba(124,58,237,.38), 0 4px 18px rgba(0,0,0,.45) !important;
    transition: transform .18s ease, box-shadow .18s ease !important;
    position: relative !important;
    overflow: hidden !important;
}
.stButton > button::after {
    content: '';
    position: absolute; inset: 0;
    background: linear-gradient(180deg, rgba(255,255,255,.1) 0%, transparent 60%);
    border-radius: 15px;
    pointer-events: none;
}
.stButton > button:hover:not(:disabled) {
    transform: translateY(-2px) !important;
    box-shadow: 0 0 42px rgba(124,58,237,.58), 0 8px 28px rgba(0,0,0,.55) !important;
}
.stButton > button:active:not(:disabled) { transform: translateY(1px) !important; }
.stButton > button:disabled {
    background: rgba(255,255,255,.07) !important;
    color: rgba(255,255,255,.28) !important;
    box-shadow: none !important;
    cursor: not-allowed !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
    background: rgba(255,255,255,.05) !important;
    backdrop-filter: blur(18px) !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255,255,255,.09) !important;
    font-size: .875rem !important;
}
[data-testid="stAlert"] p,
[data-testid="stAlert"] span { color: rgba(255,255,255,.82) !important; }
[data-testid="stAlert"] a    { color: #a78bfa !important; text-decoration: none !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,.04) !important;
    border: 1px solid rgba(255,255,255,.08) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] p { color: rgba(255,255,255,.7) !important; font-size: .83rem !important; }

/* ── Dialog ── */
[data-testid="stModal"],
div[role="dialog"] {
    background: rgba(8,7,26,.6) !important;
    backdrop-filter: blur(12px) !important;
}
[data-testid="stModal"] > div > div,
div[role="dialog"] > div {
    background: rgba(12,10,35,.9) !important;
    backdrop-filter: blur(36px) saturate(160%) !important;
    -webkit-backdrop-filter: blur(36px) saturate(160%) !important;
    border: 1px solid rgba(255,255,255,.1) !important;
    border-radius: 24px !important;
    box-shadow: 0 24px 64px rgba(0,0,0,.6), 0 0 0 1px rgba(124,58,237,.12) !important;
}

hr { border-color: rgba(255,255,255,.07) !important; margin: 1rem 0 !important; }
[data-testid="stSpinner"] > div > div { border-top-color: #7c3aed !important; }
h1, h2, h3 { color: #f1f5f9 !important; }
.stMarkdown p { color: rgba(255,255,255,.75) !important; }
[data-testid="stCaptionContainer"] p { color: rgba(255,255,255,.38) !important; font-size: .78rem !important; }

@media (max-width: 640px) {
    [data-testid="stMainBlockContainer"] { padding-left: .75rem !important; padding-right: .75rem !important; }
    .hero-title { font-size: 2.1rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ─── Hero ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding:1.5rem 0 2rem;">
    <div style="font-size:3.2rem;margin-bottom:.6rem;
                filter:drop-shadow(0 0 24px rgba(124,58,237,.55));">🏯</div>
    <h1 class="hero-title" style="
        font-size:2.6rem;font-weight:800;letter-spacing:-.03em;line-height:1.15;
        background:linear-gradient(135deg,#f8fafc 0%,#c4b5fd 45%,#93c5fd 100%);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
        background-clip:text;margin-bottom:.5rem;">
        Anime Sensei
    </h1>
    <p style="color:rgba(255,255,255,.45);font-size:1rem;max-width:360px;margin:0 auto;">
        Discover your next obsession, powered by AI&nbsp;&amp;&nbsp;your AniList history
    </p>
</div>
""", unsafe_allow_html=True)

# ─── Read settings from state ─────────────────────────────────────────────────
user_api_key = st.session_state["cfg_api_key"]
username     = st.session_state["cfg_username"]
model_choice = st.session_state["cfg_model"]

# ─── Status chips ─────────────────────────────────────────────────────────────
profile_ok = (st.session_state.get("validation_result") or ("", ""))[0] == "ok"

key_chip   = ('<span style="color:#6ee7b7;">● Key ready</span>'      if user_api_key
              else '<span style="color:#fca5a5;">● No key</span>')
user_chip  = (f'<span style="color:#6ee7b7;">● {username}</span>'    if profile_ok
              else ('<span style="color:#fcd34d;">● No profile</span>' if not username
                   else '<span style="color:#fca5a5;">● Invalid</span>'))
model_chip = f'<span style="color:#c4b5fd;">● {model_choice}</span>'

st.markdown(f"""
<div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:center;
            margin-bottom:1.5rem;font-size:.78rem;font-weight:500;letter-spacing:.02em;">
    {key_chip} {user_chip} {model_chip}
    <span style="color:rgba(255,255,255,.3);cursor:pointer;font-size:.75rem;"
          onclick="document.getElementById('sensei-gear-fab')?.click()">
        ✦ tap ⚙️ to configure
    </span>
</div>
""", unsafe_allow_html=True)

# ─── CTA button ───────────────────────────────────────────────────────────────
button_disabled = not user_api_key or not username or not profile_ok

# Quota countdown hint
if st.session_state["quota_error_ts"]:
    secs = seconds_until_midnight_utc()
    if secs > 0:
        st.markdown(f"""
        <div style="text-align:center;font-size:.82rem;color:#fcd34d;margin-bottom:.75rem;">
            ⏳ Quota resets in {fmt_duration(secs)} (midnight UTC)
        </div>""", unsafe_allow_html=True)

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
                st.session_state["quota_error_ts"]    = None

            elif resp.status_code == 429:
                detail = resp.json().get("detail", "Quota exceeded.")
                st.session_state["quota_error_model"] = model_choice
                st.session_state["quota_error_ts"]    = time.time()
                secs      = seconds_until_midnight_utc()
                suggested = next_fallback_model(model_choice)
                st.markdown(f"""
                <div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.25);
                            border-radius:16px;padding:1.1rem 1.25rem;margin:1rem 0;">
                    <div style="font-size:.95rem;font-weight:600;color:#fca5a5;margin-bottom:6px;">
                        ⏱ Quota reached
                    </div>
                    <div style="font-size:.85rem;color:rgba(255,255,255,.6);line-height:1.6;">
                        {detail}<br>
                        Resets in <strong style="color:#fcd34d;">{fmt_duration(secs)}</strong> (midnight UTC).<br>
                        Open ⚙️ Settings and try <strong style="color:#c4b5fd;">{suggested}</strong>.
                    </div>
                </div>
                """, unsafe_allow_html=True)

            elif resp.status_code in (400, 401, 403, 404):
                st.markdown(f"""
                <div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.22);
                            border-radius:16px;padding:1rem 1.2rem;margin:1rem 0;
                            font-size:.88rem;color:#fca5a5;">
                    🚫 {resp.json().get('detail','Request failed.')}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"Unexpected error (HTTP {resp.status_code}). Try again.")

        except requests.exceptions.ConnectionError:
            st.error("Cannot reach the backend.")
        except requests.exceptions.Timeout:
            st.error("Request timed out — try gemini-2.5-flash-lite.")
        except Exception as e:
            st.error(f"Something went wrong: {e}")

# ─── Recommendation cards ─────────────────────────────────────────────────────
recs = st.session_state.get("recommendations")
if recs:
    st.markdown(f"""
    <div style="text-align:center;margin:1.75rem 0 1.25rem;">
        <div style="font-size:.7rem;font-weight:700;letter-spacing:.15em;
                    text-transform:uppercase;color:rgba(255,255,255,.3);margin-bottom:6px;">
            For {username}
        </div>
        <div style="font-size:1.45rem;font-weight:700;color:#f1f5f9;">Your Picks</div>
    </div>
    """, unsafe_allow_html=True)

    cards = ""
    for i, rec in enumerate(recs):
        title  = rec.get("title", "Unknown")
        reason = rec.get("reason", "")
        score  = rec.get("match_score")
        if isinstance(score, int):
            sc, sb = (("#86efac","rgba(134,239,172,.12)") if score>=85
                      else ("#fde68a","rgba(253,230,138,.12)") if score>=70
                      else ("#fca5a5","rgba(252,165,165,.12)"))
            score_html = (f'<div style="display:inline-flex;align-items:center;gap:4px;'
                          f'padding:3px 11px;border-radius:50px;border:1px solid {sc}55;'
                          f'background:{sb};color:{sc};font-weight:700;font-size:.88rem;">'
                          f'{score}%<span style="font-size:.65rem;opacity:.65;text-transform:uppercase;'
                          f'letter-spacing:.06em;"> match</span></div>')
        else:
            score_html = ""

        cards += f"""
        <div style="
            background:rgba(255,255,255,.045);
            backdrop-filter:blur(28px) saturate(180%);
            -webkit-backdrop-filter:blur(28px) saturate(180%);
            border:1px solid rgba(255,255,255,.09);
            border-radius:22px;overflow:hidden;
            box-shadow:0 8px 32px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.07);
            margin-bottom:.85rem;
            animation:fadeUp .45s ease {i*.07}s both;">
            <div style="height:2px;background:linear-gradient(90deg,#7c3aed,#4f46e5,#2563eb);opacity:.65;"></div>
            <div style="padding:1.2rem 1.45rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.55rem;">
                    <span style="font-size:.68rem;font-weight:700;letter-spacing:.12em;
                                 text-transform:uppercase;color:rgba(124,58,237,.75);">#{i+1}</span>
                    {score_html}
                </div>
                <h3 style="font-size:1.08rem;font-weight:700;color:#f1f5f9;
                           margin:0 0 .45rem;line-height:1.3;">{title}</h3>
                <p style="font-size:.865rem;color:rgba(226,232,240,.62);
                          line-height:1.65;margin:0;">{reason}</p>
            </div>
        </div>"""

    st.markdown(f"""
    <style>
    @keyframes fadeUp {{
        from {{ opacity:0; transform:translateY(18px); }}
        to   {{ opacity:1; transform:translateY(0);    }}
    }}
    </style>
    {cards}
    """, unsafe_allow_html=True)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2.5rem 0 .5rem;">
    <div style="width:40px;height:1px;background:rgba(255,255,255,.1);margin:0 auto 1rem;"></div>
    <div style="font-size:.75rem;color:rgba(255,255,255,.25);letter-spacing:.06em;">
        FastAPI &nbsp;·&nbsp; Google Gemini &nbsp;·&nbsp; AniList &nbsp;·&nbsp; Streamlit
    </div>
</div>
""", unsafe_allow_html=True)
