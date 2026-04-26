
import subprocess
import re
from lingua import Language, LanguageDetectorBuilder

# Voice map based on language codes
VOICE_MAP = {
    "en": "Samantha",
    "ar": "Majed",
    "fr": "Thomas",
    "es": "Jorge",
    "de": "Anna",
    "it": "Alice",
    "pt": "Luciana",
    "hi": "Lekha",
    "ru": "Milena",
    "zh-cn": "Tingting",
    "ja": "Kyoko",
    "ko": "Yuna",
    "tr": "Yelda",
}

# Build detector once — only for languages the app supports
_detector = LanguageDetectorBuilder.from_languages(
    Language.ENGLISH, Language.ARABIC, Language.FRENCH, Language.SPANISH,
    Language.GERMAN, Language.ITALIAN, Language.PORTUGUESE, Language.HINDI,
    Language.RUSSIAN, Language.CHINESE, Language.JAPANESE, Language.KOREAN,
    Language.TURKISH
).build()

def get_available_voices():
    result = subprocess.run(["say", "-v", "?"], stdout=subprocess.PIPE, text=True)
    voices = set()
    for line in result.stdout.splitlines():
        parts = line.strip().split()
        if parts:
            voices.add(parts[0])
    return voices

def detect_language(text):
    try:
        result = _detector.detect_language_of(text)
        if result is None:
            return "en"
        code = result.iso_code_639_1.name.lower()
        return "zh-cn" if code == "zh" else code
    except Exception:
        return "en"

def segment_text(text):
    # Split on punctuation followed by space
    return re.split(r'(?<=[.!?،؟])\s+', text.strip())

def clean_segment(text):
    """Strip markdown formatting and return None if nothing speakable remains."""
    # Remove markdown: **bold**, *italic*, # headings, numbered list prefixes like "1."
    text = re.sub(r'\*{1,2}([^*]*)\*{1,2}', r'\1', text)  # **bold** / *italic*
    text = re.sub(r'^#{1,6}\s*', '', text)                  # # headings
    text = re.sub(r'^\d+\.\s*$', '', text.strip())          # bare "1." "2." etc.
    text = text.strip()
    return text if text else None

def speak_mac(text, lang=None):
    available_voices = get_available_voices()
    segments = segment_text(text)

    for segment in segments:
        cleaned = clean_segment(segment)
        if not cleaned:
            continue  # skip bare numbers, empty markdown fragments
        seg_lang = lang if lang else detect_language(cleaned)
        voice = VOICE_MAP.get(seg_lang, "Samantha")
        if voice not in available_voices:
            voice = "Samantha"
        print(f"[{seg_lang}] {voice} says: {cleaned}")
        subprocess.run(["say", "-v", voice, cleaned])
