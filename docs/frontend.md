# yar-agent — Frontend

Reverse-engineering blueprint for the dashboard SPA. Stack rules live in
[`../frontend/AGENTS.md`](../frontend/AGENTS.md). API contracts: [`api.md`](api.md).
Pillars / backend: [`ARCHITECTURE.md`](ARCHITECTURE.md) (same folder).

**Yar target:** Vite + React + TypeScript + Tailwind + shadcn/ui + React Router + **pnpm**.
**Behavior source today:** the Waku cockpit — `waku/ops/static/` in
[waku-agent](https://github.com/ShenSeanChen/waku-agent) (`main` @
[`871c4ac`](https://github.com/ShenSeanChen/waku-agent/tree/871c4ac)), vanilla JS, ~2,400 lines.
Port features and contracts from that UI; do not invent a generic admin CRUD app. Each page
should still teach one pillar box.

Two things this doc names but does not contain — copy them from source: the **architecture SVG**
(`static/js/diagram.js`: `archSVG()` + the `STAGE` map) and the **design token values**
(`static/style.css`; §10 below lists only the token names).

**Do not port** (cut from Yar — see [ARCHITECTURE §13](ARCHITECTURE.md#13-deliberately-out-of-scope)):
the mic / voice transcription path, provider pickers and multi-provider model ids, the Notion
episodic banner and episodic-backend switch, and Apple tool toggles. Models are plain OpenAI
model ids everywhere.

**Must add** (waku's cockpit is LTR-only): full RTL / bidi support, since Persian is a first-class
language ([ARCHITECTURE §7](ARCHITECTURE.md#7-language-support-persian-and-english)).
See §11 below — this is a build requirement, not a polish pass.

---

## 1. Stack

| Piece | Choice |
| ----- | ------ |
| Bundler / dev server | Vite |
| UI | React 18+ SPA + TypeScript (strict) |
| Styling | Tailwind CSS; global tokens in `src/index.css` |
| Components | shadcn/ui (`pnpm dlx shadcn@latest add <name>`) |
| Routing | React Router (`/overview`, `/memory/semantic`, … — map old `#hash`/`#view/sub`) |
| Package manager | pnpm only; `.npmrc` `minimum-release-age=10080` |
| HTTP | native `fetch` via `@/lib/http` + `@/lib/api` |
| Backend | `VITE_API_BASE_URL` (default `http://127.0.0.1:7777`); Vite `server.proxy` preferred |

**Not used:** Next.js, SSR, axios, lodash, moment, CSS modules, styled-components, vitest /
Playwright / Cypress.

**UI rules:** no emojis (project rule). Pin stars `★`/`☆` are the one typographic exception.
Persian and English are both first-class: the shell is bidi-aware and all user/model text carries
`dir="auto"` (§11).

---

## 2. Shell layout (three columns)

The cockpit is one viewport with three independently scrolling columns:

```
┌──────────┬─────────────────────────────┬──────────────────┐
│  nav     │  main                       │  chat dock       │
│  brand   │  pagehead (title + live)    │  New / History   │
│  links   │  #view / <Outlet>           │  stats · model   │
│  counts  │                             │  transcript      │
│          │                             │  input + send    │
└──────────┴─────────────────────────────┴──────────────────┘
     ↕ resizer                          ↕ resizer
```

| Region | Job |
|--------|-----|
| **Nav** | Brand + clickable current `model` (→ Settings). Links: Overview, Gateway, Loop, Memory, Tools, Database, Ops, Compare, Settings. Badge counts from `D` (msg count, turns, facts+episodes, calendar+outbox, table count, tool_errors / missing eval). Collapse + drag-resize; widths/hidden state in `localStorage` (`navW`, `navHidden`). |
| **Main** | Sticky page title + live subtitle (`live · updated Ns ago · {home}`). Route content. |
| **Dock** | Always-available chat. New chat, History menu, stats toggle, model chip, streaming transcript, text input, Send. Collapse (`dockClosed`); width `dockW`. Default closed on narrow viewports (<~1180px). |

Resizers: drag handles between columns; CSS vars `--nav-w` / `--dock-w`.

---

## 3. Target file layout

Map old vanilla modules → React concerns:

```text
frontend/
├── src/
│   ├── components/
│   │   ├── layout/          # Shell, Nav, Dock, Resizer, PageHead
│   │   ├── chat/            # Transcript, ChatBubble, StreamPending, TelemetryFooter
│   │   ├── diagram/         # ArchitectureSvg + live animation (node/edge ids)
│   │   ├── memory/          # FactEditor, SoulEditor, SkillEditor
│   │   ├── models/          # ModelChip, Catalog, Pins (★/☆)
│   │   ├── compare/         # Race form, ResultCols, Scoreboard, Scatter
│   │   └── ui/              # shadcn primitives
│   ├── pages/               # one route file per nav item (+ Memory/Tools/Database subroutes)
│   ├── hooks/               # useDashboardData, useChatStream, useTraceEvents, useLocalChrome
│   ├── lib/
│   │   ├── api.ts           # typed get/post + SSE helpers
│   │   ├── http.ts          # thin fetch wrapper, ApiError, isNetworkError
│   │   ├── env.ts           # ONLY import.meta.env reader
│   │   ├── markdown.ts      # escape-first tiny markdown (XSS-safe)
│   │   └── types.ts         # DashboardData, Turn, Session, … from /api/data
│   ├── App.tsx              # Router + Shell
│   ├── main.tsx
│   └── index.css            # Tailwind + design tokens (light/dark)
├── index.html
├── vite.config.ts           # @ alias + proxy /api → :7777
├── tsconfig.json
├── .npmrc
└── package.json
```

**Old → new map**

| Vanilla (`ops/static/js/`) | React home |
|----------------------------|------------|
| `util.js` | `lib/markdown`, `lib/http`, reveal helper |
| `main.js` | `hooks/useDashboardData`, layout chrome |
| `dock.js` | Dock + session/history/model chip |
| `render.js` | chat components + `useChatStream` |
| `views.js` | `pages/*` |
| `memory.js` | memory editors |
| `models.js` | Settings + model components (`applyModel` = sole settings writer) |
| `diagram.js` | `components/diagram` |
| `compare.js` | Compare page |

---

## 4. Data flow

```
mount
  -> useDashboardData: GET /api/data every ~5s  →  DashboardData (D)
  -> render route from D
  -> useTraceEvents: GET /api/events?cursor= every ~450ms  →  diagram animation
mutations (settings, memory, pin, session, …)
  -> api.post(…)
  -> refetch /api/data
chat
  -> POST /api/chat/stream (SSE)
  -> apply events to pending bubble
  -> on done: refetch /api/data
```

### Guards (port these — silent bugs otherwise)

| Guard | Why |
|-------|-----|
| **`editing`** | While the user edits SOUL/skill/fact/settings, skip wiping that form on the 5s poll. Clear on navigation. |
| **`animating`** | Don't rebuild the Overview diagram mid-animation or glow nodes get wiped. |
| **Scroll preserve** | Same-route refresh keeps `main` scrollTop; only jump to top on real navigation. |
| **Compare self-heal** | While on Compare and not mid-race / mid-edit, re-pull `/api/compare/history` ~every 5s. |
| **Dock restore** | On first load, load current session history into the dock so refresh doesn't look empty. |

---

## 5. `DashboardData` (`GET /api/data`)

Types the SPA must model (from `collect()`). Full field notes also in [api.md](api.md).

| Key | Use in UI |
|-----|-----------|
| `model`, `home`, `generated_at` | Brand chip, live subtitle |
| `stats` | Tiles + badges: `turns`, `tool_calls`, `tool_errors`, `gate_skips`, `gate_retrieves`, `tokens_in`/`out`, `cost`, `latency_avg`/`p95`, `trace_files` |
| `usage` | All-time spend (`total_cost`, …) |
| `turns` | Loop page + Overview "latest turn" (newest first, capped ~50) |
| `facts`, `episodes` | Memory semantic/episodic |
| `soul`, `skills`, `chat_pending`, `consolidate_every` | Memory SOUL / skills / consolidation |
| `chat_log` | Raw recent messages (Gateway/ops); prefer sessions for inbox |
| `sessions`, `current_session` | Gateway inbox + dock History |
| `calendar`, `outbox` | Tools results |
| `tools` | Catalog + MCP |
| `eval_report`, `eval_history` | Ops |
| `trace_tail`, `trace_file`, `trace_errors` | Ops |
| `db` | Database page (`tables`, `fts`, `path`, `size`) |
| `settings` | Settings form (key set/last4, loop + small model, base URL) |

**Turn card shape** (Loop / Overview / chat telemetry): gate decision, llm_calls (+usage), tools (name/args/output/status), reply, latency, cost. Assistant history `meta`: `gate`, `iterations`, `latency_ms`, `tools`, `model`.

**Session row:** `id`, `title` (first user msg), `messages`, `last`, `last_at`, `sources[]` (`cli`/`dashboard`).

---

## 6. Pages (feature checklist)

Routes should mirror old `#view` / `#view/sub` (`/memory/semantic`, …).

### Overview `/overview`
- Stat tiles: all-time spend, avg latency, turns, tool calls, facts, calendar events.
- Retrieval-gate split (skips vs retrieves) — the hero chart.
- **Live architecture SVG** (clickable nodes → navigate to that pillar). See §8.
- Latest turn card.

### Gateway `/gateway`
- Inbox of **sessions** (not a flat duplicate of the dock).
- Each row: title, channel tags, msg count, last preview/time.
- Click → open that thread in the dock (`session` switch + load history).

### Loop `/loop`
- List of recent turn cards (telemetry + tools + reply).

### Memory `/memory/*`
Subtabs:

| Sub | UI |
|-----|----|
| overview | Counts + short pillar summary |
| semantic | Fact list; inline edit / delete → `POST /api/memory` `update_fact` / `delete_fact` |
| episodic | Episode list; delete |
| skills | Editable bodies; save → `save_skill` (path + content) |
| soul | Full `SOUL.md` textarea; save → `save_soul` |
| consolidation | Pending chat count vs `consolidate_every`; explain batching |

Set `editing=true` while dirty so poll doesn't clobber.

### Tools `/tools/*`
- Results: calendar events + outbox drafts (with **reveal** links → `GET /api/reveal?path=`).
- MCP: servers/tools from `tools.mcp` / catalog.

### Database `/database/*`
- Table browser from `db.tables` (columns, types, counts, sample rows).
- **SQL console:** `POST /api/query` — SELECT / WITH…SELECT only; one statement; show columns+rows or error. Optional query chips that fill the box.

### Ops `/ops`
- Latest eval report + history.
- Usage / cost.
- Trace tail + errors.
- Links/reveal to `.yar/traces/`.

### Compare `/compare`
Largest feature surface — see §9.

### Settings `/settings`
- Current loop model + small (gate/summarizer) model. No provider select — OpenAI only.
- **Your models** card: pins + default (`POST /api/pin`).
- `OPENAI_API_KEY` field + optional base URL (password input; UI only shows set/····last4 — never echo full keys).
- Advanced: manual model ids; catalog from `GET /api/models`.
- **Sole writer:** one `applyModel` / `saveSettings` path → `POST /api/settings` (rebuilds agent in-process). Dock model chip must use the same path.

---

## 7. Chat dock

| Control | Behavior |
|---------|----------|
| New chat | `POST /api/session` `{action:"new"}` → clear local transcript, set `current_session` |
| History | Menu of `sessions`; switch → `{action:"switch", id}` or load history; optional "all history" view |
| stats | Toggle per-turn footer: gate, seconds, iterations, tools (`localStorage`) |
| model chip | Same catalog/pins as Settings; `switchModel` → `/api/settings` |
| Send | Prefer **`POST /api/chat/stream`** |

### Streaming (`/api/chat/stream`)

SSE lines: `data: {json}\n\n`. Kinds:

| `kind` | UI |
|--------|-----|
| `text` | Append `delta` to pending assistant bubble |
| `gate` | Show gate stage (skip/retrieve) |
| `tool` | Show tool name/args/output as stage |
| `llm` | Iteration / usage tick |
| `consolidation` | Optional note |
| `done` | Finalize bubble; stop pending; refetch `/api/data` |

Render assistant text with **escape-first** markdown (`lib/markdown.ts`): escape `&<>` then bold/italic/code/links (`http` + `message:` only)/lists/tables. No sanitizer library.

Chat bubbles may show a stages row while streaming and a telemetry footer when stats is on.

---

## 8. Architecture diagram + live animation

Port the Overview SVG (old `archSVG` + `STAGE` in `diagram.js`).

**Rules:**
- Nodes emit stable `data-node` ids; edges `data-edge` ids.
- Clicking a node navigates to the matching route.
- `GET /api/events?cursor=` (~450ms): new trace events → light up node/edge via a `STAGE` map (`llm`→llm box, `tool`→tools, `gate`→gate, …).
- **Keep SVG ids and STAGE map in the same module** — changing an id without both sides breaks animation.
- Treat the chart as teaching chrome: few arrows, lots of air; detail lives in tabs.

Labels to preserve conceptually: Harness container, Gateway → Working memory → Loop (LLM ↔ Tools) → Reply arc back through gateway; Memory (gate / semantic / episodic / procedural / consolidation / state.db); LLM Ops (trace → evals → release gate).

---

## 9. Compare arena

Isolated from `state.db` (history in `.yar/compare/history.jsonl`).

**Controls:** multi-select OpenAI model ids (pinned + catalog), prompt, toggles for judge / coding, judge model picker, Run.

**Race:** `POST /api/compare/stream` — SSE columns fill as each model finishes (reply, latency, tokens, cost, errors, optional Completion score vs `dataset.jsonl`, judge score).

**Scoreboard:** `GET /api/compare/history` → runs + aggregate; sort; scatter (cost × quality); clear / regrade / delete_run.

**Guards:** don't poll-overwrite mid-race; self-heal history when idle on the tab.

Error UX: map known failures (rate limit, unsupported model id on `chat.completions`, missing key) to short human reasons.

---

## 10. Design tokens (port to Tailwind theme)

Light/dark via `prefers-color-scheme` (or class). Conceptual tokens from the current CSS:

| Token | Role |
|-------|------|
| `--bg`, `--panel`, `--line`, `--line2` | Surfaces / borders |
| `--ink`, `--ink2`, `--ink3` | Text hierarchy |
| `--accent`, `--accent-soft` | Active nav, focus |
| `--good` / `--bad` (+ soft) | Success / error pills |
| `--mono` | Paths, SQL, model ids |

Patterns: sticky pagehead, subtabs with bottom accent, tile grid, scrollable tables with sticky headers, tool/session cards, meta monospace lines. Prefer shadcn + Tailwind equivalents over copying class names blindly — keep the calm teaching look (not a dense SaaS dashboard).

---

## 11. RTL and bilingual UI (Persian + English)

The UI must read correctly in both languages. Waku's cockpit has no `dir` handling at all, so this
is new work, not a port. Backend contract:
[ARCHITECTURE §7](ARCHITECTURE.md#7-language-support-persian-and-english).

**Document level.** `<html lang="fa" dir="rtl">` or `lang="en" dir="ltr"` from a persisted
preference (`localStorage.lang`, default from `navigator.language`). A language toggle sits in
Settings and in the nav.

**Per-content direction — the part that actually matters.** The chrome follows the UI language, but
*content* direction follows the content: a Persian user may store an English fact, and an English
user may get a Persian reply. Put **`dir="auto"`** on every element rendering user or model text —
chat bubbles, fact rows, episode summaries, SOUL/skill textareas, session titles, tool arguments,
trace output. The browser then picks direction from the first strong directional character, per
element, for free. Do not compute direction yourself in JS.

**CSS: logical properties only.** Use `margin-inline-start` / `padding-inline-end` /
`border-inline-start`, `inset-inline`, and `text-align: start | end` — never `left` / `right` — so
one stylesheet serves both directions. In Tailwind that means `ms-*`/`me-*`/`ps-*`/`pe-*` and
`text-start`/`text-end` instead of `ml-*`/`mr-*`/`text-left`/`text-right`. The nav/dock resizers,
the collapse chevrons, and the subtab accent underline all need mirroring; the three-column shell
should swap order under RTL via `flex-direction: row-reverse` or logical grid placement.

**Stays LTR regardless of language** (mirroring these makes them wrong): the architecture SVG,
code and `--mono` spans, SQL console input and results, model ids, file paths, JSON/trace dumps,
numbers and the cost/latency columns. Wrap them in `dir="ltr"` explicitly, even inside an RTL page.

**Fonts.** No webfont dependency. Extend the stack with Persian-capable system faces:
`system-ui, -apple-system, "Segoe UI", Tahoma, "Iranian Sans", "Vazirmatn", sans-serif`. Persian
needs slightly more line-height than Latin at the same size — set `line-height` on the RTL root
rather than per component. Keep `--mono` Latin-only.

**Numbers and dates.** Render digits as ASCII in tables and telemetry (comparable, monospaced);
`Intl.DateTimeFormat` with the active locale for human-facing dates, and Jalali dates come from the
backend rather than being computed in the browser.

**Verify:** switch to Persian and walk every route — punctuation must sit at the correct end of the
line, no horizontal scrollbars, the diagram unmirrored, and a mixed-script chat turn ("جلسه with
Alex فردا") rendering both runs correctly in one bubble.

---

## 12. Vite config essentials

```ts
// vite.config.ts (sketch)
server: {
  proxy: {
    "/api": { target: "http://127.0.0.1:7777", changeOrigin: true },
  },
},
resolve: { alias: { "@": path.resolve(__dirname, "src") } },
```

Then `VITE_API_BASE_URL` can be `""` in dev (same-origin proxy) or the absolute loopback URL in prod preview.

Env via `src/lib/env.ts` only — validate required vars at boot.

---

## 13. Commands & verify

```bash
cd frontend
pnpm install
pnpm dev                 # SPA
pnpm build
pnpm tsc --noEmit
pnpm lint
```

Backend: `cd backend && uv run yar dashboard`.

Manual checklist (no frontend test suite):

1. Every nav route + Memory/Tools/Database subtabs — zero console errors.
2. Chat stream: tokens appear; gate/tool stages show; stats footer toggles.
3. New chat / History / model chip / Settings save all stay in sync.
4. Overview diagram animates during a turn (`/api/events`).
5. Memory edit SOUL → poll doesn't wipe mid-edit.
6. Compare race + scoreboard; Database SELECT.
7. No emojis in UI.
8. Switch to Persian: every route reads correctly RTL, the diagram and code stay LTR, and a
   mixed-script turn renders right (§11).

Restart backend after Python changes; Vite HMR covers SPA edits.

---

## 14. Rebuild order

1. Scaffold Vite React-TS + Tailwind + shadcn + Router + pnpm `.npmrc`.
2. `env` / `http` / `api` / `types` against [api.md](api.md); proxy `/api`.
3. Shell (nav + main + dock chrome, resizers, localStorage).
4. `useDashboardData` poll + Overview tiles (no diagram yet).
5. Chat dock: sessions + `/api/chat/stream` + markdown + stats.
6. Memory / Settings / pin / models (sole settings writer).
7. Loop, Gateway, Tools, Database, Ops pages.
8. Architecture SVG + `/api/events` animation.
9. Compare arena (stream + history).
10. RTL pass (§11): `lang`/`dir`, `dir="auto"` on all content, logical properties. Do this while
    the component count is small — retrofitting `ml-*` → `ms-*` across a finished SPA is miserable.
11. Polish dark mode / empty states.

**Done when:** a newcomer can watch one turn light up the diagram, send a chat, flip Memory/Settings, and run a Compare race — same teaching story as the Waku cockpit, on the document-copilot SPA stack.
