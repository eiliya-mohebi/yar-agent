# Agent Instructions

This file is the source of truth for any coding agent (Claude Code, Cursor, Codex, etc.)
working in this repo. Read it before touching code. Deep design lives in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md); per-service specifics live in
[`backend/AGENTS.md`](backend/AGENTS.md) and [`frontend/AGENTS.md`](frontend/AGENTS.md).

**Yar** (یار — "companion, helper") is a local-first personal assistant that keeps the four
pillars behind every serious agent legible: **Harness, Loop, Memory, Eval/LLM-Ops**. It began
as a teaching repo you could read in an afternoon and is growing toward a full assistant. The
bar for every change: **clear, honest code a newcomer can follow — each pillar legible on its
own.** The project will get bigger; it must never get muddier.

## Stack

- **Backend:** Python 3.11+ (stdlib `http.server`) + `openai`
- **Backend package manager:** `uv` (lockfile: `backend/uv.lock`)
- **Frontend:** Vite + React SPA + TypeScript (strict)
- **Frontend styling:** Tailwind CSS + shadcn/ui
- **Frontend routing:** React Router
- **Frontend package manager:** `pnpm` only (lockfile: `frontend/pnpm-lock.yaml`)
- **Database:** SQLite + FTS5 (local file, no server)
- **Memory:** semantic (FTS5) · episodic (SQLite) · procedural (SKILL.md) + retrieval gate
- **LLM:** OpenAI `chat.completions` only — one provider, one wire format
- **Gateways:** CLI · dashboard SPA
- **Languages:** Persian (فارسی) **and** English, both first-class
- **Ops:** JSONL tracing (+ optional OTel), dashboard API on `:7777`, eval release gate

Stack is locked unless explicitly changed. Don't propose alternatives without a stated reason.
In particular: **not Next.js**, not bare `pip`/`venv` for day-to-day work, not `npm`/`yarn`.

