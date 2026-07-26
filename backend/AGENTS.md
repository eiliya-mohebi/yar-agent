# Backend — Agent Instructions

Python agent + stdlib API server. Read the root [`../AGENTS.md`](../AGENTS.md) first; this file
adds backend-specific rules. Deep design lives in [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

**Reference:** this package is a port of `waku/` from
[waku-agent](https://github.com/ShenSeanChen/waku-agent) (`main` @
[`871c4ac`](https://github.com/ShenSeanChen/waku-agent/tree/871c4ac)) — same module layout, minus
the [§13](../docs/ARCHITECTURE.md#13-deliberately-out-of-scope) cuts, with `WAKU_*` → `YAR_*`. Prompt literals (`DEFAULT_SOUL`, `GATE_PROMPT`,
`SUMMARIZER_PROMPT`, the judge rubric), the full `SCHEMA` DDL with its FTS5 triggers, the token
price map, and `dataset.jsonl` are **not** in these docs — lift them from source. See
[ARCHITECTURE §14](../docs/ARCHITECTURE.md#14-reference-implementation), which also lists waku's known defects — notably
its ASCII tokenizers, which must **not** be ported ([§7](../docs/ARCHITECTURE.md#7-language-support-persian-and-english)).

## Stack & entry points

- Python 3.11+, build with hatchling. Core deps: `openai`, `python-dotenv`, `rich`. Everything
  heavier is an opt-in extra (`[eval]`, `[tracing]`, `[mcp]`, `[dev]`).
- Console script: `yar = "yar.__main__:main"`. Subcommands: `yar` (cli), `yar dashboard`,
  `yar brief`, `yar skill install <url>`.
- **OpenAI is the only provider** and `chat.completions` the only wire format. Out of scope
  (don't add back unasked): other providers, the Anthropic wire format, voice/Telegram
  gateways, Supabase/Notion stores, OS calendar integration. See
  [ARCHITECTURE §13](../docs/ARCHITECTURE.md#13-deliberately-out-of-scope) for each seam.
- **Persian + English are both required** — see [ARCHITECTURE §7](../docs/ARCHITECTURE.md#7-language-support-persian-and-english). `yar/text.py` owns normalization and is the
  only tokenizer in the package.

## Package manager

**`uv` only.** Do not use bare `pip install` or `python -m venv` for day-to-day work. The
lockfile is `uv.lock` (commit it). If you see a hand-rolled `.venv` workflow without uv, fix
the docs/commands — don't invent a second path.

```bash
# from backend/
uv sync                              # create/sync .venv from uv.lock / pyproject.toml
uv sync --extra eval --extra mcp     # opt-in extras
uv run yar                           # run the console entry
uv run make gate                     # or: uv run python -m yar.ops.release_gate
uv add <pkg>                         # add a runtime dep (discuss first — see root policy)
uv add --dev <pkg>                   # add a dev dep
uv remove <pkg>
```

Before adding a runtime dep with `uv add`, follow the root dependency policy and justify it in
the commit message. Optional capabilities go behind extras, not into the default install.

## Package layout (file ↔ pillar)

```text
backend/
├── pyproject.toml        # console script + deps/extras
├── uv.lock               # locked deps (commit this)
├── Makefile              # run / dashboard / eval / gate / lint (prefer via `uv run`)
├── .env.example          # documented YAR_* catalog
├── yar/
│   ├── app.py            # assembly: config → db → memory → tools → session → loop → tracer
│   ├── config.py         # Settings + load_settings() — the ONLY config source
│   ├── db.py             # one SQLite file (state.db): facts, episodes, calendar, chat_log
│   ├── text.py           # fa/en normalization + the ONLY tokenizer; jalali dates
│   ├── gateway/          # HARNESS: cli (move text only); the SPA is the other gateway
│   ├── runtime/session.py# working memory: per-turn system prompt assembly
│   ├── loop/             # LOOP: agent.py (the ~95-line loop) + models.py (OpenAI client)
│   ├── tools/            # side effects: calendar (flagship), notes, messages, search, …
│   ├── memory/           # semantic / episodic / procedural + retrieval_gate + consolidation
│   └── ops/              # tracing, dashboard API, release_gate, evals
├── evals/                # deterministic (pytest) + judge (DeepEval)
├── skills/               # built-in procedural memory (SKILL.md)
└── scripts/              # demo_seed, shootout, validate_skills
```

## Rules that bite

- **The loop stays legible.** `loop/agent.py` is the whole trick — reason → act → observe with
  two guardrails (model stops asking for tools; max_iterations). Don't wrap it in indirection.
- **Config only through `Settings`.** No scattered `os.getenv` in app code; `config.py` loads
  `.env` once. The client and model defaults resolve in `loop/models.py` via `get_client()`.
- **One wire format.** The loop speaks OpenAI `chat.completions` natively (`role: tool`,
  `tool_calls`) — no adapter, no content-block translation, no provider table. Don't add an
  abstraction layer "in case" a second format arrives.
- **Adding a tool:** follow the `new-tool` skill — JSON schema, safe execution, honest output
  (return real errors, never fake success), AND a deterministic eval. `create_event` is the
  flagship: its eval asserts on `calendar_events` rows.
- **Memory:** the retrieval gate **fails open** (retrieve on error); consolidation runs via
  `Memory.maybe_consolidate()` when unconsolidated rows ≥ `consolidate_every * 2`, and is
  loss-safe (exception → leave rows unmarked). SQLite + FTS5 is the only backend; `state.db`
  must always work with no extras and no network.
- **Session history:** fold tool activity into `[tools used: …]` on the assistant history line
  or the model will re-fire tools (triple-book bug). See [ARCHITECTURE §3](../docs/ARCHITECTURE.md#3-the-loop-the-whole-trick).
- **Skills:** YAML frontmatter `name` + `description` required; match = word overlap ≥ 2,
  top 2 skills. `description` carries Persian **and** English trigger words. See [ARCHITECTURE §6](../docs/ARCHITECTURE.md#6-memory).
- **Text is Unicode, always.** Every tokenizer and every normalization goes through `yar/text.py`
  (`normalize()`, `tokens()`). An ASCII character class applied to user text — in skill matching,
  `_fts_query()`, date parsing, anywhere — is a **bug**, because it turns Persian into zero tokens
  and fails silently. Facts/episodes are normalized on write; queries with the same function.
  See [ARCHITECTURE §7](../docs/ARCHITECTURE.md#7-language-support-persian-and-english).
- **Evals:** `dataset.jsonl` + `ops/scoring.py` are the deterministic contract (substring args,
  `expect_tool: null` ⇒ no tools). Never mix with judge. Every flagship case has a Persian `-fa`
  counterpart. See [ARCHITECTURE §8](../docs/ARCHITECTURE.md#8-ops--eval).
- **Never wipe `.yar/` without explicit, immediate approval.** `demo_seed.py` backs up first
  and refuses without `--yes`; still ask every time (root rule).

## Evals — never mixed

- `evals/deterministic/` — 0/1 pytest, "did the right tool fire?". Offline tier uses a scripted
  client; live tier needs a key. Run: `uv run make eval` (or `make eval` inside an activated
  uv env).
- `evals/judge/` — DeepEval GEval quality scoring, needs `OPENAI_API_KEY`. Run: `make eval-judge`.
- Never put a judge assertion in the deterministic suite or vice versa.
- **Gate before push:** `make gate` runs deterministic (must be 100%) then judge if a key
  exists. Fix a live bug AND add a deterministic regression case.

## API surface

The dashboard server exposes the REST/SSE contract in [`../docs/api.md`](../docs/api.md).
When adding an endpoint, update that doc in the same change.

## Code style

Universal rules from root apply. Additionally: validate at boundaries (gateway input, LLM/tool
I/O, DB writes); trust internal callers; small modules, one concern each. The dashboard server
(`ops/dashboard.py`) is stdlib `http.server` bound to `127.0.0.1` — it exposes the REST API the
Vite SPA talks to. Restart it after backend edits (Python is held in memory).
