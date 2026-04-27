# MultiLingua — Multilingual AI Conversation Assistant

A real-time voice assistant that listens to you in **any language**, thinks with a **fully local LLM**, and **speaks the answer back in your language** — no cloud, no subscriptions, no data leaving your machine.

---

## How It Works

1. **You speak** — click *Tap to speak* and talk naturally
2. **Whisper transcribes** — OpenAI Whisper (running locally) converts your speech to text and identifies the language directly from the audio
3. **LLM replies** — your local LLM is instructed to respond in your language
4. **Voiced back** — macOS speaks the reply with the matching native voice (Arabic → Majed, French → Thomas, etc.)

Everything runs on your Mac. Nothing is sent to the internet.

---

## Supported Languages

| Language   | Voice     |
|------------|-----------|
| English    | Samantha  |
| Arabic     | Majed     |
| French     | Thomas    |
| Spanish    | Jorge     |
| German     | Anna      |
| Italian    | Alice     |
| Portuguese | Luciana   |
| Hindi      | Lekha     |
| Russian    | Milena    |
| Chinese    | Tingting  |
| Japanese   | Kyoko     |
| Korean     | Yuna      |
| Turkish    | Yelda     |

> Voices must be installed on your Mac: **System Settings → Accessibility → Spoken Content → System Voice → Manage Voices**

---

## Requirements

- **macOS** (TTS uses the built-in `say` command)
- **Python 3.9+**
- A working **microphone**
- A local LLM backend — choose one:
  - **[LM Studio](https://lmstudio.ai/)** — recommended for beginners
  - **[Ollama](https://ollama.com/)** — recommended for developers

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/multilingua.git
cd multilingua
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> Whisper will download the `base` model (~140 MB) automatically on first run.

### 4. Set up your local LLM (choose one)

---

#### Option A — LM Studio (recommended for beginners)

1. Download and install [LM Studio](https://lmstudio.ai/)
2. Search for and download a model — recommended: `meta-llama-3.1-8b-instruct`
3. Go to the **Local Server** tab and click **Start Server**
4. The server runs at `http://localhost:1234` by default
5. In `config.json`, set:

```json
{
    "MODEL_NAME": "meta-llama-3.1-8b-instruct",
    "API_URL": "http://localhost:1234/v1/chat/completions"
}
```

---

#### Option B — Ollama (recommended for developers)

1. Install Ollama: [https://ollama.com/download](https://ollama.com/download)
2. Pull a model:

```bash
ollama pull llama3.1
```

3. Verify it's running:

```bash
ollama list
```

4. In `config.json`, update to:

```json
{
    "MODEL_NAME": "llama3.1",
    "API_URL": "http://localhost:11434/v1/chat/completions"
}
```

---

### 5. Install macOS voices

Open **System Settings → Accessibility → Spoken Content → System Voice → Manage Voices**

Install the voices for the languages you want to use. Language pills in the app turn amber when a voice is active and dimmed when its voice is not yet installed.

### 6. Launch the app

Double-click **`launch.command`** in the project folder, or run:

```bash
./run.sh
```

The app opens in your browser at `http://localhost:8501`

---

## Using the App

| UI element | What it does |
|---|---|
| **Tap to speak** button | Starts recording for the duration set in the sidebar |
| **[ ● HOW IT WORKS ]** | Opens the sidebar showing the inference pipeline |
| **Sidebar → Settings** | Adjust model name, API endpoint, and recording duration |
| **Sidebar → How it works** | Step-by-step inference pipeline with live model name |
| **Transcript** | Shows the full conversation; the two most recent turns are highlighted, older ones fade |
| **↻ Clear** | Wipes the transcript and starts a fresh session |
| **Language pills** | Shows all 13 supported languages; the active language glows amber; dimmed pills mean the macOS voice is not yet installed |
| **Footer** | Confirms the active model and API endpoint |

---

## Project Structure

```
main.py                  # Streamlit app — UI and voice pipeline logic
style.css                # Dark editorial styling (CSS tokens, component styles)
speak_multilang_mac.py   # Language detection + macOS TTS (speak_mac, detect_language)
config.json              # Default API URL and model name — edit to switch LLM backends
requirements.txt         # Python dependencies
run.sh                   # Terminal launch script
launch.command           # Double-click launcher for macOS
.streamlit/config.toml   # Streamlit theme configuration
```

---

## Configuration

Edit `config.json` to set defaults — model name and endpoint can also be changed live in the sidebar without restarting:

| Setting | LM Studio | Ollama |
|---|---|---|
| `API_URL` | `http://localhost:1234/v1/chat/completions` | `http://localhost:11434/v1/chat/completions` |
| `MODEL_NAME` | e.g. `meta-llama-3.1-8b-instruct` | e.g. `llama3.1` |

All visual tokens (colors, fonts, spacing) live at the top of `style.css` under `:root {}`. Change `--ml-accent` to retheme the whole app.

> **Note:** The app auto-detects whichever model you have loaded in LM Studio by calling `GET /v1/models` on startup. You no longer need to manually update `MODEL_NAME` in `config.json` — just load a model in LM Studio and the app picks it up automatically.

---

## API Reference

The app makes two calls to your local LLM backend. No external APIs, no API keys required.

| Endpoint | Method | Purpose |
|---|---|---|
| `/v1/models` | GET | Auto-detect the model currently loaded in LM Studio or Ollama |
| `/v1/chat/completions` | POST | Generate a reply in the detected language |

Both endpoints follow the OpenAI API spec and work with any compatible backend.

---

## Tech Stack

| Component | Technology |
|---|---|
| UI | Streamlit |
| Speech-to-Text | OpenAI Whisper (local, `base` model) |
| Language Detection | Whisper audio-level detection + Lingua (offline fallback) |
| Language Model | LM Studio or Ollama (local, OpenAI-compatible API) |
| Text-to-Speech | macOS `say` command |
| Audio Recording | sounddevice + scipy |
| Fonts | Google Fonts CDN (Inter, Instrument Serif, JetBrains Mono) |

---

## Privacy

Every component runs locally on your machine:

- Whisper transcribes your speech locally
- Language detection runs offline (no API calls)
- LLM inference runs on your hardware via LM Studio or Ollama
- TTS uses macOS built-in voices
- No API keys, no accounts, no usage tracking

**Your voice and conversations never leave your device.**
