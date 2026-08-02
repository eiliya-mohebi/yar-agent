# Research: Local TTS options for fa+en on Linux/macOS

**Ticket:** [#19](https://github.com/eiliya-mohebi/yar-agent/issues/19) (map: [#17](https://github.com/eiliya-mohebi/yar-agent/issues/17); engine choice: [#22](https://github.com/eiliya-mohebi/yar-agent/issues/22))  
**Question:** Which local text-to-speech engines can meet full Persian + English parity on Linux and macOS without cloud APIs? Recommend a shortlist for #22 — do **not** pick the winner.  
**Yar locks (from #17):** CLI push-to-talk · local-only · full fa+en · Linux+macOS · same `.yar/` continuity · no wake word · no SPA mic · no cloud audio.

**Waku baseline (not acceptable as Yar default as-is):** `waku/gateway/voice.py` uses macOS `say` with an English-locale voice picker, or Kokoro with British `lang_code="b"` / `bm_george`. Non-darwin without Kokoro has no TTS path.

**Verdict in one line:** Only **Piper** (with separate fa_IR + en_* voices) is a surveyed single-engine neural path with first-class offline fa+en on both Linux and macOS; Kokoro has **no** Persian; dual-engine (Piper-fa + Kokoro-en) and **espeak-ng** (robotic fallback) belong on the shortlist — MMS has fas+eng but is CC-BY-NC.

---

## Sources (primary)

| Source | URL / path |
|--------|------------|
| Waku voice gateway | `/home/eiliya/ml_projects/waku-agent/waku/gateway/voice.py` |
| Kokoro-82M model card | https://huggingface.co/hexgrad/Kokoro-82M |
| Kokoro VOICES.md | https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md |
| Kokoro PyPI (`kokoro`) | https://pypi.org/project/kokoro/ |
| kokoro-onnx README | https://github.com/thewh1teagle/kokoro-onnx |
| Piper (current) README | https://github.com/OHF-Voice/piper1-gpl |
| Piper VOICES.md | https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md |
| Piper samples / quality tiers | https://rhasspy.github.io/piper-samples/ |
| Piper PyPI (`piper-tts`) | https://pypi.org/project/piper-tts/ |
| Piper voice MODEL_CARD (fa amir) | https://huggingface.co/rhasspy/piper-voices/raw/main/fa/fa_IR/amir/medium/MODEL_CARD |
| Piper voice MODEL_CARD (en lessac) | https://huggingface.co/rhasspy/piper-voices/raw/main/en/en_US/lessac/medium/MODEL_CARD |
| Legacy Piper LICENSE (MIT) | https://github.com/rhasspy/piper/blob/master/LICENSE.md |
| MMS fairseq README (license) | https://github.com/facebookresearch/fairseq/blob/main/examples/mms/README.md |
| MMS-TTS Persian card | https://huggingface.co/facebook/mms-tts-fas |
| MMS language list (`fas`, `eng`) | https://dl.fbaipublicfiles.com/mms/tts/all-tts-languages.html |
| Transformers MMS docs | https://huggingface.co/docs/transformers/main/en/model_doc/mms |
| Coqui XTTS-v2 card | https://huggingface.co/coqui/XTTS-v2 |
| idiap Coqui fork | https://github.com/idiap/coqui-ai-TTS |
| espeak-ng languages | https://github.com/espeak-ng/espeak-ng/blob/master/docs/languages.md |
| espeak-ng COPYING | https://github.com/espeak-ng/espeak-ng/blob/master/COPYING |
| Apple macOS feature availability (Farsi Spoken Content) | https://www.apple.com/uk/macos/feature-availability/ |
| sherpa-onnx Piper-fa samples | https://k2-fsa.github.io/sherpa/onnx/tts/all/Persian/ |
| sherpa-onnx LICENSE | https://github.com/k2-fsa/sherpa-onnx/blob/master/LICENSE |
| ManaTTS Persian model README | https://github.com/MahtaFetrat/ManaTTS-Persian-Tacotron2-Model |

---

## Comparison matrix

| Engine | License (engine / weights) | Install size (order of magnitude) | Torch / native deps | Offline | fa | en | Voice selection | Latency / quality (from sources) | Linux | macOS | Meets fa+en alone? |
|--------|----------------------------|-----------------------------------|---------------------|---------|----|----|-----------------|----------------------------------|-------|-------|--------------------|
| **Piper** (`piper-tts` / OHF) | Engine: **GPL-3.0-or-later** (PyPI + `COPYING`); legacy rhasspy tree was **MIT**. Voices: per-`MODEL_CARD` (e.g. fa `amir` **CC0**; en `lessac` Blizzard license URL) | Runtime: `onnxruntime` wheel. Voice ONNX ~**63 MB**/medium voice (HF lists `en_US-lessac-medium.onnx` 63.2 MB; sherpa fa packs ~64 MB `.tar.bz2`) | **No torch** for inference; embeds/uses **espeak-ng** for phonemes | Yes (after voice download) | Yes — `fa_IR` voices: amir, ganji, ganji_adabi, gyro, reza_ibrahim | Yes — `en_US`, `en_GB` (+ many others) | One ONNX + JSON per voice; switch by loading another voice | Samples site: medium = 22.05 kHz, 15–20M params; marketed as fast/local (Home Assistant etc.) | Yes | Yes | **Yes** (dual voices, one runtime) |
| **Kokoro-82M** | Weights **Apache-2.0**; `kokoro` Apache; `kokoro-onnx` MIT + Apache model | Torch path: hub weights + torch stack. ONNX path: ~**325 MB** `kokoro-v1.0.onnx` + ~**28 MB** `voices-v1.0.bin` | **`torch`** (+ transformers/misaki) *or* ONNX Runtime (no torch) | Yes after download | **No** — not in VOICES.md language list | Yes — many `a*` / `b*` voices | Named voices (`af_heart`, `bm_george`, …); `lang_code` must match | Model card: 82M params, “comparable quality to larger models”, faster/cheaper; VOICES.md grades vary; short/long utterance caveats | Yes | Yes | **No** (en only among Yar langs) |
| **MMS-TTS** (Meta) | Code + weights **CC-BY-NC 4.0** | Separate VITS checkpoint per language; torch + transformers; generators via fairseq tarballs or HF `facebook/mms-tts-{fas,eng}` | **Torch** (+ Transformers; fairseq/VITS path also documented) | Yes after download | Yes — `fas` / `mms-tts-fas` | Yes — `eng` / `mms-tts-eng` | One speaker per language checkpoint; rate/noise knobs in Transformers | VITS neural quality; non-deterministic (seed); trained on religious-text readings (paper) — prosody domain caveat | Yes | Yes | **Technically yes**, but **NC license** |
| **Coqui XTTS-v2** | Code MPL-2.0 (idiap fork); weights **CPML** (non-commercial) | Large torch TTS stack + multi‑GB-class model downloads (toolkit-scale) | **Torch** (heavy) | Yes after download | **No** — official list has 17 langs incl. Arabic, **not** Persian | Yes | Speaker refs / cloning | High quality cloning where supported; company shut down; community fork maintains code | Yes | Yes | **No** |
| **espeak-ng** | **GPL-3.0+** (`COPYING`) | Distro package; megabytes | Native C binary; no torch | Yes | Yes — `fa` / `fa-latn` | Yes — `en`, `en-us`, … | Voice files + variants (`-v fa`, `-v en`) | Formant / robotic; 127 langs claimed in docs — usable accessibility baseline, not neural quality | Yes | Yes (brew/port) | **Yes** (quality weak) |
| **macOS `say`** | Proprietary Apple | System; optional voice downloads | System framework | Yes (voices local once installed) | Apple lists **Farsi** under VoiceOver / Live Speech / Spoken Content | Many English voices | `say -v '?'`; Waku filters `en_` only today | Enhanced/Premium voices near-Siri when downloaded | **No** | Yes | **macOS-only**; Linux gap |
| **sherpa-onnx** (runtime) | **Apache-2.0** | Wraps Piper ONNX packs (~64 MB/voice tarballs observed for fa) | Native ONNX; no torch | Yes | Yes (converted Piper fa voices) | Yes (converted Piper en voices) | Same Piper voice files | Same as underlying Piper model | Yes | Yes | **Yes** as alternate Piper host (not a new voice set) |
| **ManaTTS Tacotron2** | Model **CC0-1.0**; impl MIT-derived | Research checkpoint + torch TTS stack | **Torch** | Yes after download | Yes (Persian-only corpus/model) | No | Single-speaker Persian | Paper MOS ~3.76 on ManaTTS | Yes | Yes | **No** alone (fa only) |

---

## Engine notes

### Kokoro — no Persian

Official `VOICES.md` lists: American English, British English, Japanese, Mandarin, Spanish, French, Hindi, Italian, Brazilian Portuguese. **Persian/Farsi is absent.** Waku’s `KPipeline(lang_code="b")` + `bm_george` is English-only by design. Keep Kokoro only as an **English-side** option in a dual-engine design, or drop for a Piper-only path.

### Piper — strongest single-engine fa+en candidate

- Current packaging: `pip install piper-tts` → [OHF-Voice/piper1-gpl](https://github.com/OHF-Voice/piper1-gpl), license **GPL-3.0-or-later**; inference deps `onnxruntime` (no torch).
- Voices hosted at `rhasspy/piper-voices`; **fa_IR** and **en_US/en_GB** both listed in official VOICES docs.
- Fast/local positioning + quality tiers documented on the samples site; Home Assistant and Speech Dispatcher integrations exist upstream.
- **License seam for #22:** engine GPL vs older MIT tree; each voice’s `MODEL_CARD` must be reviewed (amir medium: CC0 dataset; finetuned from lessac).
- Mixed-script turns need an explicit routing policy (detect script → pick fa vs en voice) — product decision for #22/#23, not inventable here.

### MMS / Fairseq — fa+en but non-commercial

- `fas` and `eng` both in the official TTS language list; HF cards `facebook/mms-tts-fas` / `mms-tts-eng`.
- Fairseq README and model cards: **CC-BY-NC 4.0**.
- Torch + Transformers (or fairseq+VITS). Per-language checkpoints (not one multilingual synthesizer).
- Transformers docs warn some non-Roman languages need **uroman** preprocessing; Persian card’s snippet shows Persian text via `AutoTokenizer` — #22 should verify `is_uroman` on `mms-tts-fas` before relying on it.
- idiap `coqui-tts` can load Fairseq/MMS VITS by language code — same NC weight license applies.

### Coqui / XTTS — not a fa path

XTTS-v2 advertised languages: en, es, fr, de, it, pt, pl, tr, ru, nl, cs, **ar**, zh-cn, ja, hu, ko, hi — **no fa**. CPML weights. Park unless a future Persian fine-tune with a clear license appears.

### espeak-ng — universal low-quality floor

Documents `fa` and English accents; GPL; tiny; works offline on Linux/macOS. Quality is classic formant TTS. Reasonable **always-available fallback**, not a teaching-demo “nice voice” default.

### Platform TTS

- **macOS `say`:** Apple feature-availability lists **Farsi** for Spoken Content / VoiceOver / Live Speech. Viable *optional* macOS backend **only if** the Farsi voice is installed; Waku’s English-only `_best_say_voice()` must not be copied. Cannot satisfy Linux.
- **Linux Speech Dispatcher / Festival:** middleware; Persian neural path in the wild is typically **Piper** behind speechd, not a separate Festival Persian stack. Treat as OS integration, not a Yar engine choice.

### Persian-only research models

ManaTTS Tacotron2 (CC0 weights) is a Persian quality reference / possible fa half of a dual-engine design, but it is not an English engine and adds torch + research packaging cost.

---

## Combinations worth shortlisting

| Pattern | How it meets fa+en | Tradeoffs |
|---------|--------------------|-----------|
| **A. Piper-only** | Load `fa_IR-*` and `en_*-*` ONNX voices in one onnxruntime stack | GPL engine; two ~60 MB downloads; voice switch on language; quality “good neural,” not Kokoro-grade English |
| **B. Piper-fa + Kokoro-en** | Piper for Persian; Kokoro (torch or onnx) for English | Best English of the Waku lineage + real fa; two stacks; larger install; routing logic |
| **C. espeak-ng fallback** | `-v fa` / `-v en` when neural voices missing | Tiny; robotic; good fail-soft for teaching installs |
| **D. macOS `say` optional accel** | System voices when fa+en installed | macOS-only; never the cross-platform default |
| **E. Piper via sherpa-onnx** | Same Piper voices, Apache-licensed runtime | Packaging/API choice, not a new capability set |

**Not shortlisted as defaults:** Kokoro alone; Waku say+Kokoro-as-is; XTTS; MMS (NC); ManaTTS alone.

---

## Shortlist for #22 (engine-choice ticket)

Do **not** treat order as a ranking winner — criteria for #22 to weigh:

1. **Piper single-engine (fa_IR + en_US or en_GB voices)** — only clear neural offline fa+en on Linux+macOS in this survey; onnxruntime; per-voice license check.
2. **Dual-engine: Piper (fa) + Kokoro or kokoro-onnx (en)** — if #22 wants higher English quality than Piper while keeping Persian neural.
3. **espeak-ng** — cross-platform fa+en baseline / offline fallback (accept robotic quality).
4. **Optional: macOS `say`** — macOS acceleration when Farsi + English system voices are present; never sufficient alone.

**Explicit rejects for default path:** Kokoro-only; cloud APIs; MMS-TTS as default (CC-BY-NC); XTTS (no fa + CPML).

---

## Open points deferred to #22 / #23 / #24

- Exact fa/en routing for mixed-script assistant replies.
- Whether GPL (`piper-tts`) is acceptable under Yar’s dependency / extras policy vs vendoring an MIT-era Piper binary / using sherpa-onnx.
- First-run download UX into `.yar/` (which voices, how many MB).
- Whether Kokoro’s torch dep is allowed in `[voice]` or only the ONNX build.
- Speakable-text / Persian punctuation interaction with each engine (#21).
