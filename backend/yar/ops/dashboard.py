"""Dashboard — stdlib HTTP server for the Vite SPA. Zero new dependencies.

    make dashboard        # → http://127.0.0.1:7777

Bound to 127.0.0.1 only. Port walks +10 if busy. JSON is UTF-8 with
ensure_ascii=False so Persian is never escaped to \\uXXXX on the wire.

Core routes (this ticket): GET /api/data, POST /api/chat, POST /api/chat/stream,
POST /api/session. Remaining routes land in a later ticket.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from yar.config import load_settings
from yar.db import connect
from yar.ops.tracing import TraceEncodingError, iter_trace_lines

PORT = 7777
# Idle gap (minutes) before a returning dashboard user gets a fresh thread.
# Hardcoded — not a Settings knob yet; matches waku's default of 60.
SESSION_IDLE_MINUTES = 60

# One shared agent for the browser gateway. Built lazily (first chat), reused
# across the threaded server's workers via a cross-thread connection + a lock
# so chats run one at a time — correct for a single-user local tool.
_agent = None
_agent_lock = threading.Lock()
_dashboard_session = None

# Rough $/million tokens (in, out). OpenAI-only — Yar has one provider.
# Provider-level fallback when a model id is unknown.
PRICING = {"openai": (2.5, 15.0)}

# Known per-model prices ($/M in, out). Lifted from waku's date-stamped map
# (OpenAI rows only — other providers are out of scope). Fact-checked Jul 2026.
MODEL_PRICING = {
    # OpenAI rows only — lifted from waku (Jul 2026). Other providers: §13 cut.
    "gpt-5.6-sol": (5.0, 30.0),
    "gpt-5.3-chat-latest": (1.75, 14.0),
}

def price_for(provider: str, model: str) -> tuple[float, float]:
    """$/M tokens (in, out) for one call."""
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]
    return PRICING.get(provider or "openai", (2.5, 15.0))


def usage_summary(home) -> dict:
    """Read the PERMANENT spend ledger (usage.jsonl) → all-time tokens + dollar
    cost, plus per-day and per-provider breakdowns. Cost is derived from tokens
    with PRICING (approximate, labelled 'est'). Survives demo resets."""
    recs = []
    path = Path(home) / "usage.jsonl"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    def cost(r) -> float:
        pin, pout = price_for(r.get("provider", "openai"), r.get("model", ""))
        return r.get("in", 0) / 1e6 * pin + r.get("out", 0) / 1e6 * pout

    def add(bucket, key, extra, r):
        b = bucket.setdefault(key, {**extra, "calls": 0, "in": 0, "out": 0, "cost": 0.0})
        b["calls"] += 1
        b["in"] += r.get("in", 0)
        b["out"] += r.get("out", 0)
        b["cost"] += cost(r)

    by_day, by_provider = {}, {}
    for r in recs:
        day = (r.get("ts") or "")[:10]
        add(by_day, day, {"date": day}, r)
        add(by_provider, r.get("provider", "?"), {"provider": r.get("provider", "?")}, r)

    return {
        "calls": len(recs),
        "total_in": sum(r.get("in", 0) for r in recs),
        "total_out": sum(r.get("out", 0) for r in recs),
        "total_cost": round(sum(cost(r) for r in recs), 4),
        "by_day": sorted(by_day.values(), key=lambda x: x["date"], reverse=True)[:30],
        "by_provider": sorted(by_provider.values(), key=lambda x: -x["cost"]),
    }


def _parse_ts(ts: str):
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def _tool_status(output: str) -> str:
    low = (output or "").lower()
    if "failed" in low or "timed out" in low or low.startswith("error"):
        return "error"
    if "already exists" in low or "not synced" in low or "skipped" in low:
        return "warn"
    return "ok"


def _json_bytes(obj) -> bytes:
    """UTF-8 JSON with Persian (and all non-ASCII) left unescaped."""
    return json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")


def _dash_session() -> str:
    global _dashboard_session
    if _dashboard_session is None:
        try:
            conn = connect(load_settings().home)
            _dashboard_session = _resume_or_new_session(conn)
            conn.close()
        except Exception:
            _dashboard_session = datetime.now().strftime("dashboard-%Y%m%d-%H%M%S")
    return _dashboard_session


def _resume_or_new_session(conn) -> str:
    idle_min = SESSION_IDLE_MINUTES
    row = conn.execute(
        "SELECT session_id, MAX(created_at) AS last_at FROM chat_log "
        "WHERE source='dashboard' GROUP BY session_id "
        "ORDER BY last_at DESC LIMIT 1"
    ).fetchone()
    if row and row["last_at"]:
        try:
            last = datetime.strptime(row["last_at"], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=UTC
            )
            if idle_min <= 0 or (datetime.now(UTC) - last).total_seconds() <= idle_min * 60:
                return row["session_id"]
        except ValueError:
            pass
    return datetime.now().strftime("dashboard-%Y%m%d-%H%M%S")


def _get_agent():
    global _agent, _dashboard_session
    if _agent is None:
        from yar.app import Yar

        settings = load_settings()
        settings.ensure_home()
        conn = connect(settings.home, check_same_thread=False)
        _agent = Yar(settings=settings, conn=conn)
        _dashboard_session = _resume_or_new_session(conn)
        _agent.session.session_id = _dashboard_session
    return _agent


def _maybe_rotate_session(agent) -> None:
    idle_min = SESSION_IDLE_MINUTES
    if idle_min <= 0:
        return
    row = agent.conn.execute(
        "SELECT MAX(created_at) FROM chat_log WHERE session_id=?",
        (agent.session.session_id,),
    ).fetchone()
    if not row or not row[0]:
        return
    try:
        last = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return
    if (datetime.now(UTC) - last).total_seconds() > idle_min * 60:
        agent.session.start_new(datetime.now().strftime("dashboard-%Y%m%d-%H%M%S"))


def chat(message: str, session_id: str | None = None) -> dict:
    """One agent turn → structured JSON for the SPA."""
    events: list[dict] = []
    with _agent_lock:
        agent = _get_agent()
        if session_id:
            agent.session.switch(session_id)
        else:
            _maybe_rotate_session(agent)
        start = datetime.now(UTC)
        result = agent.respond(
            message,
            observer=lambda kind, ev: events.append({"kind": kind, **ev}),
            source="dashboard",
        )
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)

    gate = next((e for e in events if e["kind"] == "gate"), None)
    cons = next((e for e in events if e["kind"] == "consolidation"), None)
    tools = [
        {
            "tool": c["tool"],
            "args": c["args"],
            "output": c["output"],
            "status": _tool_status(c["output"]),
            "summary": (c["output"] or "").split(". ")[0][:120],
        }
        for c in result.tool_calls
    ]
    meta = {
        "gate": {"decision": gate["decision"], "reason": gate.get("reason")} if gate else None,
        "iterations": result.iterations,
        "latency_ms": latency_ms,
        "tools": [c["tool"] for c in result.tool_calls],
        "model": agent.settings.model,
    }
    return {
        "reply": result.reply,
        "tool_calls": tools,
        "iterations": result.iterations,
        "meta": meta,
        "gate": meta["gate"],
        "tools": tools,
        "consolidation": {"new_facts": cons["new_facts"]} if cons else None,
        "latency_ms": latency_ms,
    }


def chat_stream(message: str, emit, session_id: str | None = None) -> None:
    """One turn as SSE: harness events + terminal `done`."""
    events: list[dict] = []

    def observer(kind, ev):
        if kind in ("gate", "consolidation"):
            events.append({"kind": kind, **ev})
        emit(kind, ev)

    with _agent_lock:
        agent = _get_agent()
        if session_id:
            agent.session.switch(session_id)
        else:
            _maybe_rotate_session(agent)
        start = datetime.now(UTC)
        result = agent.respond(message, observer=observer, source="dashboard", stream=True)
        latency_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)

    gate = next((e for e in events if e["kind"] == "gate"), None)
    cons = next((e for e in events if e["kind"] == "consolidation"), None)
    emit(
        "done",
        {
            "reply": result.reply,
            "gate": {"decision": gate["decision"], "reason": gate.get("reason")} if gate else None,
            "tools": [
                {
                    "tool": c["tool"],
                    "args": c["args"],
                    "output": c["output"],
                    "status": _tool_status(c["output"]),
                    "summary": (c["output"] or "").split(". ")[0][:120],
                }
                for c in result.tool_calls
            ],
            "consolidation": {"new_facts": cons["new_facts"]} if cons else None,
            "iterations": result.iterations,
            "latency_ms": latency_ms,
            "model": agent.settings.model,
            "meta": {
                "iterations": result.iterations,
                "latency_ms": latency_ms,
                "tools": [c["tool"] for c in result.tool_calls],
                "model": agent.settings.model,
            },
        },
    )


def _rel_to_home(path, home) -> str:
    try:
        return str(path.resolve().relative_to(home.resolve()))
    except ValueError:
        return str(path)


def session_list(conn) -> list[dict]:
    groups = conn.execute(
        """SELECT session_id, COUNT(*) AS messages, MAX(created_at) AS last_at
           FROM chat_log GROUP BY session_id ORDER BY last_at DESC"""
    ).fetchall()
    out = []
    for g in groups:
        sid = g["session_id"]
        first = conn.execute(
            "SELECT content FROM chat_log WHERE session_id=? AND role='user' ORDER BY id LIMIT 1",
            (sid,),
        ).fetchone()
        last = conn.execute(
            "SELECT role, content FROM chat_log WHERE session_id=? ORDER BY id DESC LIMIT 1",
            (sid,),
        ).fetchone()
        sources = [
            r["source"]
            for r in conn.execute(
                "SELECT DISTINCT source FROM chat_log WHERE session_id=?", (sid,)
            ).fetchall()
        ]
        preview = ""
        if last:
            preview = ("you: " if last["role"] == "user" else "yar: ") + last["content"][:80]
        out.append(
            {
                "id": sid,
                "title": (first["content"][:60] if first else "(empty)"),
                "last": preview,
                "sources": sources,
                "messages": g["messages"],
                "last_at": g["last_at"],
            }
        )
    return out


def _thread_history(conn, sid: str) -> list[dict]:
    rows = conn.execute(
        "SELECT role, content, meta FROM chat_log WHERE session_id=? ORDER BY id",
        (sid,),
    ).fetchall()
    return [
        {
            "role": r["role"],
            "content": r["content"],
            "meta": json.loads(r["meta"]) if r["meta"] else None,
        }
        for r in rows
    ]


def session_action(payload: dict) -> dict:
    """new / switch / history — body uses session_id per api.md."""
    action = payload.get("action")
    sid = payload.get("session_id") or "default"
    if action == "history":
        settings = load_settings()
        settings.ensure_home()
        conn = connect(settings.home)
        return {"ok": True, "session_id": sid, "history": _thread_history(conn, sid)}
    with _agent_lock:
        agent = _get_agent()
        if action == "new":
            new_id = datetime.now().strftime("s-%Y%m%d-%H%M%S")
            agent.session.start_new(new_id)
            return {"ok": True, "session_id": new_id, "history": []}
        if action == "switch":
            agent.session.switch(sid)
            return {"ok": True, "session_id": sid, "history": _thread_history(agent.conn, sid)}
    return {"error": f"unknown action {action}"}


def settings_info() -> dict:
    """Editable knobs for the Settings page — OpenAI only; never echo full keys."""
    s = load_settings()
    key = s.api_key or ""
    return {
        "provider": "openai",
        "model": s.model,
        "small_model": s.small_model,
        "base_url": s.base_url or "",
        "api_key_set": bool(key.strip()),
        "api_key_last4": key[-4:] if key.strip() else "",
        "pinned": [],
        "search_key_env": "TAVILY_API_KEY",
        "search_key_set": bool(os.getenv("TAVILY_API_KEY")),
        "search_key_last4": (os.getenv("TAVILY_API_KEY") or "")[-4:],
    }


_FLAGSHIP = {"create_event", "list_events", "save_note", "send_message"}
_WEB = {"search_web"}
_SELFMGMT = {"manage_memory", "update_soul", "create_skill"}
_EXPERIMENTAL = {"delegate_task", "run_command", "browse_web", "schedule_task"}


def _tool_source(name: str, mcp_servers: list[str]) -> str:
    if name in _FLAGSHIP:
        return "flagship"
    if name in _WEB:
        return "web"
    if name in _SELFMGMT:
        return "self-management"
    if name in _EXPERIMENTAL:
        return "experimental"
    if any(name.startswith(f"{s}_") for s in mcp_servers):
        return "mcp"
    return "other"


def tools_info() -> dict:
    """Registered tool catalog + MCP status for the Tools page.

    When no live agent exists, builds a display-only catalog (no MCP subprocess
    is spawned just to render the page).
    """
    settings = load_settings()
    settings.ensure_home()
    mcp = {"configured": False, "servers": [], "live": False}
    mcp_path = settings.home / "mcp.json"
    if mcp_path.exists():
        mcp["configured"] = True
        try:
            mcp["servers"] = [
                s.get("name", "?")
                for s in json.loads(mcp_path.read_text()).get("servers", [])
            ]
        except (json.JSONDecodeError, OSError):
            pass

    catalog = []
    if _agent is not None:
        mcp["live"] = getattr(_agent, "mcp_bridge", None) is not None
        tools = list(_agent.tools._tools.values())
    else:
        # Display-only: same tools minus MCP (building the real registry would
        # start MCP servers on a poll).
        from yar.tools import calendar, memory_admin, messages, notes, search

        conn = connect(settings.home)
        tools = [
            calendar.make_tool(conn, settings.home),
            calendar.make_list_tool(conn, settings.home),
            notes.make_tool(conn),
            messages.make_tool(settings.home),
            search.make_tool(),
            memory_admin.make_update_soul_tool(settings),
        ]
        try:
            from yar.memory import Memory

            mem = Memory(conn, settings, None)
            tools += [
                memory_admin.make_manage_memory_tool(mem),
                memory_admin.make_create_skill_tool(settings, mem),
            ]
        except Exception:
            pass
        if settings.experimental:
            from yar.tools import experimental

            tools += experimental.make_tools(settings)

    for t in tools:
        catalog.append(
            {
                "name": t.name,
                "description": t.description,
                "source": _tool_source(t.name, mcp["servers"]),
            }
        )
    catalog.sort(key=lambda c: (c["source"], c["name"]))
    from yar.tools.experimental import PLANNED

    return {"catalog": catalog, "mcp": mcp, "planned": PLANNED}


def collect() -> dict:
    """Full dashboard snapshot — the SPA's global `D`."""
    settings = load_settings()
    settings.ensure_home()
    home = settings.home
    conn = connect(home)

    def rows(sql: str) -> list[dict]:
        return [dict(r) for r in conn.execute(sql).fetchall()]

    events = []
    trace_errors = []
    trace_files = sorted((home / "traces").glob("*.jsonl"))
    for path in trace_files:
        try:
            lines = list(iter_trace_lines(path))
        except TraceEncodingError as exc:
            trace_errors.append({"file": path.name, "error": str(exc)})
            continue
        for line in lines:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    turns, current = [], None
    for ev in events:
        kind = ev.get("type")
        if kind == "turn_start":
            current = {
                "user_message": ev.get("user_message"),
                "ts": ev.get("ts"),
                "gate": None,
                "llm_calls": [],
                "tools": [],
                "reply": None,
            }
        elif current is not None:
            if kind == "gate":
                current["gate"] = ev
            elif kind == "llm":
                current["llm_calls"].append(ev)
            elif kind == "tool":
                current["tools"].append(ev)
            elif kind == "consolidation":
                current["consolidation"] = ev
            elif kind == "turn_end":
                current["reply"] = ev.get("reply")
                current["iterations"] = ev.get("iterations")
                turns.append(current)
                current = None
    if current is not None:
        current["reply"] = "TURN NEVER FINISHED — check for a hang after this point"
        current["unfinished"] = True
        turns.append(current)

    price_in, price_out = price_for("openai", settings.model or "")
    for t in turns:
        start, end = _parse_ts(t["ts"]), None
        last = t["llm_calls"][-1]["ts"] if t["llm_calls"] else None
        end = _parse_ts(last)
        t["latency_ms"] = int((end - start).total_seconds() * 1000) if start and end else None
        tin = sum(c.get("usage", {}).get("in", 0) for c in t["llm_calls"])
        tout = sum(c.get("usage", {}).get("out", 0) for c in t["llm_calls"])
        t["cost"] = tin / 1e6 * price_in + tout / 1e6 * price_out
        for x in t["tools"]:
            x["status"] = _tool_status(x.get("output", ""))
            x["summary"] = (x.get("output", "") or "").split(". ")[0][:120]

    latencies = sorted(t["latency_ms"] for t in turns if t["latency_ms"] is not None)
    total_cost = sum(t["cost"] for t in turns)

    def pct(p: float) -> int:
        return latencies[min(len(latencies) - 1, int(len(latencies) * p))] if latencies else 0

    from yar.memory import REPO_SKILLS
    from yar.memory.procedural.loader import SkillLoader

    skills = [
        {
            "name": s.name,
            "description": s.description,
            "body": s.body,
            "path": str(s.path),
            "rel": _rel_to_home(s.path, home),
            "editable": str((home / "skills").resolve()) in str(s.path.resolve()),
        }
        for s in SkillLoader([REPO_SKILLS, home / "skills"]).skills
    ]

    eval_report = None
    report_path = home / "eval_report.json"
    if report_path.exists():
        eval_report = json.loads(report_path.read_text(encoding="utf-8"))

    outbox = [
        {"name": p.name, "text": p.read_text(encoding="utf-8")[:400]}
        for p in sorted((home / "outbox").glob("*.txt"), reverse=True)[:20]
    ]

    def table_info(name):
        info = conn.execute(f"PRAGMA table_info({name})").fetchall()
        cols = [r["name"] for r in info]
        types = {r["name"]: r["type"] for r in info}
        count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        sample = [
            dict(r)
            for r in conn.execute(
                f"SELECT * FROM {name} ORDER BY rowid DESC LIMIT 200"
            ).fetchall()
        ]
        return {"name": name, "columns": cols, "types": types, "count": count, "sample": sample}

    db_path = home / "state.db"
    all_tables = [
        r["name"]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]
    db_info = {
        "path": str(db_path.resolve()),
        "size": db_path.stat().st_size if db_path.exists() else 0,
        "tables": [table_info(n) for n in ("calendar_events", "facts", "episodes", "chat_log")],
        "fts": [t for t in all_tables if t.endswith("_fts")],
        "all_tables": all_tables,
    }

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "home": str(home.resolve()),
        "provider": "openai",
        "model": settings.model,
        "stats": {
            "turns": len(turns),
            "tool_calls": sum(len(t["tools"]) for t in turns),
            "tool_errors": sum(1 for t in turns for x in t["tools"] if x["status"] == "error"),
            "gate_skips": sum(
                1 for t in turns if t["gate"] and t["gate"].get("decision") == "skip"
            ),
            "gate_retrieves": sum(
                1 for t in turns if t["gate"] and t["gate"].get("decision") == "retrieve"
            ),
            "tokens_in": sum(
                c.get("usage", {}).get("in", 0) for t in turns for c in t["llm_calls"]
            ),
            "tokens_out": sum(
                c.get("usage", {}).get("out", 0) for t in turns for c in t["llm_calls"]
            ),
            "cost": round(total_cost, 4),
            "latency_avg": int(sum(latencies) / len(latencies)) if latencies else 0,
            "latency_p95": pct(0.95),
            "trace_files": len(trace_files),
        },
        "turns": turns[::-1][:50],
        "trace_tail": [
            {
                "type": e.get("type"),
                "ts": e.get("ts"),
                "detail": (
                    e.get("user_message")
                    or e.get("decision")
                    or e.get("tool")
                    or e.get("reply")
                    or ""
                ),
            }
            for e in events[-18:]
        ][::-1],
        "trace_file": (trace_files[-1].name if trace_files else None),
        "trace_errors": trace_errors,
        "facts": rows(
            "SELECT id, subject, content, source, created_at FROM facts ORDER BY id DESC"
        ),
        "episodes": rows(
            "SELECT id, happened_at, summary FROM episodes ORDER BY happened_at DESC"
        ),
        "soul": (home / "SOUL.md").read_text(encoding="utf-8")
        if (home / "SOUL.md").exists()
        else "",
        "chat_pending": conn.execute(
            "SELECT COUNT(*) FROM chat_log WHERE consolidated=0"
        ).fetchone()[0],
        "chat_log": rows(
            "SELECT role, content, consolidated, source, session_id, meta, created_at "
            "FROM chat_log ORDER BY id DESC LIMIT 80"
        )[::-1],
        "sessions": session_list(conn),
        "current_session": (
            _agent.session.session_id if _agent is not None else _dash_session()
        ),
        "consolidate_every": settings.consolidate_every,
        "calendar": rows(
            'SELECT title, start, "end", attendees, created_at '
            "FROM calendar_events ORDER BY start"
        ),
        "outbox": outbox,
        "skills": skills,
        "eval_report": eval_report,
        "db": db_info,
        "settings": settings_info(),
        "tools": tools_info(),
        "usage": usage_summary(home),
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, ctype: str, *, no_cache: bool = False) -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if no_cache:
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        # Local SPA on another origin (Vite) — allow during development.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):  # noqa: N802
        if self.path == "/api/data" or self.path.startswith("/api/data?"):
            self._send(_json_bytes(collect()), "application/json; charset=utf-8")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        if self.path == "/api/chat/stream":
            payload = json.loads(self.rfile.read(length) or b"{}")
            message = (payload.get("message") or "").strip()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            def emit(kind, ev):
                try:
                    payload_out = {"kind": kind, **ev}
                    line = json.dumps(payload_out, ensure_ascii=False, default=str)
                    self.wfile.write(f"data: {line}\n\n".encode())
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            if not message:
                emit("done", {"error": "empty message"})
                return
            try:
                chat_stream(message, emit, session_id=payload.get("session_id"))
            except Exception as exc:
                emit("done", {"error": f"{type(exc).__name__}: {exc}"})
            return

        routes = {
            "/api/chat": None,
            "/api/session": session_action,
        }
        if self.path not in routes:
            self.send_response(404)
            self.end_headers()
            return
        payload = json.loads(self.rfile.read(length) or b"{}")
        try:
            if self.path == "/api/chat":
                message = (payload.get("message") or "").strip()
                out = (
                    chat(message, session_id=payload.get("session_id"))
                    if message
                    else {"error": "empty message"}
                )
            else:
                out = routes[self.path](payload)
        except Exception as exc:
            out = {"error": f"{type(exc).__name__}: {exc}"}
        self._send(_json_bytes(out), "application/json; charset=utf-8")

    def log_message(self, *args):
        pass


def main() -> None:
    # Port precedence: YAR_DASHBOARD_PORT, then PORT, then 7777. Walk +10 if busy.
    base = int(os.getenv("YAR_DASHBOARD_PORT") or os.getenv("PORT") or PORT)
    for port in range(base, base + 10):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        except OSError:
            print(f"port {port} busy, trying {port + 1}…")
            continue
        print(f"Yar dashboard → http://127.0.0.1:{port}  (Ctrl-C to stop)")
        server.serve_forever()
        return
    raise SystemExit(f"no free port in {base}–{base + 9}")


if __name__ == "__main__":
    main()
