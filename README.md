<p align="center">
  <img src="docs/assets/yar-logo.png" alt="Yar — companion, helper" width="420" />
</p>

<h1 align="center">yar-agent</h1>

**Yar** (یار — "companion, helper") is a local-first personal assistant that keeps the four
pillars behind every serious agent legible: **Harness, Loop, Memory, and Eval/LLM-Ops**.
Everything runs on your machine against one SQLite file — no cloud server, no framework magic.
The whole agent loop is a ~95-line while-loop you can read in an afternoon.

Persian (فارسی) and English are both first-class. Ask in either language (or mix them) and Yar
replies in the same language.

The repo is split into a **backend** (Python agent + API server, managed with **uv**) and a
**frontend** (Vite + React SPA, managed with **pnpm**).

---

## ⚙️ How Yar works — the four pillars

```
You (CLI or dashboard)
  -> Gateway          # moves text in/out — no reasoning
  -> Session          # builds the system prompt (SOUL + clock + memory + skills)
  -> Loop             # reason -> act -> observe until a reply
  -> Memory           # save the turn; maybe consolidate into facts/episodes
  -> Tracer           # append a JSONL trace for this run
```

### 🔌 Harness / Gateway

The gateway only moves text. It does not think.

| Gateway | What it does |
| ------- | ------------ |
| **CLI** (`uv run yar`) | Terminal chat; live tool/gate feedback; `/memory`, `/quit` |
| **Dashboard SPA** | Vite + React UI talking to the API on `:7777` |

Same agent underneath. Pick the surface that fits the moment.

### 🔄 Loop

`run_loop()` is the entire agent — a reason → act → observe cycle:

1. Call the LLM with system prompt + history + your message.
2. If the model returns tool calls → run them, feed results back, repeat.
3. If the model replies in plain text → done (guardrail 1).
4. If `max_iterations` is hit → hard stop (guardrail 2). Never spin forever.

Working memory is rebuilt **every turn**: `SOUL.md` persona, a bilingual clock line
(Gregorian + Jalali), optional gated memory, and any matching skills.

### 🧠 Memory

Three kinds of durable state, all local:

| Kind | What it stores | Where |
| ---- | -------------- | ----- |
| **Semantic** | Durable facts ("name is ایلیا", "loves soccer") | SQLite FTS5 / BM25 |
| **Episodic** | Dated summaries of what happened | SQLite + recency |
| **Procedural** | How-to playbooks (`SKILL.md`) | Disk under `skills/` and `.yar/skills/` |

Two design choices matter:

- **Retrieval gate** — a small model first answers "does this turn need memory?" Skip search
  when it does not. Fails open (retrieve on error).
- **Consolidation** — after enough unconsolidated chats, a summarizer distills them into facts
  + one episode. Loss-safe: if summarization fails, the chat log stays unmarked.

A human-readable mirror is written to `.yar/MEMORY.md` after every turn.

### 📊 Eval / LLM-Ops

| Piece | Role |
| ----- | ---- |
| **Tracing** | Every run → `.yar/traces/YYYY-MM-DD.jsonl` (+ optional OTel) |
| **Dashboard API** | REST/SSE on `127.0.0.1:7777` for the SPA |
| **Deterministic evals** | 0/1: "did the right tool fire?" (`make eval`) |
| **Judge evals** | Scored quality: "was the reply good?" (`make eval-judge`) |
| **Release gate** | `make gate` — deterministic must be 100%, then judge if a key exists |

Deterministic and judge suites never mix. One is a unit test; the other is a scored opinion.

---

## 🇮🇷 Features with Persian examples

Yar replies in the language you use. Tool arguments stay canonical (ISO dates, English-ish
keys); the spoken reply stays فارسی when you write فارسی.

### 📅 Calendar — schedule and list events

Flagship teaching task. Creates a row in `calendar_events` and updates `.yar/calendar.ics`.

```text
شما: فردا ساعت ۱۰ صبح با دانیال جلسه بگذار برای بررسی پروژه
یار:  ثبت شد — «جلسه با دانیال» فردا ساعت ۱۰:۰۰ (با یادداشت بررسی پروژه).

شما: جلسه‌های این هفته را نشان بده
یار:  [list_events] … لیست رویدادهای هفته را برمی‌گرداند
```

Jalali dates work too — the clock line gives the model both calendars:

```text
شما: ۵ مرداد ساعت ۱۴ یک قرار قهوه با سارا بگذار
```

### 📝 Notes — save facts to semantic memory

```text
شما: یادداشت کن که اسم من ایلیاست و بهترین دوستم دانیال است
یار:  ذخیره شد. از این به بعد این‌ها را در حافظه دارم.

شما: من عاشق فوتبالم
یار:  یادداشت شد.
```

