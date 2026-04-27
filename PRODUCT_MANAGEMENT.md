# Product Management Case Study — MultiLingua

*A full product lifecycle document covering discovery, validation, execution, and roadmap. Written for senior PM interviews.*

---

## The Problem

Language learning apps teach vocabulary and grammar. None of them let you have a real conversation.

I was learning Arabic and Spanish. I had Duolingo, which is structured, gamified, and pre-written. Useful for vocabulary, but useless for the thing that actually builds fluency: unscripted conversation. Real conversation needs a live partner, patience, and availability at 11pm when you feel like practising. Human tutors cost money and require scheduling. Language exchange partners require coordination and reciprocity.

There was no product that let me open a tool, speak in Arabic, and get a natural response back in Arabic, spoken aloud. So I built one.

---

## Discovery

This was personal pain, not a survey. I was the user, and the gap was obvious.

**What existed at the time:**
- Duolingo: pre-written content, no real conversation, gamified to the point of being disconnected from actual speaking
- iTalki and language tutors: human, expensive, requires scheduling
- Google Translate voice: translation only, no conversational loop, no memory of the exchange
- Smart speakers: English-first, single language, not built for practice

The gap was not "build a better Duolingo." Conversation was the missing primitive. Every tool built for language learning avoided the hardest and most valuable part.

This was roughly 18 months before ChatGPT Voice and Google's conversational AI features existed. The market had not yet validated the category, which made it riskier to build and more interesting in retrospect.

---

## Market Context at Time of Build

| Product | What it lacked |
|---|---|
| Duolingo | Pre-written content, no real conversation |
| iTalki | Human tutors, cost and scheduling barrier |
| Google Translate | Translation only, no conversational loop |
| Alexa / Siri | Single language, English-first architecture |
| Cloud STT/TTS APIs | Per-minute billing, unusable for long practice sessions |

The cost problem was structural. Cloud voice APIs all offer free tiers, but language practice is open-ended. At 90 minutes a day — a realistic practice session — AWS Transcribe alone costs roughly $65 a month at standard pricing. That is not a free tool. It is a subscription with an unpredictable bill. Building on those APIs would have made the product inaccessible to the exact person it was built for.

The product had to be free to run, indefinitely, at any usage volume. That constraint eliminated cloud APIs and forced the local-first architecture that became its core differentiator.

---

## Validation

**Does it work at all?**
Built a minimal version: microphone input, Whisper transcription, LLM response, macOS `say` command output. No UI, just command line. The goal was to prove the loop closes. It did.

**Is it actually useful for language practice?**
Used it personally for Arabic and Spanish over several weeks. The conversational loop worked. Being spoken to in your target language, even by a machine, activates listening comprehension in a way that reading a response on screen does not. The product was genuinely useful.

**Where does it break?**
Language detection was the hardest problem. Hindi and Arabic speakers whose speech was transcribed in non-native scripts were being detected as English. The product would respond in English and use the wrong voice — an immediately trust-breaking failure. A user who gets an English response after speaking Arabic does not try again.

The fix came from shifting language detection from text analysis to audio-level detection via Whisper, which identifies language from acoustic features before transcription happens. This was more reliable and solved the root cause rather than patching the symptom.

---

## API Architecture

The app uses two local API calls and one public CDN. No external API keys anywhere.

| Endpoint | Method | Purpose | Credentials |
|---|---|---|---|
| `{base}/v1/models` | GET | Auto-detect the model loaded in LM Studio or Ollama | None |
| `{base}/v1/chat/completions` | POST | Generate LLM reply in the detected language | None |
| Google Fonts CDN | GET | Load UI fonts (Inter, Instrument Serif, JetBrains Mono) | None |

Both LLM endpoints follow the OpenAI API spec, which means any compatible backend works — LM Studio, Ollama, or anything else that exposes the same interface. The model auto-detection call hits `/v1/models` on startup and picks up whatever is currently loaded, so users never need to manually configure a model name.

---

## Build vs Buy — Key Decisions

