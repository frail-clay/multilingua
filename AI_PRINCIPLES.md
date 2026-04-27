# AI Design Principles — MultiLingua

*A reference document for product and engineering interviews, covering the AI decisions made during the design and development of MultiLingua.*

---

## 1. Privacy by Default, Not by Policy

Voice is among the most personal data a product can collect. A user practising a language at home, speaking in their native script, discussing personal things — that data has no business on a third-party server. So from the start, the constraint was simple: nothing leaves the device. No telemetry, no external API calls, no data stored anywhere outside the user's own machine.

Privacy was not a feature added at the end. It was the founding constraint that shaped every technical choice that followed.

---

## 2. Local-First Over Cloud-Convenient

Cloud STT and TTS APIs were evaluated early on: AWS Transcribe, Google Speech-to-Text, Azure. All have free tiers, but voice is a high-consumption surface. At 90 minutes of daily practice, free tier limits disappear quickly. At AWS Transcribe pricing of roughly $0.024 per minute, 90 minutes a day adds up to about $65 a month. That is not a free tool — it is a subscription with unpredictable billing.

OpenAI Whisper, released as an open-weight model, solved this. It runs locally on a Mac, delivers near-equivalent transcription quality, and costs nothing regardless of how long you use it.

The lesson here is that cost modelling is an AI design input, not just a commercial consideration. For high-frequency interactions like voice, the right model is often the one users can actually keep running.

---

## 3. Graceful Degradation Over Hard Failure

Language detection uses two layers. Whisper detects language from raw audio before transcription happens — this is the primary signal and handles romanised or transliterated speech correctly. Lingua, an offline NLP library, acts as a fallback for edge cases where Whisper returns nothing.

Early versions used only text-based detection. This failed for Hindi and Arabic speakers whose speech was transcribed in non-native scripts. The detector saw Latin characters and returned English. Shifting to audio-level detection fixed the root cause. The fallback layer means the product does not break when it hits an unsupported edge case.

A single model as a hard dependency creates fragility. Layered signals create resilience.

---

## 4. Human Language as a First-Class Citizen

Multilingual products fail when they treat all languages as translations of an English-first experience. In MultiLingua, language detection, LLM prompting, and TTS voice selection are all language-aware from the first interaction. The LLM is instructed with a system prompt that names the detected language explicitly and tells it not to switch. Each language has a dedicated native macOS voice rather than a generic fallback.

There is a known limitation worth being honest about. Arabic and Hindi/Urdu sit on a dialect and script boundary. Whisper sometimes classifies Hindustani speech as Urdu, which is linguistically correct but breaks the current voice routing. The model is right; the product needs to catch up. That is a good example of where AI accuracy and product experience diverge and the product side needs to do the work.

---

## 5. The LLM as a Generation Layer, Not a Routing Layer

Early iterations tried to extract the detected language code from the LLM response. It was brittle. The model would reply in English regardless of instruction, or embed language codes inconsistently across responses. The architecture was refactored so that Whisper and Lingua own detection and the LLM only handles natural language generation.

LLMs are good at what to say and unreliable at what is true. Routing, classification, and structured signal extraction belong outside the LLM wherever possible.

---

## 6. Zero Credentials as a Design Constraint

The app makes exactly two API calls, both to localhost:

- `GET /v1/models` — detects which model is currently loaded in LM Studio or Ollama automatically on startup, removing the need to manually configure a model name
- `POST /v1/chat/completions` — sends the user's message and receives a reply in the detected language

Neither call requires an API key, an account, or any external network access. Google Fonts is the only outbound request and it carries no user data. The result is a product that anyone can run without signing up for anything, and that works fully offline once fonts are cached.

This was a deliberate constraint. Requiring credentials adds friction, creates a dependency on third-party services, and introduces a potential data exposure point. Removing all three was the goal.

---

## 7. Cost Transparency as a Trust Signal

MultiLingua shows the active model name and API endpoint in the UI footer and in the sidebar settings. Switching between LM Studio and Ollama is a one-field change. This transparency does two things: it respects the user's right to know what is running on their hardware, and it makes the product inspectable for technically literate users. Trust in an AI product comes partly from being able to see inside it.

---

## Summary

| Principle | Decision | Outcome |
|---|---|---|
| Privacy by default | All inference on-device | Zero data exposure |
| Local-first | Whisper over cloud STT | Zero marginal cost at any usage volume |
| Graceful degradation | Whisper plus Lingua fallback chain | Robust language detection across scripts |
| Language equality | Native voice per language, native-language LLM prompting | Natural multilingual experience |
| LLM as generation layer only | Whisper and Lingua own detection; LLM owns reply | Stable, auditable pipeline |
| Zero credentials | Localhost-only API calls, no keys required | Zero friction, zero exposure |
| Cost transparency | Live model and endpoint display in UI | User trust and inspectability |
