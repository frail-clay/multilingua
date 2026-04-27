"""
MultiLingua — Multilingual AI Conversation Assistant
Dark editorial UI + fully local voice pipeline (Whisper + LLM + macOS TTS)
"""

from pathlib import Path
from PIL import Image, ImageDraw
import html
import json
import os
import time
import tempfile

import numpy as np
import requests
import scipy.io.wavfile
import sounddevice as sd
import streamlit as st
import streamlit.components.v1 as components
import whisper

from speak_multilang_mac import detect_language, speak_mac, VOICE_MAP, get_available_voices

# ─────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────
def make_favicon() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    amber = (212, 165, 116, 255)       # --ml-accent #d4a574
    glow  = (212, 165, 116, 60)        # soft outer ring
    draw.ellipse([0, 0, size - 1, size - 1], fill=glow)
    draw.ellipse([8, 8, size - 9, size - 9], fill=amber)
    return img

st.set_page_config(
    page_title="MultiLingua",
    page_icon=make_favicon(),
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────
def load_css() -> None:
    css = (Path(__file__).parent / "style.css").read_text()
    # <link> tags have no asterisks so st.markdown is safe here —
    # they land in the main document (not an iframe) so the browser
    # registers the font before any text is painted.
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?'
        'family=Instrument+Serif:ital@0;1'
        '&family=Inter:wght@400;500;600'
        '&family=JetBrains+Mono:wght@400;500'
        '&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )
    # st.html() bypasses the markdown parser so asterisks in CSS
    # selectors like [class*="stApp"] are preserved correctly.
    st.html(f"<style>{css}</style>")

load_css()

# ─────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────
def load_config() -> dict:
    try:
        return json.loads((Path(__file__).parent / "config.json").read_text())
    except Exception:
        return {}

config = load_config()
SAMPLERATE = 16000

def detect_loaded_model(api_url: str) -> str:
    try:
        base = api_url.split("/v1/")[0]
        r = requests.get(f"{base}/v1/models", timeout=3)
        models = r.json().get("data", [])
        if models:
            return models[0]["id"]
    except Exception:
        pass
    return config.get("MODEL_NAME", "meta-llama-3.1-8b-instruct")

LANG_FLAGS = {
    "en": "🇬🇧", "ar": "🇸🇦", "fr": "🇫🇷", "es": "🇪🇸",
    "de": "🇩🇪", "it": "🇮🇹", "pt": "🇵🇹", "hi": "🇮🇳",
    "ru": "🇷🇺", "zh": "🇨🇳", "zh-cn": "🇨🇳", "ja": "🇯🇵",
    "ko": "🇰🇷", "tr": "🇹🇷",
}

LANG_NAMES = {
    "en": "English",    "ar": "Arabic",     "fr": "French",
    "es": "Spanish",    "de": "German",     "it": "Italian",
    "pt": "Portuguese", "hi": "Hindi",      "ru": "Russian",
    "zh-cn": "Chinese", "zh": "Chinese",    "ja": "Japanese",
    "ko": "Korean",     "tr": "Turkish",
}

# Languages that read right-to-left
RTL_LANGS = {"ar", "he", "fa", "ur"}

# Display order for the language pill bar
LANGUAGES = [
    ("🇬🇧", "EN", "en"),   ("🇸🇦", "AR", "ar"),   ("🇫🇷", "FR", "fr"),
    ("🇩🇪", "DE", "de"),   ("🇪🇸", "ES", "es"),   ("🇮🇹", "IT", "it"),
    ("🇵🇹", "PT", "pt"),   ("🇮🇳", "HI", "hi"),   ("🇷🇺", "RU", "ru"),
    ("🇨🇳", "ZH", "zh-cn"), ("🇯🇵", "JA", "ja"),  ("🇰🇷", "KO", "ko"),
    ("🇹🇷", "TR", "tr"),
]

# ─────────────────────────────────────────────────────────────────────
# Models / resources  (cached across reruns)
# ─────────────────────────────────────────────────────────────────────
@st.cache_resource
def load_whisper():
    return whisper.load_model("base")

@st.cache_data(ttl=300)
def cached_available_voices() -> set:
    return get_available_voices()

whisper_model = load_whisper()

# ─────────────────────────────────────────────────────────────────────
# Core functions
# ─────────────────────────────────────────────────────────────────────
def record_audio(seconds: int = 5, indicator: st.delta_generator.DeltaGenerator | None = None) -> str:
    if indicator:
        indicator.markdown(
            f'<div class="ml-recording-indicator">'
            f'<span class="ml-recording-dot"></span>'
            f'RECORDING · {seconds}S'
            f'</div>',
            unsafe_allow_html=True,
        )
    audio = sd.rec(
        int(seconds * SAMPLERATE),
        samplerate=SAMPLERATE, channels=1, dtype="int16",
    )
    sd.wait()
    if indicator:
        indicator.empty()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        scipy.io.wavfile.write(f.name, SAMPLERATE, audio)
        return f.name


# Languages that use non-Latin scripts — Whisper base model sometimes
# romanises these unless you pass the language hint explicitly.
_NON_LATIN = {"hi", "ar", "zh", "ja", "ko", "ru"}

def transcribe(path: str) -> tuple[str, float, str | None]:
    # First pass: let Whisper detect the language from audio features.
    probe = whisper_model.transcribe(path)
    whisper_lang = probe.get("language")

    # Second pass: re-transcribe with the language hint for non-Latin scripts
    # so Whisper outputs Devanagari, Arabic, CJK, Cyrillic — not romanised text.
    if whisper_lang in _NON_LATIN:
        result = whisper_model.transcribe(path, language=whisper_lang)
    else:
        result = probe

    text = result["text"].strip()
    segs = result.get("segments", [])
    if segs:
        avg_no_speech = sum(s.get("no_speech_prob", 0.0) for s in segs) / len(segs)
        confidence = round(1.0 - avg_no_speech, 2)
    else:
        confidence = 0.90
    return text, confidence, whisper_lang


# Explicit script instructions for languages where LLMs tend to romanise.
_SCRIPT_INSTRUCTIONS = {
    "hi":    "Always write in Devanagari script. Never use Roman/Latin transliteration.",
    "ar":    "Always write in Arabic script. Never use Roman transliteration.",
    "zh-cn": "Always write in Chinese characters (Simplified).",
    "ja":    "Always write in Japanese script (Kanji, Hiragana, Katakana).",
    "ko":    "Always write in Korean (Hangul) script.",
    "ru":    "Always write in Cyrillic script.",
}

def query_llm(prompt: str, model: str, endpoint: str, lang_code: str) -> tuple[str, int]:
    lang_name = LANG_NAMES.get(lang_code, "the same language the user spoke in")
    script_note = _SCRIPT_INSTRUCTIONS.get(lang_code, "")
    system_prompt = (
        f"You are a helpful voice assistant. "
        f"Always respond in {lang_name}. "
        f"Never switch to another language. "
        f"{script_note}"
    ).strip()
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "stream": False,
    }
    try:
        r = requests.post(endpoint, json=payload, timeout=60)
        data = r.json()
        reply = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("completion_tokens", 0)
        return reply, tokens
    except Exception as e:
        return f"[Error: {e}]", 0