| Component | Options Evaluated | Decision | Reason |
|---|---|---|---|
| Speech-to-Text | AWS Transcribe, Google STT, Whisper local | Whisper local | Zero cost, no data leaving device, near-equivalent quality |
| Language Detection | Google Translate API, Lingua offline NLP, Whisper language field | Whisper plus Lingua fallback | Audio-level detection more reliable for multilingual speech |
| Language Model | OpenAI API, Anthropic API, local LLM | Local LLM via LM Studio or Ollama | Cost, privacy, offline capability |
| Text-to-Speech | AWS Polly, Google TTS, ElevenLabs, macOS `say` | macOS `say` | Free, on-device, native voices for 13+ languages, no API dependency |

The macOS `say` decision was the key unlock. Without a free, multi-language, on-device TTS option, the product could not exist without an ongoing API bill. macOS ships with high-quality native voices across 13+ languages. That made the whole product viable.

---

## Execution

As the sole builder, product and engineering were the same job.

**Scope management:** Started with English only to prove the loop, then added Arabic and Spanish first because that was the personal use case, then expanded from there.

**Technical pivots on language detection:**

Version 1 used text parsing and heuristics. Brittle, especially for non-Latin scripts.

Version 2 tried to extract the language code from the LLM response. Still brittle — the model was inconsistent and would occasionally ignore instructions.

Version 3 uses Whisper's audio-level language detection as the primary signal and Lingua as an offline fallback. Robust and auditable. This is the current architecture.

**UI rebuild:** The original version was functional but not portfolio-ready. The current version was rebuilt with a dark editorial design system to make the product showcaseable and the architecture visible to non-technical viewers through the in-app "HOW IT WORKS" panel.

**Cost of iteration:** Zero. Local-first architecture meant every experiment, pivot, and rebuild cost only time.

---

## Metrics Framework

If MultiLingua were a commercial product, success would be measured across three layers.

**Engagement**
- Daily active users
- Average session length (target above 15 minutes — below that the user is testing, not practising)
- Sessions per week per user (frequency signals habit formation)
- Language detection accuracy rate (target above 95%)

**Language outcomes**
- Languages used per user
- Session length by language (shorter sessions in a particular language may signal friction or voice quality issues)
- Return rate after first successful session

**Retention**
- Week 1 and Week 4 retention
- Churn trigger analysis — the most likely churn cause is language detection failure or wrong voice, both of which break immersion immediately

---

## Known Issues and Open Problems

| Problem | Impact | Status |
|---|---|---|
| Hindi/Urdu boundary | Whisper correctly distinguishes Hindi and Urdu, but the product only has a Hindi voice. Urdu speech falls through to the wrong routing. | Open |
| Arabic dialect variation | The LLM responds in Modern Standard Arabic, which may not match a user's spoken dialect | Open |
| No interruption | Cannot stop the AI mid-speech. User must wait for full TTS playback to finish. | On roadmap |
| Non-technical setup | Requires Python, a local LLM, and a command line. Not accessible to general users. | Mobile app on roadmap |

---

## Roadmap

**Near-term**
- Stop and interrupt button so the user can cut off TTS mid-speech, the way a real conversation works
- Expand language support to Turkish, Vietnamese, and Polish
- UI themes including light mode and a high-contrast accessibility option

**Medium-term**
- Conversation memory so the assistant retains context across sessions
- Progress tracking including session history, language detection accuracy over time, and vocabulary exposure
- User-selectable voices per language from the available macOS options

**Long-term**
- Mobile app for iOS and Android, removing the technical setup barrier and opening the product to mainstream language learners
- Cloud-optional mode for users who want higher quality responses and are comfortable with the data trade-off
- Community vocabulary packs for specific topics like travel, business, and medical conversation

---

## What I Would Do Differently

Validate with other users earlier. The product was built entirely on personal need, which produced a focused v1 but also meant some assumptions were never stress-tested. The macOS voice quality question and the command-line setup barrier are both things real users would have challenged quickly.

Prioritise the language detection failure mode sooner. The wrong-language response is the single most trust-breaking failure in the product. It was a known risk early on but was not treated as a P0 until it became an obvious problem.

Separate the learning product from the showcase product more consciously. The original version was built for personal use. The current version was rebuilt for a portfolio. In a commercial context these would be the same product — but the rebuild forced useful clarity on what the product actually is and who it is for.

---

## Summary

MultiLingua was built to solve a real personal problem before the market had validated the category. It shows discovery from lived experience rather than research decks, constraint-driven design where the cost constraint produced the privacy architecture, multiple technical pivots on the hardest problem in the product, and clear roadmap thinking grounded in real usage gaps.
