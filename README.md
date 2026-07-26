# yar-agent

**Yar** (یار — "companion, helper") is a local-first personal assistant that makes the four
pillars behind every serious agent legible: **Harness, Loop, Memory, and Eval/LLM-Ops**.
Everything runs on your machine against one SQLite file — no server, no framework magic. The
whole agent loop is a ~95-line while-loop you can read in an afternoon.

The repo is split into a **backend** (Python agent + API server, managed with **uv**) and a
**frontend** (Vite + React SPA, managed with **pnpm**).

## Stack

| Layer | Choice |
| ----- | ------ |
| Backend | Python 3.11+ (stdlib `http.server`) + `openai` |
| Backend package manager | [uv](https://docs.astral.sh/uv/) (`uv.lock`) |
| Frontend | Vite + React SPA + TypeScript |
| Frontend styling | Tailwind CSS + shadcn/ui |
| Frontend routing | React Router |
| Frontend package manager | [pnpm](https://pnpm.io/) (`pnpm-lock.yaml`) |
| Agent loop | ~95-line reason → act → observe while-loop |
| Database | SQLite + FTS5 (local file, no server) |
| Memory | semantic (FTS5) · episodic (SQLite) · procedural (SKILL.md) + retrieval gate |
| Retrieval | SQLite FTS5 / BM25 |
| LLM | OpenAI `chat.completions` — one provider, one wire format |
| Gateways | CLI · dashboard SPA |
| Languages | Persian (فارسی) and English, both first-class · RTL-aware UI |
| Ops | JSONL tracing (+ optional OTel), API on `:7777`, eval release gate |

**One of everything on the default path:** one provider, one wire format, one database, one
gateway that runs with no extras. What's deliberately excluded — other providers, voice and
Telegram gateways, Supabase/Notion backends, OS calendar sync — and where each seam is:
[ARCHITECTURE §13](docs/ARCHITECTURE.md#13-deliberately-out-of-scope).

**Bilingual is a requirement, not a translation pass.** Persian breaks keyword memory in silent
ways (an ASCII tokenizer reduces a Persian sentence to zero tokens, so skills stop firing and
searches come back empty with no error). The rules that prevent it — one Unicode
normalize/tokenize module, letter and digit folding, a bilingual clock line, RTL UI, and Persian
eval cases in the release gate — are specified in
[ARCHITECTURE §7](docs/ARCHITECTURE.md#7-language-support-persian-and-english).

## Repo layout

```
yar-agent/
├── AGENTS.md                 # agent instructions (read first)
├── README.md                 # this file
├── docs/
│   ├── README.md             # spec index + reading order
│   ├── ARCHITECTURE.md       # how the whole system works (start here to rebuild)
│   ├── frontend.md           # SPA deep-dive
│   └── api.md                # backend REST/SSE contracts
├── backend/                  # Python agent + API server (the four pillars)
│   ├── pyproject.toml        # console script `yar`; core deps + opt-in extras
│   ├── uv.lock               # locked deps
│   ├── Makefile              # run / dashboard / eval / gate / lint
│   ├── yar/                  # the package (gateway, loop, memory, tools, ops, runtime)
│   ├── evals/                # deterministic (pytest) + judge (DeepEval) suites
│   ├── skills/               # built-in procedural memory (SKILL.md)
│   └── scripts/              # demo_seed, shootout, validate_skills
└── frontend/                 # Vite + React SPA
    ├── src/                  # components, pages, lib, App.tsx
    ├── package.json
    ├── pnpm-lock.yaml
    └── vite.config.ts
```

Runtime state lives in a gitignored `.yar/` directory (SQLite, calendar, traces, outbox).

## Prerequisites

| Tool | Version | Used for | Install |
| ---- | ------- | -------- | ------- |
| [Python](https://www.python.org/downloads/) | 3.11+ | Backend runtime + agent | OS package manager or python.org |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Backend deps + lockfile | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Node.js](https://nodejs.org/) | 20+ (LTS) | Frontend toolchain | nodejs.org or `nvm install --lts` |
| [pnpm](https://pnpm.io/installation) | latest | Frontend package manager | `corepack enable && corepack prepare pnpm@latest --activate` |

You also need an **`OPENAI_API_KEY`**. OpenAI is the only supported provider.

## Running locally

### Backend

```bash
cd backend
uv sync                              # create/sync .venv from uv.lock
# optional extras: uv sync --extra eval --extra tracing --extra mcp
cp .env.example .env                 # set OPENAI_API_KEY

uv run yar                           # chat in the terminal
uv run yar dashboard                 # API on http://127.0.0.1:7777
make gate                            # deterministic evals must pass before shipping
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev                             # Vite dev server; points at VITE_API_BASE_URL
```

Set `VITE_API_BASE_URL=http://127.0.0.1:7777` (see `frontend/.env.example` once created).
Restart the backend after Python changes; the Vite SPA hot-reloads UI edits.

## Where to go next

- **[docs/](docs/README.md)** — spec index and reading order; start here to build.
- **[AGENTS.md](AGENTS.md)** — rules for coding agents (also [`backend/AGENTS.md`](backend/AGENTS.md),
  [`frontend/AGENTS.md`](frontend/AGENTS.md)).
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — whiteboard, pillars, system prompt, model
  access, memory, language support, evals, rebuild order, and what's out of scope.
- **[docs/api.md](docs/api.md)** — full `/api/*` route + payload contracts for the SPA.
- **[docs/frontend.md](docs/frontend.md)** — Vite + React SPA structure and conventions.

## Reference implementation

These docs describe the **Yar target layout** (`backend/` + `frontend/`, package `yar`,
`uv` + `pnpm`). Behavior and contracts are reverse-engineered from the working Waku source;
names and packaging are the Yar redesign.

**[github.com/ShenSeanChen/waku-agent](https://github.com/ShenSeanChen/waku-agent)** (MIT) is the
reference — described here as of `main` @ [`871c4ac`](https://github.com/ShenSeanChen/waku-agent/tree/871c4ac).
Treat these files as a **port guide, not a standalone spec**: they specify every contract but
deliberately omit some long literals (prompt texts, the full SQL DDL, the token price map, the
architecture SVG). [ARCHITECTURE §14](docs/ARCHITECTURE.md#14-reference-implementation) maps each
omission to the file it lives in, plus the `waku` → `yar` renames, the modules not to port, and
waku's known defects to fix on the way in (it is English-only in practice).
