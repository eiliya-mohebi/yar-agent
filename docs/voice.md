# yar-agent — Voice gateway

Implementer contract for the **CLI voice gateway**: push-to-talk mic in → local STT →
the same agent loop as typed text → local TTS out. Decisions locked on the
[Voice processing spec](https://github.com/eiliya-mohebi/yar-agent/issues/17) map.
Reference shape: `waku/gateway/voice.py` in
[waku-agent](https://github.com/ShenSeanChen/waku-agent) (`main` @
[`871c4ac`](https://github.com/ShenSeanChen/waku-agent/tree/871c4ac)) — port selectively;
see [§11](#11-waku-delta-checklist).

This doc is the handoff. **Do not implement speculative hooks** for cut features.
When voice ships, update [ARCHITECTURE §13](ARCHITECTURE.md#13-deliberately-out-of-scope)
so CLI local voice is no longer listed as cut; wake word, SPA mic, and cloud audio stay cut.

**Persian and English are both required** for STT and TTS ([ARCHITECTURE §7](ARCHITECTURE.md#7-language-support-persian-and-english)).
Never match or filter speech-side text with ASCII character classes.

---

## 1. Purpose and seam

Voice is a **gateway** (Harness pillar), not a second agent. It only moves audio ↔ text.
After transcription, the path is identical to the text CLI: `Yar.respond(...)` → loop →
memory → tools → reply. Speaking is a presentation of the final reply string.

| Concern | Location (when built) |
|---------|------------------------|
| Voice gateway | `backend/yar/gateway/voice.py` |
| Entrypoint | `yar voice` (lazy-import); `make voice` |
| Config | `backend/yar/config.py` `Settings` + `YAR_*` (never scattered `os.getenv`) |
| Runtime cache | `.yar/voice/` (models + Piper voices) |
| Deterministic evals | `backend/evals/deterministic/` (pure helpers only) |

Continuity: same `.yar/` home and `state.db` as the text CLI. Use
`respond(..., source="voice")` and a distinct chat thread `session_id="voice"`
(parallel to CLI’s terminal session). Reuse `gateway/cli.py`’s `_observer` so gate/tool
lines print on the terminal.

---

## 2. Out of scope (this effort)

| Cut | Why |
|-----|-----|
| SPA / dashboard microphone (`POST /api/voice`, mic button) | Stays cut; see [frontend.md](frontend.md) |
| Wake word / always-listening | Push-to-talk only |
| Cloud STT/TTS APIs | Local-only |
| Windows-native voice | Linux + macOS required |
| Kokoro / torch TTS path; Piper-fa + Kokoro-en dual-stack | Heavier; Kokoro has no Persian |
| CI tests that download Whisper/Piper weights | Manual smoke only for live audio |

---

## 3. User flow

```text
uv sync --extra voice
yar voice          # or: make voice
```

1. Prompt: press **Enter** to start recording.
2. User speaks; press **Enter** again to stop (`record_until_enter`, `SAMPLE_RATE = 16000`).
3. Reject clips shorter than ~`SAMPLE_RATE // 4` with a clear message; do not call the agent.
4. **Ears** transcribe → show transcript on the terminal.
5. `yar.respond(transcript, observer=_observer, source="voice")` with `session_id="voice"`.
6. Take the **final assistant reply** only → `_speakable` → **Mouth** TTS.
7. Loop to step 1.

Observer/tool events stay on stdout. They are never spoken.

### Fail clearly

| Condition | Behavior |
|-----------|----------|
| `[voice]` deps missing | `SystemExit` with `uv sync --extra voice` |
| No mic / PortAudio device | Clear error; do not hang |
| Piper voices missing and no fallback | Clear error naming the missing voice/file |
| Fallback used (espeak / say) | Speak, and print which backend spoke |

### Platforms

- **Required:** Linux and macOS with a working mic and Piper fa+en voices (or a documented fallback).
- **WSL:** mic forwarding (PulseAudio / PipeWire) is environment-dependent and often brittle.
  Fail clearly when no input device is visible — do not ship a full WSL audio cookbook.
- **Windows native:** out of scope.

---

## 4. Speech-to-text (Ears)

| Item | Contract |
|------|----------|
| Engine | [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) (CTranslate2; MIT) |
| Default model | Multilingual **`small`** — never an `.en`-only checkpoint |
| Override | `YAR_WHISPER_MODEL` via `Settings` |
| Compute | CPU `int8` is the teaching default (Waku-shaped) |
| Language | See [§6](#6-language-selection) |

First-run weights download into **`.yar/voice/`** (or the library cache pointed there).
Print progress; on offline failure, error clearly. Approximate size: Whisper `small` CT2
weights ~**484 MB**.

Shape reference: Waku `Ears` in `waku/gateway/voice.py` — keep the class idea; wire model/lang
through `Settings`.

---

## 5. Text-to-speech (Mouth)

| Item | Contract |
|------|----------|
| Required engine | **Piper** (`piper-tts` / onnxruntime) — one runtime, two voices |
| Default fa voice | `fa_IR-amir-medium` (or equivalent id from [piper-voices](https://huggingface.co/rhasspy/piper-voices); confirm filenames at implement time) |
| Default en voice | `en_US-lessac-medium` |
| Overrides | `YAR_PIPER_VOICE_FA`, `YAR_PIPER_VOICE_EN` |
| Must-work | Linux + macOS with those voices present under `.yar/voice/` |

Approximate size: ~**63 MB** per medium Piper voice (ONNX + JSON).

### License

`piper-tts` is **GPL-3.0-or-later**. It is allowed **only** behind the optional `[voice]` extra —
never on the default non-voice install path. Document this in `pyproject.toml` / README when
shipping. Per-voice `MODEL_CARD` licenses still apply (e.g. amir medium CC0 dataset notes).

### Engine selection (`YAR_TTS_ENGINE`)

| Value | Behavior |
|-------|----------|
| `auto` (default) | Prefer Piper; else espeak-ng if on `PATH`; else macOS `say` on Darwin when fa **and** en system voices exist |
| `piper` | Piper only; fail if voices missing |
| `espeak` | Best-effort robotic fa+en (`espeak-ng` system binary) |
| `say` | Best-effort macOS only; must pick Farsi-capable and English voices — **do not** copy Waku’s English-only `_best_say_voice()` filter |

Fallbacks are **best-effort**. “Voice works” for the product bar means Piper fa+en on Linux and macOS.

### Not in v1 default path

Kokoro (no Persian), cloud TTS, MMS-TTS (CC-BY-NC), XTTS, torch-based neural extras.

---

## 6. Language selection

fa and en are first-class. No English-preferring defaults.

### STT (`YAR_VOICE_STT_LANG`)

| Value | Behavior |
|-------|----------|
| `auto` (default) | `language=None` → faster-whisper built-in language detection |
| `fa` / `en` | Pin Whisper language for the utterance |

**Mixed-script / code-switch:** Whisper is weak mid-utterance (upstream). Auto-detect picks a
dominant language. For reliable mixed turns, the user pins `fa` or `en`. Document that limit;
do not pretend parity of code-switch quality with monolingual turns.

### TTS routing (`YAR_VOICE_TTS_LANG`)

Default **`auto`** routes from the **speakable reply text** (not from STT language alone):

1. Count Arabic/Persian-script letters vs Latin letters in speakable text.
2. Persian-script majority, or any Persian-script if Latin count is zero → fa Piper voice.
3. Latin majority, or no Persian-script → en Piper voice.
4. Tie / both substantial → if pin is `fa`|`en`, use it; else last STT-detected or pinned
   language for the turn; else `en` as last resort. Prefer documenting “pin TTS lang” for
   mixed replies over silent wrong-voice surprises.

Pin: `YAR_VOICE_TTS_LANG` = `auto` | `fa` | `en`. espeak / `say` backends use the same fa|en choice.

Implement the router as a **pure function** (importable without `[voice]` deps) for evals.

---

## 7. Speakable and voicing rules

Voice **only** the final assistant reply string from `respond()`. Never speak:

- observer / tool traces
- system prompts
- history `[tools used: …]` lines

### `_speakable(text) -> str`

Pure function (keep importable without mic/TTS deps):

1. Strip emoji / pictographs (Waku `_EMOJI` range — copy from
   `waku/gateway/voice.py`, don’t reinvent ad hoc).
2. Strip markdown marker characters `` * _ ` # > ``.
3. **Remove fenced code blocks** (` ```…``` `) entirely.
4. Collapse runs of horizontal whitespace; strip lines; trim.
5. **Do not** transliterate Eastern digits, strip ZWNJ, or “normalize” Persian punctuation for TTS.
6. **Do not** ASCII-filter: ی / ک and mixed fa+en prose must survive.

If the result is empty: **skip TTS**, print a clear one-line terminal notice
(e.g. `nothing to speak`), continue the PTT loop. The turn still counts for text/memory.

**Length:** no cap — speak the full scrubbed reply.

Starting point: Waku `_speakable` + `evals/deterministic/test_speakable.py`, plus the code-fence
and Persian cases above.

---

## 8. Packaging

Optional uv extra on the backend package:

```toml
# conceptual — pin versions at implement time
voice = [
  "faster-whisper>=1.0",
  "sounddevice>=0.4",
  "piper-tts",  # GPL-3.0-or-later; onnxruntime transitive
]
```

- No torch on this path. No `[voice-neural]` in v1.
- `espeak-ng` is an optional **system** package for fallback, not a pip dep.
- Entrypoints: `yar voice`, `make voice`.
- Knobs in `backend/.env.example` under a Voice block; loaded only through `Settings`.

---

## 9. Configuration

All knobs are `YAR_*` on `Settings` (`backend/yar/config.py`).

| Knob | Meaning | Default |
|------|---------|---------|
| `YAR_WHISPER_MODEL` | faster-whisper model size/name | `small` |
| `YAR_VOICE_STT_LANG` | `auto` \| `fa` \| `en` | `auto` |
| `YAR_VOICE_TTS_LANG` | `auto` \| `fa` \| `en` | `auto` |
| `YAR_PIPER_VOICE_FA` | Piper fa voice id | `fa_IR-amir-medium` |
| `YAR_PIPER_VOICE_EN` | Piper en voice id | `en_US-lessac-medium` |
| `YAR_TTS_ENGINE` | `auto` \| `piper` \| `espeak` \| `say` | `auto` |

Cache directory: **`.yar/voice/`** (whisper weights + Piper ONNX/JSON).

---

## 10. Evals and smoke

### Deterministic (in `make gate` / default CI)

**No** audio-model downloads. Pure helpers only; **fa and en** cases required.

**Speakable** (`test_speakable.py` — adapt Waku, do not port `test_wake_word.py`):

- English: emoji + markdown strip cases from Waku.
- Drop fenced code blocks; surrounding prose may remain.
- Persian reply survives scrubbing (aside from intentional strips).
- Mixed fa+en survives (no ASCII filter).
- All-emoji / code-only → `""`.

**TTS language router:**

- Pure Persian → `fa`
- Pure English → `en`
- Mixed, Persian-script majority → `fa`
- Mixed, Latin majority → `en`
- Explicit pin overrides auto

Prefer keeping `_speakable` and the router in a module importable without `[voice]` installed
so default CI never needs the extra.

### Manual smoke (required by this spec; not CI)

On **Linux and macOS** (WSL best-effort):

1. `uv sync --extra voice` succeeds; `yar voice` starts.
2. PTT English → sensible transcript → reply spoken with en Piper voice.
3. PTT Persian → sensible transcript → reply spoken with fa Piper voice.
4. Observer/tool lines on terminal, not spoken.
5. Empty-speakable path: terminal notice, no hang.
6. Missing mic: clear error.
7. (Optional) Piper voices absent, espeak present: fallback speaks and prints backend name.

Default `make gate` / CI **must not** require `[voice]` or model files.

---

## 11. Waku delta checklist

Full inventory: [`.scratch/voice-processing/research/waku-voice-deltas.md`](../.scratch/voice-processing/research/waku-voice-deltas.md).
STT survey: [`local-stt-fa-en.md`](../.scratch/voice-processing/research/local-stt-fa-en.md).
TTS survey: [`local-tts-fa-en.md`](../.scratch/voice-processing/research/local-tts-fa-en.md).

```text
KEEP (shape / rename WAKU→YAR, .waku→.yar)
[ ] Gateway-only: record → STT → Yar.respond(source="voice") → TTS
[ ] session_id "voice"; reuse CLI _observer
[ ] PTT record_until_enter + short-audio guard + SAMPLE_RATE 16000
[ ] Optional [voice] extra + yar voice + make voice
[ ] Fail clearly if voice extra missing
[ ] Same .yar/ state.db continuity as text CLI

ADAPT (Yar deltas — do not copy Waku literals blindly)
[ ] Ears: faster-whisper default small; Settings knobs; fa+en
[ ] Mouth: Piper fa_IR + en_US on Linux+macOS; GPL extra note
[ ] _speakable: Waku strip + fenced code removal; fa/mixed eval cases
[ ] TTS/STT language: auto + pins; script-majority router
[ ] .env.example voice block without wake; WSL mic caveat
[ ] ARCHITECTURE §13/§14 at implementation time (CLI voice in; wake/SPA/cloud stay out)

DROP
[ ] wake_loop, matches_wake, record_command, wait_for_speech, _mic_threshold
[ ] All wake-related env defaults and test_wake_word.py
[ ] SPA mic + POST /api/voice
[ ] macOS say / British Kokoro as the sole TTS design
[ ] Cloud STT/TTS; Windows-native; CI audio-model tests in v1
```

---

## 12. Rebuild order (suggested)

1. Pure helpers: `_speakable` + TTS language router + deterministic evals (fa+en).
2. `Settings` / `.env.example` voice knobs; `.yar/voice/` cache paths.
3. `[voice]` extra in `backend/pyproject.toml`.
4. `Ears` (faster-whisper) + `record_until_enter`.
5. `Mouth` (Piper + auto/espeak/say dispatch).
6. `gateway/voice.py` main PTT loop wired to `Yar.respond`.
7. `yar voice` + `make voice`.
8. Manual smoke on Linux and macOS.
9. Update ARCHITECTURE §13 / §14 and any API `source` docs that still say only `cli`|`dashboard`.

Guiding bar: **clear, honest code a newcomer can follow — each pillar legible on its own.**
The voice gateway should stay a thin harness; complexity belongs in STT/TTS engines, not in a
second agent stack.
