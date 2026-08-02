# Survey: local STT options for Persian + English

**Ticket:** [#18](https://github.com/eiliya-mohebi/yar-agent/issues/18) · Map: [#17](https://github.com/eiliya-mohebi/yar-agent/issues/17)  
**Branch:** `research/local-stt-fa-en`  
**Date:** 2026-08-02  
**Scope:** CLI voice gateway, push-to-talk, local-only STT, full fa+en parity (incl. mixed-script turns), Linux + macOS. Destination is a handoff into `docs/voice.md` via later tickets — **no winner picked here.**

## Locked product constraints (from #17)

- Optional extra packaging (Waku-shaped `[voice]`), not on the default path.
- Same text pipeline after transcription (gateway only moves words in/out).
- Whisper-family engines share one quality profile for fa/en; monolingual Kaldi/ONNX stacks need dual models or routing for parity.

## Waku baseline (reference)

Waku’s ears are `faster-whisper` with default model `base`, `compute_type="int8"`, optional `language=` / env pin:

- Source: `/home/eiliya/ml_projects/waku-agent/waku/gateway/voice.py` (`Ears` class; docstring claims ~74MB first-run download for `base`).
- Extra: `voice = ["faster-whisper>=1.0", "sounddevice>=0.4"]` in `/home/eiliya/ml_projects/waku-agent/pyproject.toml`.
- Measured CT2 Hub weight for `Systran/faster-whisper-base` `model.bin`: **~145 MB** (HTTP Content-Length 145217532) — Waku’s “~74MB” matches Whisper **parameter** count (74M), not download size.

---

## Shared Whisper quality facts (all Whisper ports)

These apply to **faster-whisper**, **whisper.cpp / pywhispercpp**, **sherpa-onnx Whisper**, **mlx-whisper**, and **openai-whisper** when using multilingual (non-`.en`) checkpoints.

| Fact | Source |
| --- | --- |
| Persian (`fa`) is a first-class language token | [openai/whisper `tokenizer.py` `LANGUAGES`](https://raw.githubusercontent.com/openai/whisper/main/whisper/tokenizer.py) (`"fa": "persian"`) |
| Code + weights MIT | [openai/whisper README](https://github.com/openai/whisper/blob/main/README.md) |
| Multilingual sizes tiny→large (+ turbo); `.en` models are English-only | same README model table |
| Auto language detection built into decode path (`language=None`) | faster-whisper README usage prints `info.language`; openai-whisper CLI `--language` optional |
| Training data for Persian ~**392 hours** (paper appendix language hours list) | [Whisper paper PDF](https://cdn.openai.com/papers/whisper.pdf) (appendix; “Persian 392”) |
| Maintainer: intended for **monolingual** inputs; **code-switching not well supported** | [openai/whisper discussion #1160](https://github.com/openai/whisper/discussions/1160) (jongwook) |
| Community fine-tune of `whisper-small` on FLEURS Farsi reports **~25.8% WER** (improvement over base small, not a Yar default) | [AmirMohseni/whisper-small-persian](https://huggingface.co/AmirMohseni/whisper-small-persian) |

**Mixed-script / code-switch implication for Yar:** no surveyed engine claims strong mid-utterance fa↔en switching. Whisper can still emit mixed tokens when language is pinned or detected as one language; reliability is weaker than monolingual turns. Per-turn language pin (`fa` / `en` / auto) remains a #23 decision. Dual monolingual engines (Vosk, Shenava+en) need an explicit router and are worse for mid-turn mixes unless segmented.

---

## Candidate matrix

Sizes below: **wheel ≈** largest relevant Linux/macOS PyPI wheel for current release (order-of-magnitude install); **model ≈** first-run weights. Mic capture (`sounddevice` / PortAudio) is shared across options and omitted from engine-specific deps unless noted.

### 1. faster-whisper (Waku’s choice)

| Dimension | Finding |
| --- | --- |
| **What** | CTranslate2 reimplementation of OpenAI Whisper |
| **License** | MIT ([PyPI](https://pypi.org/project/faster-whisper/), [repo](https://github.com/SYSTRAN/faster-whisper)) |
| **Install size** | Package wheel ~1 MB; pulls **ctranslate2** ~40 MB, **onnxruntime** ~19 MB, **av** ~35 MB (+ tokenizers / huggingface-hub). **Models (CT2 `model.bin`):** tiny ~76 MB · base ~145 MB · small ~484 MB · medium ~1.5 GB · large-v3 ~3.1 GB |
| **Runtime deps** | Python ≥3.9; `ctranslate2`, `onnxruntime`, `av`, `tokenizers`, `huggingface-hub`. **No PyTorch** on the default path. Optional NVIDIA cuBLAS/cuDNN for CUDA. CPU `int8` is the Waku path. |
| **Offline** | After Hub download of CT2 weights, inference is local. First run needs network unless models are pre-seeded. |
| **fa/en quality** | Same multilingual Whisper weights; Persian officially supported; quality scales with size (base is light/weak for fa — paper + community note small/medium/large for non-English). English strong even at small sizes. |
| **Language detection** | Yes — `transcribe(..., language=None)` returns `info.language` / probability ([README](https://raw.githubusercontent.com/SYSTRAN/faster-whisper/master/README.md)). |
| **Linux + macOS** | Yes (CPU; CUDA Linux when libs present). |
| **`[voice]` fitness** | **High.** Matches Waku extras shape; pure pip/uv; no system toolchain. Teaching-repo continuity. |

### 2. whisper.cpp via `pywhispercpp`

| Dimension | Finding |
| --- | --- |
| **What** | C/C++ Whisper port (ggml); Python bindings package [`pywhispercpp`](https://pypi.org/project/pywhispercpp/) |
| **License** | whisper.cpp MIT ([badge/README](https://github.com/ggml-org/whisper.cpp)); pywhispercpp MIT (PyPI) |
| **Install size** | pywhispercpp wheel ~4 MB. **ggml models** ([models README](https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md)): tiny 75 MiB · base 142 MiB · small 466 MiB · medium 1.5 GiB · large-v3 2.9 GiB · large-v3-turbo 1.5 GiB · q5 quants smaller |
| **Runtime deps** | Prebuilt wheels ship native lib; optional Metal/Core ML / CUDA / Vulkan backends via build flags. No CTranslate2/onnxruntime stack. |
| **Offline** | Fully offline after ggml download. |
| **fa/en quality** | Same Whisper multilingual models; Persian listed in whisper.cpp language table / maintainer replies ([issue #2614](https://github.com/ggml-org/whisper.cpp/issues/2614)). |
| **Language detection** | Yes (Whisper LID; CLI `-l auto` / API equivalents). |
| **Linux + macOS** | First-class (Metal/Core ML strong on Apple Silicon). |
| **`[voice]` fitness** | **High–medium.** Smaller Python dep tree than faster-whisper; platform acceleration story is clearer on Mac. Binding maturity / API surface is thinner than faster-whisper; may need subprocess to `whisper-cli` as fallback. |

### 3. sherpa-onnx (Whisper path and/or Persian specialist)

| Dimension | Finding |
| --- | --- |
| **What** | ONNXRuntime-based local ASR/TTS toolkit; factories include `from_whisper`, NeMo CTC/transducer, SenseVoice, etc. ([docs](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/index.html), [PyPI](https://pypi.org/project/sherpa-onnx/)) |
| **License** | Apache-2.0 ([k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)) |
| **Install size** | `sherpa-onnx` ~4 MB + `sherpa-onnx-core` ~10–36 MB by platform. Models separate: Whisper ONNX exports (tiny→large) or Persian community exports (e.g. Shenava CTC ~tens of MB; RNNT int8 ~136 MB encoder+decoder+joiner per [Shenava-Koochik-v1.5-RNNT-sherpa-onnx](https://huggingface.co/Reza2kn/Shenava-Koochik-v1.5-RNNT-sherpa-onnx)) |
| **Runtime deps** | Bundled native core; CPU by default; optional CUDA wheels. No torch for Whisper/NeMo ONNX paths. |
| **Offline** | Yes after model files are present (manual download / release assets — less “string name auto-fetch” than faster-whisper). |
| **fa/en quality** | (A) Whisper ONNX → same Whisper fa/en profile. (B) **Persian-only** Shenava / NeMo exports claim strong fa (community model cards; CC-BY-4.0 for Shenava cards) but **not** English — would need a second English model + router for Yar parity. |
| **Language detection** | Whisper path: yes (infer language if unset). Spoken LID also documented via multilingual Whisper models. Monolingual NeMo/Shenava: no LID (language is the model). |
| **Linux + macOS** | Yes (official wheels). |
| **`[voice]` fitness** | **Medium–high** for Whisper-ONNX single model; **medium** if pursuing dual Shenava+en (more UX/config; better fa ceiling). Apache-2.0 friendly. Heavier conceptual surface than “one WhisperModel string”. |

### 4. Vosk (Kaldi)

| Dimension | Finding |
| --- | --- |
| **What** | Offline Kaldi-based ASR with per-language model packs |
| **License** | API Apache-2.0 ([vosk-api](https://github.com/alphacep/vosk-api)); listed fa/en models Apache-2.0 on [models page](https://alphacephei.com/vosk/models) (avoid AGPL/NC listed variants) |
| **Install size** | Wheel ~7 MB (manylinux). **Models:** small-en-us 40M · en-us-0.22 1.8G · small-fa-0.42 **53M** (WER 23.4 CV17 / 14.0 Fleurs) · fa-0.42 **1.6G** (16.7 / 11.1) — same page |
| **Runtime deps** | `cffi`, bundled native libs; streaming API; no torch. |
| **Offline** | Yes after model zip download. |
| **fa/en quality** | Explicit Persian models with published WER; English models mature. Official notes on fa models: “not yet accurate but better than before.” |
| **Language detection** | **No** single multilingual model — load one language model at a time. Mixed fa+en turns require dual instances + custom routing/segmentation. |
| **Linux + macOS** | Yes. |
| **`[voice]` fitness** | **Low–medium for Yar’s fa+en parity.** Light and proven offline, but dual-model design fights mixed-script turns and “one optional extra” simplicity. |

### 5. openai-whisper (reference / non-shortlist)

| Dimension | Finding |
| --- | --- |
| **License** | MIT |
| **Deps** | **PyTorch** + ffmpeg/tiktoken — heavy vs faster-whisper for same accuracy ([faster-whisper README](https://raw.githubusercontent.com/SYSTRAN/faster-whisper/master/README.md): up to ~4× faster, less memory) |
| **fa/en / LID** | Same as Whisper family |
| **`[voice]` fitness** | Poor vs faster-whisper unless torch is already required for TTS (Waku’s Kokoro path). Not shortlisted. |

### 6. mlx-whisper (reference / non-shortlist)

| Dimension | Finding |
| --- | --- |
| **License** | MIT ([PyPI](https://pypi.org/project/mlx-whisper/)) |
| **Deps** | `mlx`, and listed requires include **torch** + numba/scipy/tiktoken |
| **Platform** | **Apple Silicon only** — cannot alone satisfy Linux + macOS |
| **`[voice]` fitness** | Optional Mac accel backend later; not a sole shortlist engine. |

---

## Cross-cutting notes for later tickets (#22 / #23 / #24)

1. **Default model size vs fa quality:** Waku `base` is fine for English PTT demos; Persian will likely need `small`+ (or turbo/large) — trade RAM/latency. Decide in engine-choice / language tickets with a smoke checklist, not CI audio gates (map #17).
2. **Never ship `.en` checkpoints** if fa is required.
3. **Auto-detect vs pin:** Whisper LID exists but is imperfect (paper Fleurs LID underperforms supervised SOTA). Mixed turns: pin or segment; document expected failure modes.
4. **First-run UX:** Hub/ggml download needs clear progress + offline failure; seed under `.yar/` if caching locally.
5. **Extras layout:** STT alone fits `[voice]`; neural TTS (torch) may stay a separate extra (Waku `[voice-neural]`). STT choice should not force torch.
6. **WSL:** engine choice orthogonal; mic path is environment (map notes) — fail clearly if PortAudio sees no device.

---

## Shortlist for #22 (engine choice) — do not pick a winner here

Ordered for decision convenience, not preference:

1. **faster-whisper** — Waku parity; best “one pip extra + Hub model name” story; MIT; Linux+macOS; built-in LID; no torch.
2. **whisper.cpp (`pywhispercpp`)** — same Whisper fa/en quality; lighter native stack; strong Mac acceleration; MIT; LID via Whisper.
3. **sherpa-onnx (Whisper ONNX, optionally + Persian specialist later)** — Apache-2.0; Linux+macOS; Whisper path matches shortlist peers; only stack that also offers a serious **fa-specialized** upgrade path without leaving the toolkit.

**Surveyed but not shortlisted:** Vosk (dual monolingual packs hurt mixed turns); openai-whisper (torch cost, superseded by faster-whisper); mlx-whisper (macOS-ARM-only as sole engine).

---

## Sources (primary)

- Waku: `/home/eiliya/ml_projects/waku-agent/waku/gateway/voice.py`, `pyproject.toml`
- https://github.com/SYSTRAN/faster-whisper (+ README, MIT)
- https://pypi.org/project/faster-whisper/ · https://pypi.org/project/ctranslate2/
- https://huggingface.co/Systran/faster-whisper-{tiny,base,small,medium,large-v3} (Content-Length of `model.bin`)
- https://github.com/openai/whisper · https://raw.githubusercontent.com/openai/whisper/main/whisper/tokenizer.py
- https://cdn.openai.com/papers/whisper.pdf
- https://github.com/openai/whisper/discussions/1160
- https://github.com/ggml-org/whisper.cpp · models README · https://pypi.org/project/pywhispercpp/
- https://alphacephei.com/vosk/models · https://github.com/alphacep/vosk-api
- https://github.com/k2-fsa/sherpa-onnx · https://k2-fsa.github.io/sherpa/onnx/ · https://pypi.org/project/sherpa-onnx/
- https://huggingface.co/Reza2kn/Shenava-Koochik-v1.5-RNNT-sherpa-onnx (Persian specialist example)
- https://pypi.org/project/mlx-whisper/
- https://huggingface.co/AmirMohseni/whisper-small-persian (community fa fine-tune WER)
