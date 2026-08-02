# Research: Waku voice gateway → Yar deltas

**Ticket:** [#20](https://github.com/eiliya-mohebi/yar-agent/issues/20) (map: [#17](https://github.com/eiliya-mohebi/yar-agent/issues/17))  
**Question:** What should `docs/voice.md` inherit from Waku’s voice path versus name as an explicit Yar delta?  
**Sources (primary):**

| Source | Path |
|--------|------|
| Waku voice gateway | `/home/eiliya/ml_projects/waku-agent/waku/gateway/voice.py` |
| Waku extras | `/home/eiliya/ml_projects/waku-agent/pyproject.toml` (`voice`, `voice-neural`) |
| Waku env catalog | `/home/eiliya/ml_projects/waku-agent/.env.example` (Voice gateway block) |
| Waku CLI entry | `/home/eiliya/ml_projects/waku-agent/waku/__main__.py` (`waku voice`) |
| Waku Makefile | `/home/eiliya/ml_projects/waku-agent/Makefile` (`voice` target) |
| Waku speakable eval | `/home/eiliya/ml_projects/waku-agent/evals/deterministic/test_speakable.py` |
| Waku wake-word eval | `/home/eiliya/ml_projects/waku-agent/evals/deterministic/test_wake_word.py` |
| Waku SPA mic | `/home/eiliya/ml_projects/waku-agent/waku/ops/static/js/main.js` (`toggleMic` / `/api/voice`) |
| Waku dashboard STT | `/home/eiliya/ml_projects/waku-agent/waku/ops/dashboard.py` (`transcribe_audio`, `/api/voice`) |
| Yar §13 voice cut | `docs/ARCHITECTURE.md` §13 + §14 “no Yar counterpart” |
| Yar frontend mic cut | `docs/frontend.md` (“Do not port … mic / voice transcription path”) |
| Yar CLI harness | `backend/yar/gateway/cli.py` (only gateway today; notes voice out of scope) |
| Yar extras today | `backend/pyproject.toml` (no `[voice]` yet) |

**Yar locks (from #17 charting — do not reopen here):** push-to-talk only · local-only STT/TTS · fa+en parity · Linux+macOS · same `.yar/` continuity · no SPA mic · no wake word.

**Verdict in one line:** Inherit the *gateway shape* (PTT record → local STT → same `respond()` → speakable strip → local TTS) and the `[voice]` / optional neural packaging idea; drop the entire wake-word stack and SPA mic path; name TTS/STT language, Linux default, Settings-not-`os.getenv`, and Persian speakable rules as explicit deltas.

---

## 1. How Waku’s voice path is shaped

`waku/gateway/voice.py` is a second harness next to CLI: it only moves audio↔text; the loop/memory/eval path is `Waku.respond(..., source="voice")` with the same `_observer` as CLI.

Two interaction modes live in one file:

1. **Push-to-talk** (`record_until_enter` + Enter/Enter) — the MVP described in the module docstring.
2. **Wake-word always-listening** (`wake_loop`) — **default at runtime** via a non-empty `WAKU_WAKE_WORD` default string. Set `WAKU_WAKE_WORD=""` for PTT.

Doc drift to name in the Yar spec (do not copy blindly):

- Module docstring still calls wake-word “deliberately v2” / openWakeWord roadmap, but `main()` enables wake by default.
- `.env.example` says “Unset = push-to-talk”, but code supplies a long default wake string when the env var is absent — so “unset” in the process environment is *not* PTT.

Ears = `faster-whisper` (`WhisperModel`, `compute_type="int8"`, model from `WAKU_WHISPER_MODEL` default `base`; optional `WAKU_WHISPER_LANG`).  
Mouth = macOS `say` (auto-picks English Premium/Enhanced voices) or Kokoro (`lang_code="b"` British English, default `bm_george`) if importable / `WAKU_TTS=kokoro`. Non-darwin without Kokoro prints “(no TTS engine…)”.

SPA path is separate: browser PCM WAV → `POST /api/voice` → same Whisper in `dashboard.py` (`transcribe_audio`); mic UI in `ops/static/js/main.js` + `#mic` in `index.html`.

---

## 2. Pasteable delta checklist for `docs/voice.md`

Legend: **keep** = inherit shape/literals with rename only · **adapt** = keep idea, rewrite for Yar locks · **drop** = out of this effort / conflicts with locks.

### 2.1 Gateway module (`waku/gateway/voice.py` → future `backend/yar/gateway/voice.py`)

| Piece | Waku location | Decision | Notes for Yar |
|-------|---------------|----------|---------------|
| Gateway-only contract (audio in → text → `respond` → text out → speak) | module docstring + `main` loop | **keep** | Same pillar story as CLI; cite ARCHITECTURE harness box. |
| Reuse CLI `_observer` for gate/tool lines | import from `gateway/cli.py` | **keep** | Yar already has `_observer` in `backend/yar/gateway/cli.py`. |
| `session_id = "voice"` distinct thread | `main()` | **keep** | Continuity: same `.yar/` / `state.db`; separate inbox thread like CLI’s `"terminal"`. |
| `source="voice"` on `respond` | `main` / `wake_loop` | **keep** | Yar `app.respond` already accepts `source`; dashboard uses `"dashboard"`. |
| `SAMPLE_RATE = 16000` | module constant | **keep** | Matches Whisper expectation. |
| `record_until_enter()` PTT capture | `voice.py` | **keep** | This is the locked interaction mode. Document Enter/Enter UX + short-clip guard (`< SAMPLE_RATE//4`). |
| PTT `main` loop (no wake) | bottom of `main()` | **keep** | Make this the *only* path; do not default to wake. |
| Fail clearly if `[voice]` missing | `import sounddevice` → `SystemExit` | **keep** | Message → `uv sync --extra voice` / Yar wording. |
| `Ears` class (`faster-whisper`) | `Ears` | **adapt** | Shape keep; engine/model/lang locked by #18/#22/#23. Must support fa+en (and mixed-script turns). No ASCII-only assumptions. Wire knobs through `Settings`, not `os.getenv`. |
| `Mouth` class (TTS dispatch) | `Mouth` | **adapt** | Shape keep (engine + voice + `speak`); engines must meet **Linux+macOS** and **fa+en**. Waku’s default macOS-`say` + British Kokoro is English/mac-centric — name as delta, do not ship as sole Linux path. |
| `_speakable` + `_EMOJI` strip | helpers | **adapt** | Keep “strip emoji/markdown before TTS” idea + English cases from `test_speakable.py`; extend for Persian punctuation / tool-heavy replies (#21). Project rule: no emojis in UI — still strip if model emits them. |
| `_best_say_voice()` English-only picker | helper | **adapt or drop** | macOS-only helper may remain as *optional* macOS backend after #19/#22; must not be the Linux default; English-locale filter (`en_`) is a fa+en delta if `say` stays. |
| `matches_wake` | pure fn | **drop** | Wake word out. Also ASCII/CJK/kana norm omits Arabic/Persian letters — would violate §7 if revived later. |
| `wake_loop` | always-listening | **drop** | Includes scout `Ears("tiny")`, ack TTS, follow-up window, stream drain, `wake_scan` tracer events. |
| `record_command` / `wait_for_speech` / `_mic_threshold` | wake helpers | **drop** | Only used by wake path. (If later VAD for PTT end-of-utterance is desired, that’s a new decision — not this inventory.) |
| Default non-empty `WAKU_WAKE_WORD` | `main()` | **drop** | Yar: PTT only; no wake env default. |
| `WAKU_WAKE_ACK`, `WAKU_FOLLOWUP_SECONDS`, `WAKU_WAKE_LANG`, `WAKU_MIC_THRESHOLD` | env usage in wake path | **drop** | |
| openWakeWord / “v2 wake” roadmap comments | module docstring | **drop** | Spec should not promise wake. |
| Docstring claiming wake is v2 while code defaults wake on | docstring vs `main` | **drop / do not copy** | Spec states PTT-only unambiguously. |

### 2.2 Packaging & entrypoints

| Piece | Waku location | Decision | Notes for Yar |
|-------|---------------|----------|---------------|
| Optional `[voice]` extra: `faster-whisper`, `sounddevice` | `pyproject.toml` | **keep** (rename/placement) | Yar: `backend/pyproject.toml` extras; install via `uv`. Exact pins deferred to #22/#24. |
| Optional `[voice-neural]`: `kokoro`, `soundfile` | `pyproject.toml` | **adapt** | Pattern (heavy TTS behind second extra) keep; Kokoro-as-chosen-engine is **not** locked — #19/#22 may pick dual-engine / different package. Name “split extras” as open until #24. |
| `waku voice` subcommand | `waku/__main__.py` | **keep** | Add `yar voice` beside dashboard/brief; lazy-import gateway. |
| `make voice` | Waku `Makefile` | **keep** | Mirror under `backend/Makefile` when implementing. |
| `.env.example` voice block | Waku `.env.example` | **adapt** | Rename `WAKU_*` → `YAR_*`; omit wake knobs; document Linux+macOS + fa+en; load only via `yar/config.py` `Settings` (Yar rule — no scattered `os.getenv`). |
| `WAKU_WHISPER_MODEL` / `WAKU_WHISPER_LANG` | code (+ model in `.env.example`; lang **missing** from example) | **adapt** | Keep knobs in spirit; exact names/behavior → #23/#24. Document lang (Waku forgot it in `.env.example`). |
| `WAKU_TTS` / `WAKU_VOICE` | code + `.env.example` | **adapt** | Same; engine set depends on #22. |
| Auto-detect Kokoro if importable | `Mouth.__init__` | **adapt** | Nice UX; only if Kokoro (or chosen neural) remains a supported engine. |

### 2.3 Deterministic evals

| Piece | Waku location | Decision | Notes for Yar |
|-------|---------------|----------|---------------|
| `test_speakable.py` (emoji/markdown strip cases) | `evals/deterministic/test_speakable.py` | **adapt** | Port English cases; **add Persian / mixed-script cases** (#21/#25). Live under `backend/evals/deterministic/`. |
| `test_wake_word.py` | `evals/deterministic/test_wake_word.py` | **drop** | Entire file. ARCHITECTURE §14 currently lists it among “do not port” cut evals — remains dropped even when voice returns. |
| Audio-model / Whisper integration tests in CI | (none required in Waku gate for live mic) | **drop for v1** | Matches #17: deterministic pure-function tests + manual smoke; no required CI audio-model tests. |

### 2.4 SPA / dashboard mic (explicit non-goals)

| Piece | Waku location | Decision | Notes for Yar |
|-------|---------------|----------|---------------|
| `#mic` button + `getUserMedia` / WAV encode | `waku/ops/static/js/main.js`, `index.html` | **drop** | `docs/frontend.md` already: do not port mic path. |
| `POST /api/voice` + `transcribe_audio` | `waku/ops/dashboard.py` | **drop** | No Yar `docs/api.md` voice route; do not add for this effort. |
| Dashboard `wake_scans` trace UI | `dashboard.py` thread summary | **drop** | Wake-only telemetry. |
| Architecture SVG “cli · voice · web” label | `diagram.js` | **adapt later** | When voice ships, CLI gateway story may mention voice; SPA mic stays cut. Not part of #20 implement. |

### 2.5 Continuity & platform

| Piece | Decision | Notes |
|-------|----------|-------|
| Same home / DB / memory as text CLI | **keep** | `.yar/` (not `.waku/`); voice is another gateway into one brain. |
| Linux + macOS required | **adapt** | Waku Mouth effectively macOS-first; Linux needs a real TTS default (#19/#22). Document WSL mic caveats (Pulse/PipeWire) as fail-clearly guidance (#17 open item). |
| Windows native | **drop** | Out of scope per #17. |
| Cloud STT/TTS | **drop** | Local-only lock. |

### 2.6 Docs / ARCHITECTURE posture

| Piece | Decision | Notes |
|-------|----------|-------|
| §13 lists Voice gateway as cut | **adapt at implementation** | #17: do not rewrite §13 while only writing the spec; when voice is built, narrow the cut (SPA mic / wake / cloud remain cut; CLI local voice moves in-scope). |
| §14 “Do not port `gateway/voice.py`” + speakable/wake evals | **adapt via selective re-port** | This research defines the selective map: re-port PTT+Ears+Mouth+_speakable+extras; never wake/SPA. |
| New `docs/voice.md` + `docs/README.md` reading-order entry | **keep** (destination of #17) | Packaging decision already locked. |

---

## 3. Compact checklist (copy into spec)

```text
KEEP (shape / rename WAKU→YAR, .waku→.yar)
[ ] Gateway-only: record → STT → Yar.respond(source="voice") → TTS
[ ] session_id "voice"; reuse CLI _observer
[ ] PTT record_until_enter + short-audio guard + SAMPLE_RATE 16000
[ ] Optional [voice] extra: faster-whisper + sounddevice
[ ] yar voice + make voice entrypoints
[ ] Fail clearly if voice extra missing
[ ] Same .yar/ state.db continuity as text CLI

ADAPT (explicit Yar deltas — do not copy Waku literals blindly)
[ ] Ears/STT: fa+en (+ mixed); Settings knobs (not os.getenv); model/lang from #18/#22/#23
[ ] Mouth/TTS: Linux+macOS capable; fa+en (likely dual-engine); macOS say / British Kokoro not sole design
[ ] _speakable + test_speakable: keep EN strip cases; add fa / punctuation / tool-reply rules (#21/#25)
[ ] Extras split ([voice] vs neural/TTS): follow #19/#22/#24 — Kokoro optional pattern only
[ ] .env.example voice block without wake; document WSL mic caveats
[ ] ARCHITECTURE §13/§14 updated at implementation time (CLI voice in; wake/SPA/cloud stay out)

DROP (conflicts with locks)
[ ] wake_loop, matches_wake, record_command, wait_for_speech, _mic_threshold
[ ] Default / any WAKU_WAKE_WORD, WAKE_ACK, FOLLOWUP_SECONDS, WAKE_LANG, MIC_THRESHOLD
[ ] test_wake_word.py
[ ] SPA mic (main.js / #mic) and POST /api/voice / transcribe_audio
[ ] Cloud STT/TTS; Windows-native; openWakeWord roadmap
[ ] CI live audio-model tests in v1
```

---

## 4. Env var map (Waku → Yar intent)

| Waku | Role | Yar |
|------|------|-----|
| `WAKU_WHISPER_MODEL` | STT model size | **adapt** → `YAR_*` via Settings (#24) |
| `WAKU_WHISPER_LANG` | STT language hint (code only; undocumented in `.env.example`) | **adapt** (#23/#24) |
| `WAKU_TTS` | TTS engine select | **adapt** (#22/#24) |
| `WAKU_VOICE` | Voice id within engine | **adapt** (#22/#24) |
| `WAKU_WAKE_WORD` | Wake enable + variants | **drop** |
| `WAKU_WAKE_ACK` | Spoken ack | **drop** |
| `WAKU_FOLLOWUP_SECONDS` | Post-wake open mic | **drop** |
| `WAKU_WAKE_LANG` | Scout STT lang | **drop** |
| `WAKU_MIC_THRESHOLD` | Wake VAD threshold | **drop** |

---

## 5. What this ticket does *not* decide

Still owned by sibling tickets on #17: exact STT/TTS engines (#18/#19/#22), language selection behavior (#23), speakable-text rules beyond emoji/markdown (#21), concrete `YAR_*` / extras UX (#24), eval case list + smoke checklist (#25), decision-complete gate (#26).

---

## 6. Source citations (anchors)

- PTT vs wake default: `waku/gateway/voice.py` `main()` (`WAKU_WAKE_WORD` default string vs `WAKU_WAKE_WORD=""` → PTT).
- Ears/Mouth/`_speakable`: same file, classes/helpers named above.
- Extras: `waku-agent/pyproject.toml` `[project.optional-dependencies]` `voice` / `voice-neural`.
- Evals: `waku-agent/evals/deterministic/test_speakable.py`, `test_wake_word.py`.
- SPA mic: `waku/ops/static/js/main.js` (~L112–175), `waku/ops/dashboard.py` `transcribe_audio` + `/api/voice` dispatch.
- Yar cuts: `docs/ARCHITECTURE.md` §13 Voice row; §14 do-not-port list; `docs/frontend.md` Do not port mic path; `backend/yar/gateway/cli.py` module docstring.