def ago_label(ts: float) -> str:
    delta = int(time.time() - ts)
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{delta // 60}m ago"
    return f"{delta // 3600}h ago"

# ─────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────
if "turns" not in st.session_state:
    st.session_state.turns = []

# ─────────────────────────────────────────────────────────────────────
# SIDEBAR — settings
# ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="ml-sidebar-heading">'
        '<span class="ml-sidebar-dot">●</span> SETTINGS'
        '</div>',
        unsafe_allow_html=True,
    )

    endpoint = st.text_input(
        "API ENDPOINT",
        value=config.get("API_URL", "http://localhost:1234/v1/chat/completions"),
    )
    model = st.text_input(
        "MODEL",
        value=detect_loaded_model(endpoint),
        help="Auto-detected from LM Studio. Edit to override.",
    )
    record_seconds = st.slider(
        "RECORD DURATION",
        min_value=3, max_value=15, value=5, step=1,
        help="How long to record after you tap the orb",
    )

    st.markdown(
        '<div class="ml-sidebar-heading" style="margin-top: 16px;">STATUS</div>',
        unsafe_allow_html=True,
    )

    available_voices = cached_available_voices()
    voice_count = sum(1 for v in VOICE_MAP.values() if v in available_voices)

    st.markdown(
        f'<div class="ml-status-list">'
        f'<div><span class="ml-good">●</span> Model loaded</div>'
        f'<div><span class="ml-good">●</span> {voice_count} voices ready</div>'
        f'<div><span class="ml-good">●</span> Mic ready</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="ml-sidebar-heading" style="margin-top: 20px;">HOW IT WORKS</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="ml-pipeline-list">'
        f'<div><span class="ml-pipeline-num">01</span><span class="ml-pipeline-action">Record voice</span><span class="ml-pipeline-tech">sounddevice</span></div>'
        f'<div><span class="ml-pipeline-num">02</span><span class="ml-pipeline-action">Transcribe</span><span class="ml-pipeline-tech">Whisper · local</span></div>'
        f'<div><span class="ml-pipeline-num">03</span><span class="ml-pipeline-action">Detect language</span><span class="ml-pipeline-tech">Lingua · offline</span></div>'
        f'<div><span class="ml-pipeline-num">04</span><span class="ml-pipeline-action">Generate reply</span><span class="ml-pipeline-tech">{html.escape(model)}</span></div>'
        f'<div><span class="ml-pipeline-num">05</span><span class="ml-pipeline-action">Speak back</span><span class="ml-pipeline-tech">macOS say · on-device</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Pinned sidebar wordmark
    st.markdown(
        '<div class="ml-sidebar-wordmark">'
        '  <div class="ml-sidebar-wordmark-name">'
        '    MULTI<span style="color: var(--ml-accent)">·</span>LINGUA'
        '  </div>'
        '  <div class="ml-nav-tagline">'
        '    Multilingual Conversational'
        '    <span class="ml-nav-tagline-ai">AI</span>'
        '  </div>'
        '</div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────
# NAV — brand + subtitle + version
# ─────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="ml-nav">
      <div class="ml-nav-brand">
        <span class="ml-nav-dot"></span>
        <div>
          <div>MULTI<span style="color: var(--ml-accent)">·</span>LINGUA</div>
          <div class="ml-nav-tagline">Multilingual Conversational <span class="ml-nav-tagline-ai">AI</span></div>
        </div>
      </div>
      <div style="display:flex; flex-direction:column; align-items:flex-end; gap:8px;">
        <a href="#" class="ml-how-it-works-link">
          <span class="ml-hiw-bracket">[</span>
          <span class="ml-how-it-works-dot">●</span>
          HOW IT WORKS
          <span class="ml-hiw-bracket">]</span>
        </a>
        <div class="ml-nav-version">v1.0 · LOCAL</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
# JS event delegation — attaches to parent doc from same-origin iframe;
# onclick on st.markdown elements is stripped by DOMPurify so we wire it here.
components.html(
    """
    <script>
      window.parent.document.addEventListener('click', function(e) {
        if (e.target.closest('.ml-how-it-works-link')) {
          e.preventDefault();
          var b = window.parent.document.querySelector('[data-testid="stSidebarCollapsedControl"] button')
               || window.parent.document.querySelector('[data-testid="stSidebarCollapseButton"] button');
          if (b) b.click();
        }
      });
    </script>
    """,
    height=0,
)

# ─────────────────────────────────────────────────────────────────────
# HERO — headline + orb
# ─────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="ml-hero">
      <div class="ml-eyebrow">Running on device. Privacy first.</div>
      <div class="ml-headline">Speak <em>any</em> language.</div>
      <div class="ml-headline ml-headline--muted">Hear it back, naturally.</div>

      <div class="ml-orb-wrap" style="margin-top: 28px;">
        <div class="ml-orb-glow"></div>
        <svg class="ml-orb-rings" width="168" height="168" viewBox="0 0 168 168">
          <circle cx="84" cy="84" r="82" fill="none" stroke="rgba(244,241,234,0.08)" stroke-width="0.5"/>
          <circle cx="84" cy="84" r="68" fill="none" stroke="rgba(244,241,234,0.08)" stroke-width="0.5"/>
          <circle cx="84" cy="84" r="54" fill="none" stroke="rgba(244,241,234,0.08)" stroke-width="0.5"/>
        </svg>
        <div class="ml-orb-core">
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none"
               stroke="#fff" stroke-width="1.6" stroke-linecap="round">
            <rect x="9" y="3" width="6" height="12" rx="3"/>
            <path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>
          </svg>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────
# SPEAK BUTTON
# ─────────────────────────────────────────────────────────────────────
_, col_btn, _ = st.columns([1, 2, 1])
with col_btn:
    speak = st.button(
        f"Tap to speak  |  {record_seconds} seconds",
        key="speak_btn",
    )
indicator = st.empty()

if speak:
    audio_path = record_audio(seconds=record_seconds, indicator=indicator)
    raw_text, confidence, whisper_lang = transcribe(audio_path)
    # Normalise Whisper's "zh" → "zh-cn" to match our VOICE_MAP key.
    if whisper_lang == "zh":
        whisper_lang = "zh-cn"
    # Use Whisper's audio-level language detection when available; it handles
    # romanised/transliterated speech (e.g. Hindi in Latin script) correctly.
    # Fall back to lingua only when Whisper returns nothing.
    lang = whisper_lang if whisper_lang and whisper_lang in VOICE_MAP else detect_language(raw_text)

    user_turn = {
        "who": "you",
        "lang_flag": LANG_FLAGS.get(lang, "🌐"),
        "lang_code": lang.upper()[:2],
        "voice": None,
        "text": html.escape(raw_text),
        "rtl": lang in RTL_LANGS,
        "confidence": confidence,
        "ts": time.time(),
    }

    with st.spinner("Thinking..."):
        t0 = time.time()
        reply, tokens = query_llm(raw_text, model, endpoint, lang)
        gen_ms = int((time.time() - t0) * 1000)

    t1 = time.time()
    speak_mac(reply, lang)
    tts_ms = int((time.time() - t1) * 1000)

    bot_turn = {
        "who": "bot",
        "lang_flag": LANG_FLAGS.get(lang, "🌐"),
        "lang_code": lang.upper()[:2],
        "voice": VOICE_MAP.get(lang, "Samantha").upper(),
        "text": html.escape(reply),
        "rtl": lang in RTL_LANGS,
        "gen_ms": gen_ms,
        "tts_ms": tts_ms,
        "tokens": tokens,
        "ts": time.time(),
    }

    st.session_state.turns.extend([user_turn, bot_turn])
    os.remove(audio_path)
    st.rerun()

# ─────────────────────────────────────────────────────────────────────
# TRANSCRIPT
# ─────────────────────────────────────────────────────────────────────
turns = st.session_state.turns
if turns:
    col_label, col_clear = st.columns([5, 1])
    with col_label:
        st.markdown(
            f'<div class="ml-section-label">— TRANSCRIPT · {len(turns)} TURNS</div>',
            unsafe_allow_html=True,
        )
    with col_clear:
        if st.button("↻ Clear", key="clear_btn", type="tertiary"):
            st.session_state.turns = []
            st.rerun()

    SHARP_COUNT = 2
    rendered = []
    for i, t in enumerate(reversed(turns)):
        faded = i >= SHARP_COUNT
        mine = t["who"] == "you"
        klass = "ml-turn"
        if mine:  klass += " ml-turn--mine"
        if faded: klass += " ml-turn--faded"

        who_label = "YOU" if mine else "MULTILINGUA"
        lang_bit = f"{t['lang_flag']} {t['lang_code']}"
        if mine and "confidence" in t:
            lang_bit += f" · {t['confidence']:.2f}"
        if not mine and t.get("voice"):
            lang_bit += f" · {t['voice']}"

        body_class = "ml-turn-body"
        if t.get("rtl"):
            body_class += " ml-turn-body--rtl"

        stats_html = ""
        if not mine and "gen_ms" in t:
            stats_html = (
                f'<div class="ml-turn-stats">'
                f'<span>{t["gen_ms"] / 1000:.1f}s · gen</span>'
                f'<span>{t["tts_ms"] / 1000:.1f}s · tts</span>'
                f'<span>{t["tokens"]} tok</span>'
                f'</div>'
            )

        ago = ago_label(t["ts"]) if "ts" in t else ""

        rendered.append(
            f'<div class="{klass}">'
            f'  <div class="ml-turn-meta">'
            f'    <div><span class="ml-turn-meta-who">{who_label}</span> · {lang_bit}</div>'
            f'    <span>{ago}</span>'
            f'  </div>'
            f'  <div class="{body_class}">{t["text"]}</div>'
            f'  {stats_html}'
            f'</div>'
        )
    st.markdown("".join(reversed(rendered)), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# LANGUAGE PILLS
# ─────────────────────────────────────────────────────────────────────
active_code = turns[-1]["lang_code"] if turns else None

st.markdown(
    '<div class="ml-section-label">— SUPPORTED · 13 LANGUAGES</div>',
    unsafe_allow_html=True,
)

pills_html = '<div class="ml-pills">' + "".join(
    '<div class="ml-pill'
    + (" ml-pill--active" if code == active_code else "")
    + ("" if VOICE_MAP.get(lang_key, "Samantha") in available_voices else " ml-pill--missing")
    + f'" title="{LANG_NAMES.get(lang_key, code)}'
    + ("" if VOICE_MAP.get(lang_key, "Samantha") in available_voices else " (voice not installed)")
    + f'"><span class="ml-pill-flag">{flag}</span>{code}</div>'
    for flag, code, lang_key in LANGUAGES
) + '</div>'
st.markdown(pills_html, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="ml-footer">
      <div class="ml-footer-left">
        <span><span class="ml-accent-dot">●</span> ON-DEVICE</span>
        <span>{html.escape(model.upper())}</span>
      </div>
      <span>{html.escape(endpoint.split("//", 1)[-1].split("/", 1)[0])}</span>
    </div>
    """,
    unsafe_allow_html=True,
)