### 📨 Messages — draft to the local outbox

Writes a draft file under `.yar/outbox/` (does not send email for real).

```text
شما: یک پیام برای دانیال بنویس که جلسه فردا ساعت ۱۰ است
یار:  پیش‌نویس در outbox ذخیره شد.
```

### 🔍 Web search

```text
شما: قهرمان جام جهانی ۲۰۲۲ چه تیمی بود؟
یار:  [search_web] … پاسخ را از نتایج جستجو می‌سازد
```

### 💡 Memory recall — retrieval gate + search

On a later turn, the gate may pull facts/episodes into context:

```text
شما: بهترین دوست من کیه؟
یار:  دانیال — قبلاً گفتی بهترین دوستت دانیال است.
```

Inspect memory from the CLI with `/memory`, or open the Memory pages in the dashboard.

### 📖 Skills — procedural playbooks

Built-in skills (e.g. `schedule-meeting`, `weekly-brief`) match on keyword overlap in
Persian **and** English. Descriptions carry trigger words in both languages.

```text
شما: یک جلسه برنامه‌ریزی کن با علی برای سه‌شنبه صبح
یار:  [skill: schedule-meeting] → create_event …
```

Install more with:

```bash
uv run yar skill install <url>
```

### ☀️ Morning brief

```bash
uv run yar brief
# or: make brief
```

Produces a short morning briefing from calendar + memory (also landable in the outbox).

### 🖥️ Dashboard SPA

Teaching UI that makes each pillar visible: Overview, Gateway, Loop, Memory, Tools, Database,
Ops, Compare, Settings — plus a live chat dock with streaming tokens and gate/tool stages.

```bash
# terminal 1
cd backend && uv run yar dashboard    # API :7777

# terminal 2
cd frontend && pnpm dev               # Vite SPA
```

### 🏁 Compare arena & release gate

Race OpenAI model ids against each other on the Compare page, or ship only after:

```bash
cd backend && make gate   # deterministic must pass; judge runs with a key
```

---

## 🧱 Stack

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

---

## 📁 Repo layout

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

---

## ✅ Prerequisites

| Tool | Version | Used for | Install |
| ---- | ------- | -------- | ------- |
| [Python](https://www.python.org/downloads/) | 3.11+ | Backend runtime + agent | OS package manager or python.org |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Backend deps + lockfile | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Node.js](https://nodejs.org/) | 20+ (LTS) | Frontend toolchain | nodejs.org or `nvm install --lts` |
| [pnpm](https://pnpm.io/installation) | latest | Frontend package manager | `corepack enable && corepack prepare pnpm@latest --activate` |

You also need an **`OPENAI_API_KEY`**. OpenAI is the only supported provider.

---

## 🚀 Running locally

### 🐍 Backend

```bash
cd backend
uv sync                              # create/sync .venv from uv.lock
# optional extras: uv sync --extra eval --extra tracing --extra mcp
cp .env.example .env                 # set OPENAI_API_KEY

uv run yar                           # chat in the terminal
uv run yar dashboard                 # API on http://127.0.0.1:7777
make gate                            # deterministic evals must pass before shipping
```

### ⚡ Frontend

```bash
cd frontend
pnpm install
pnpm dev                             # Vite dev server; points at VITE_API_BASE_URL
```

Set `VITE_API_BASE_URL=` (empty = Vite proxy to `:7777`) or an absolute loopback URL (see `frontend/.env.example`).
Restart the backend after Python changes; the Vite SPA hot-reloads UI edits.

### 📋 Quick CLI cheatsheet

| Command | What it does |
| ------- | ------------ |
| `uv run yar` | Chat in the terminal |
| `uv run yar dashboard` | Start the API for the SPA (`:7777`) |
| `uv run yar brief` | Morning briefing |
| `uv run yar skill install <url>` | Install a procedural skill |
| `make gate` | Release gate (deterministic + optional judge) |
| `make eval` / `make eval-judge` | Run each eval suite alone |
| `make trace` | Optional Phoenix UI on `:6006` (needs tracing extra) |

---

## 📚 Where to go next

- **[docs/](docs/README.md)** — spec index and reading order; start here to build.
- **[AGENTS.md](AGENTS.md)** — rules for coding agents (also [`backend/AGENTS.md`](backend/AGENTS.md),
  [`frontend/AGENTS.md`](frontend/AGENTS.md)).
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — whiteboard, pillars, system prompt, model
  access, memory, language support, evals, rebuild order, and what's out of scope.
- **[docs/api.md](docs/api.md)** — full `/api/*` route + payload contracts for the SPA.
- **[docs/frontend.md](docs/frontend.md)** — Vite + React SPA structure and conventions.

---

## 🔗 Reference implementation

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