**Out of scope — do not add back without being asked.** Other LLM providers (Anthropic,
Gemini, DeepSeek, xAI, OpenRouter, Kimi, GLM, MiniMax) and the Anthropic wire format; the
voice and Telegram gateways; Supabase pgvector and Notion memory backends; OS calendar
integration (Apple Calendar sync, Apple Mail/Reminders/Notes tools). Each cut and its seam is
documented in [ARCHITECTURE §13](docs/ARCHITECTURE.md#13-deliberately-out-of-scope). Don't leave
speculative hooks, flags, or `TODO: add provider X` comments for them either.

## Repo layout

```text
yar-agent/
├── AGENTS.md           # this file
├── README.md
├── docs/               # specs — see docs/README.md for the reading order
│   ├── ARCHITECTURE.md #   how the whole system works (read first)
│   ├── api.md          #   REST/SSE contract
│   └── frontend.md     #   SPA blueprint
├── backend/            # Python agent + API server (see backend/AGENTS.md)
└── frontend/           # Vite + React SPA (see frontend/AGENTS.md)
```

## Reference implementation

Yar is a port of **[waku-agent](https://github.com/ShenSeanChen/waku-agent)** (MIT), described
as of `main` @ [`871c4ac`](https://github.com/ShenSeanChen/waku-agent/tree/871c4ac). Renames:
package `waku/` → `backend/yar/`, env `WAKU_*` → `YAR_*`, home `.waku/` → `.yar/`.

**Before implementing anything, check waku for a working version of it.** These docs specify
contracts, not literals — prompt texts, the full FTS5 DDL, the token price map, the architecture
SVG, eval cases, and design token values live only in the source. Copy them; don't invent them,
and don't leave a placeholder prompt in a commit.
[ARCHITECTURE §14](docs/ARCHITECTURE.md#14-reference-implementation) has the file-by-file map, the list
of waku modules that must **not** be ported (they implement the §13 cuts), and the known defects to
fix on the way in — including the ASCII tokenizers that make waku English-only.

## Project rules (apply everywhere)

- **Be concise.** Short replies: lead with the answer, cut preamble and recap. A few lines
  beats a wall of text. Expand only when asked.
- **Never wipe runtime data without asking first, every time.** `scripts/demo_seed.py` and
  anything else that clears `.yar/` (memory, calendar, chat log, traces, or the `usage.jsonl`
  spend ledger) must be proposed and explicitly approved *immediately before each run*.
  Permission never carries over from a previous run. It refuses to run without `--yes`.

- **Gate before push:** `make gate` (deterministic must pass; judge runs with a key). When a
  live bug is found, fix it AND add a regression case to `evals/deterministic/`.
- **Persian and English are both required.** Yar must behave identically in فارسی and English,
  including mixed-script turns. The rule that prevents 90% of the damage: **never match user text
  with an ASCII character class (`[a-z0-9]`, `[a-zA-Z0-9]`) or `re.ASCII`** — tokenize only through
  `yar/text.py`, where plain `\w` is already Unicode. Persian failures are silent, not loud: an ASCII tokenizer
  turns a Persian message into zero tokens, so skills stop matching and memory searches return
  empty while every log looks fine. Full contract:
  [ARCHITECTURE §7](docs/ARCHITECTURE.md#7-language-support-persian-and-english). Any change
  to matching, search, prompts, dates, or UI text needs a Persian eval case, not just an English one.
- **No emojis** in any UI surface (dashboard, CLI output, README prose).
- **No new dependencies without discussion** — backend core is stdlib + `openai`; optional
  features go behind extras (`[eval]`, `[tracing]`, `[mcp]`, …). Frontend follows the
  pnpm + shadcn rules in [`frontend/AGENTS.md`](frontend/AGENTS.md). See the dependency policy below.
- **Scope:** scheduling is the flagship teaching task, and the default path stays
  one-of-everything (one provider, one wire format, one database, one no-extras gateway). New
  capabilities (tools, integrations) are welcome when they are self-contained, tested, opt-in,
  and keep the core legible. Reject complexity that muddies how the system works, bloats the
  default path, or adds a second implementation of something that already has one.

## Dependency policy

**Default: write it yourself. Reach for a library only when the alternative would be
non-trivial, error-prone, or reinvention of a standard.** Every dependency is a liability.

OK to depend on:
- Things genuinely hard to get right (LLM SDKs, HTTP clients, SQL drivers, parsers).
- The declared stack (`openai`, React, Vite, Tailwind, shadcn) and opt-in extras.

Not OK:
- Helper libraries wrapping 5–20 lines of stdlib / browser APIs.
- Frameworks where a function would do.
- "Nicer API" layers on top of an already-present dependency.
- Next.js / SSR / axios / lodash / moment (see per-service AGENTS.md).

Before adding a runtime dep, discuss it and answer in the commit message: (1) what it does that
we can't write in <30 lines of clear code, (2) how often it's used, (3) its maintenance /
transitive-dep footprint. Backend: use `uv add` (or extras). Frontend: use `pnpm add` and
respect the 7-day minimum release age.

## Configuration

- Backend: `backend/yar/config.py` (`Settings` + `load_settings()`) is the only config source.
  App code reads `Settings`, not scattered `os.getenv`. Knobs are `YAR_*` (see
  `backend/.env.example`). Runtime state lives in a gitignored `.yar/` directory.
- Frontend: `frontend/src/lib/env.ts` is the only place that reads `import.meta.env`. Client
  vars are prefixed `VITE_`.

Fail clearly when required config (`OPENAI_API_KEY`) is missing — never fall back to a mock.

## Code style (universal)

- **Small, obvious functions.** A 15-line function with clear names beats a three-class
  abstraction. The whole agent loop is ~95 lines on purpose.
- **No premature abstraction.** Extract on the third caller, not a hypothetical one.
- **Validate only at boundaries:** gateway input, external APIs, DB writes, untrusted parsing.
  Trust internal callers.
- **No backwards-compat shims / speculative feature flags** unless explicitly asked.
- **Comments explain *why*** when non-obvious, never *what*. Remove stale TODOs.
- **Keep files focused** and each pillar legible on its own.

## Commands

From `backend/` (via **uv**):

`uv sync` · `uv run yar` · `uv run yar dashboard` · `make run` · `make brief` ·
`make dashboard` (7777) · `make trace` (6006) · `make eval` · `make eval-judge` ·
`make gate` · `make lint`

From `frontend/` (via **pnpm**):

`pnpm install` · `pnpm dev` · `pnpm build` · `pnpm tsc --noEmit` · `pnpm lint`

Tests live under `backend/evals/`, not `tests/`. No frontend test suite.
