# yar-agent — Backend API

Contract the Vite SPA (and any other client) talks to. Implemented by
`backend/yar/ops/dashboard.py` — stdlib `http.server`, bound to **`127.0.0.1` only**.
Default port **7777** (`YAR_DASHBOARD_PORT` / `PORT`); if busy, walk +10.

Reverse-engineered from `waku/ops/dashboard.py` in
[waku-agent](https://github.com/ShenSeanChen/waku-agent) (`main` @
[`871c4ac`](https://github.com/ShenSeanChen/waku-agent/tree/871c4ac)) — go there for exact
field-level payloads and for the per-model price map behind every `cost` field.

All JSON bodies use `Content-Type: application/json` unless noted. Errors are usually
`{"error": "…"}` with a non-2xx status.

**Text is UTF-8 and may be Persian, English, or both in one field.** Serialize with
`ensure_ascii=False` and send `charset=utf-8` on every response; never escape non-ASCII into
`\uXXXX`. The server normalizes Persian letter and digit variants on the way into searchable
storage (see [ARCHITECTURE §7](ARCHITECTURE.md#7-language-support-persian-and-english)),
so clients send raw user text and do no folding of their own. Responses carry no direction hints —
the SPA relies on `dir="auto"`.

---

## Route table

| Method | Path | Role |
|--------|------|------|
| GET | `/api/data` | Full dashboard snapshot (the SPA's global `D`) |
| GET | `/api/compare/history` | Model-arena scoreboard |
| GET | `/api/models` | Live OpenAI model catalog + defaults |
| GET | `/api/events?cursor=` | Trace tail since cursor (live animation) |
| GET | `/api/reveal?path=` | Open a path under `.yar/` in the OS (editor/Finder) |
| POST | `/api/chat` | One agent turn → JSON reply |
| POST | `/api/chat/stream` | One turn as SSE (token + harness events) |
| POST | `/api/compare` | Race several models on one prompt |
| POST | `/api/compare/stream` | Same race as SSE |
| POST | `/api/compare/clear` | Clear arena history |
| POST | `/api/compare/regrade` | Re-run judges on stored runs |
| POST | `/api/compare/delete_run` | Delete one arena run |
| POST | `/api/memory` | CRUD on SOUL / skills / facts / episodes |
| POST | `/api/settings` | Change models / API key; rewrite `.env` + rebuild agent |
| POST | `/api/query` | Read-only SQL against `state.db` |
| POST | `/api/session` | `new` / `switch` / `history` |
| POST | `/api/pin` | Pin / unpin / set default model |

CORS: local SPA on another origin (Vite) needs the server to allow it, or proxy through Vite
during `pnpm dev`. Prefer a Vite `server.proxy` to `127.0.0.1:7777` so the browser stays same-origin.

---

## GET `/api/data`

Returns one JSON object — the SPA polls this (~5s). Top-level keys (rebuild must preserve):

| Key | Meaning |
|-----|---------|
| `model`, `home` | Active model + runtime home path |
| `stats` | Aggregates: turns, tool_errors, tokens, … |
| `chat_log` / `turns` | Recent messages (role, content, session_id, source, meta) |
| `facts`, `episodes` | Semantic + episodic rows |
| `soul` | Current `SOUL.md` text |
| `skills` | Installed/repo skills (name, description, body path) |
| `calendar`, `outbox` | Flagship artifacts |
| `sessions`, `current_session` | Session ids + active one |
| `eval_report` | Latest `make gate` verdict (or null) |
| `db` | Table list + counts for the Database page |
| `settings` | Editable knobs for Settings page |
| `tools` | Registered tool names/schemas |
| `usage` | Recent spend ledger summary |

Assistant `meta` (JSON on the chat row) typically includes: `gate` (skip\|retrieve + reason),
`iterations`, `latency_ms`, `tools` (name list), `model`.

`chat_log` / session `source` is `cli` or `dashboard` — those are the only two gateways.

---

## Chat

### POST `/api/chat`
Body: `{ "message": "…", "session_id"?: "…" }`  
Response: `{ "reply": "…", "tool_calls": [...], "iterations": N, "meta": {...} }`

### POST `/api/chat/stream`
Same body. Response: **SSE** (`text/event-stream`). Each event:

```
data: {"kind":"text"|"gate"|"tool"|"llm"|"consolidation"|"done", ...}\n\n
```

- `text` — `{ "delta": "…" }` token chunk  
- `gate` / `tool` / `llm` / `consolidation` — harness observer payloads  
- `done` — terminal; includes final reply / meta  

---

## Memory / settings / session / pin / query

### POST `/api/memory`
Body: `{ "action": "…", … }`  
Actions: `save_soul` (`text`), `save_skill` (`name`, `description`, `body`), `update_fact`
(`id`, `content`/`subject`), `delete_fact` (`id`), `delete_episode` (`id`).

### POST `/api/settings`
Body: loop model, small (gate/summarizer) model, `OPENAI_API_KEY`, optional `YAR_BASE_URL`.
Rewrites `.env`, rebuilds the in-process agent. Requires server restart awareness: Python holds
the agent in memory; this path rebuilds it. There is no provider field — OpenAI is the only one.
Never echo a stored key back; return set/unset plus the last 4 characters.

### POST `/api/session`
Body: `{ "action": "new"|"switch"|"history", "session_id"?: "…" }`  
- `new` — mint session id, clear working memory  
- `switch` — load that session's `chat_log` into history  
- `history` — return messages for a session (`role`/`content`/`meta`)

### POST `/api/pin`
Body: `{ "action": "pin"|"unpin"|"default", "id": "<model-id>" }`  
Persists to `.yar/models.json`.

### POST `/api/query`
Body: `{ "sql": "SELECT …" }` — **read-only**; reject writes. Returns `{ "rows": [...], "columns": [...] }`.

---

## Compare arena

Runs are stored in `.yar/compare/history.jsonl` (max ~50) — **never** in `state.db` (sandbox
isolation: a race must not pollute the user's real memory).

### POST `/api/compare` / `/api/compare/stream`
Body: `{ "message": "…", "models": ["<model-id>", …], … }` — OpenAI model ids racing each other.  
Each contestant gets an isolated temp home for the turn. Stream emits per-model results plus
optional `judge` / `coding` events. History endpoints return the aggregated scoreboard.

Also: `POST /api/compare/clear`, `/api/compare/regrade`, `/api/compare/delete_run`.

---

## Reveal, events & models

### GET `/api/reveal?path=`
Opens a path that must resolve under `.yar/` (or other allowed roots). No body.

### GET `/api/events?cursor=`
Returns new JSONL trace events since `cursor` for the live architecture animation.

### GET `/api/models`
Live catalog from OpenAI's models endpoint plus the configured defaults and pins from
`.yar/models.json`. On a catalog fetch failure, return the defaults and an `error` field rather
than an empty list.
