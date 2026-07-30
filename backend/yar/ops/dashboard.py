"""Dashboard — stdlib HTTP server for the Vite SPA. Zero new dependencies.

    make dashboard        # → http://127.0.0.1:7777

Bound to 127.0.0.1 only. Port walks +10 if busy. JSON is UTF-8 with
ensure_ascii=False so Persian is never escaped to \\uXXXX on the wire.

Full route table: docs/api.md — chat, session, memory, settings, pin, query,
models, reveal, events, compare (isolated temp homes; history outside state.db).
"""

from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from yar.config import Settings, load_settings
from yar.db import connect
from yar.ops import compare_history
from yar.ops import judge as judge_mod
from yar.ops import scoring
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
_models_cache: dict[str, tuple] = {}

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


def _normalize_spec(spec: str) -> tuple[str, str, str]:
    """Model ids only (api.md); accept optional openai: prefix for convenience."""
    raw = (spec or "").strip()
    if ":" in raw:
        provider, _, model = raw.partition(":")
        if provider == "openai" and model:
            return f"openai:{model}", "openai", model
    return f"openai:{raw}", "openai", raw


def _compare_one(message: str, spec: str) -> dict:
    """One contestant in an isolated temp home — never touches real memory."""
    import tempfile
    import time

    from yar.app import Yar

    full_spec, provider, model = _normalize_spec(spec)
    home = Path(tempfile.mkdtemp(prefix="compare-openai-"))
    gate: dict = {}
    try:
        settings = Settings(
            model=model,
            small_model="",
            home=home,
            api_key=load_settings().api_key,
            base_url=load_settings().base_url,
        )
        app = Yar(settings=settings)

        def obs(kind, ev):
            if kind == "gate":
                gate.update(decision=ev.get("decision"), reason=ev.get("reason"))

        t0 = time.perf_counter()
        result = app.respond(message, source="compare", observer=obs)
        ms = int((time.perf_counter() - t0) * 1000)
        tin = tout = 0
        ledger = home / "usage.jsonl"
        if ledger.exists():
            for line in ledger.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(line)
                    tin, tout = tin + r.get("in", 0), tout + r.get("out", 0)
                except json.JSONDecodeError:
                    pass
        pin, pout = price_for(provider, settings.model)
        return {
            "spec": full_spec,
            "provider": provider,
            "model": settings.model,
            "reply": result.reply,
            "gate": (gate or None),
            "iterations": result.iterations,
            "latency_ms": ms,
            "tools": [{"tool": c["tool"]} for c in result.tool_calls],
            "tokens_in": tin,
            "tokens_out": tout,
            "cost_usd": round(tin / 1e6 * pin + tout / 1e6 * pout, 4),
        }
    except (Exception, SystemExit) as exc:
        return {
            "spec": full_spec,
            "provider": provider,
            "model": model,
            "error": str(exc)[:200],
        }


def compare_models(payload: dict) -> dict:
    """Race one message through several OpenAI model ids (non-streaming)."""
    from concurrent.futures import ThreadPoolExecutor

    message = (payload.get("message") or "").strip()
    specs = payload.get("models") or []
    if not message or not specs:
        return {"error": "message and models required"}
    with ThreadPoolExecutor(max_workers=min(len(specs), 6)) as ex:
        results = list(ex.map(lambda s: _compare_one(message, s), specs))
    return {"ok": True, "message": message, "results": results}


def compare_stream(
    message: str,
    specs: list,
    emit,
    judge: bool = False,
    judge_model: str = "",
) -> None:
    """Race models with live harness SSE; each contestant gets a temp home."""
    import tempfile
    import time
    from concurrent.futures import ThreadPoolExecutor

    from yar.app import Yar

    if not message or not specs:
        emit("done", {"error": "message and models required"})
        return

    lock = threading.Lock()
    collected: list = []
    case = scoring.case_for_message(message)
    base = load_settings()

    def send(kind, ev):
        with lock:
            emit(kind, ev)
            if kind == "result":
                collected.append(ev)

    def run(spec):
        full_spec, provider, model = _normalize_spec(spec)
        send("start", {"spec": full_spec, "provider": provider, "model": model})
        home = Path(tempfile.mkdtemp(prefix="compare-openai-"))
        gate: dict = {}

        def obs(kind, ev):
            if kind == "gate":
                gate.update(decision=ev.get("decision"), reason=ev.get("reason"))
                send(
                    "gate",
                    {
                        "spec": full_spec,
                        "decision": ev.get("decision"),
                        "reason": ev.get("reason"),
                    },
                )
            elif kind == "tool":
                send("tool", {"spec": full_spec, "tool": ev.get("tool")})

        try:
            settings = Settings(
                model=model,
                small_model="",
                home=home,
                api_key=base.api_key,
                base_url=base.base_url,
            )
            app = Yar(settings=settings)
            if case and case.get("setup_fact"):
                app.memory.facts.add(
                    case["setup_fact"]["subject"], case["setup_fact"]["content"]
                )
            t0 = time.perf_counter()
            result = app.respond(message, source="compare", observer=obs)
            ms = int((time.perf_counter() - t0) * 1000)
            tin = tout = 0
            ledger = home / "usage.jsonl"
            if ledger.exists():
                for line in ledger.read_text(encoding="utf-8").splitlines():
                    try:
                        r = json.loads(line)
                        tin, tout = tin + r.get("in", 0), tout + r.get("out", 0)
                    except json.JSONDecodeError:
                        pass
            pin, pout = price_for(provider, settings.model)
            cost = round(tin / 1e6 * pin + tout / 1e6 * pout, 4)
            completion = None
            if case:
                passed, why = scoring.check_case(case, result.tool_calls)
                completion = {"passed": passed, "why": why, "case": case["id"]}
            send(
                "result",
                {
                    "spec": full_spec,
                    "provider": provider,
                    "model": settings.model,
                    "reply": result.reply,
                    "gate": (gate or None),
                    "iterations": result.iterations,
                    "latency_ms": ms,
                    "tools": [{"tool": c["tool"]} for c in result.tool_calls],
                    "tokens_in": tin,
                    "tokens_out": tout,
                    "cost_usd": cost,
                    "completion": completion,
                    "quality": None,
                },
            )
        except (Exception, SystemExit) as exc:
            send(
                "result",
                {
                    "spec": full_spec,
                    "provider": provider,
                    "model": model,
                    "error": str(exc)[:200],
                },
            )

    with ThreadPoolExecutor(max_workers=min(len(specs), 6)) as ex:
        list(ex.map(run, specs))

    if judge:
        jm = (judge_model or "").strip() or None
        gradable = [
            r for r in collected if not r.get("error") and (r.get("reply") or "").strip()
        ]
        emit("grading", {"n": len(gradable), "judge": jm or judge_mod.JUDGE_MODEL})

        def grade(r):
            if r.get("error") or not (r.get("reply") or "").strip():
                return
            q = judge_mod.judge_reply(
                message,
                r["reply"],
                model=jm,
                tools=[t.get("tool") for t in (r.get("tools") or [])],
            )
            r["quality"] = q
            send("grade", {"spec": r.get("spec"), "quality": q})

        with ThreadPoolExecutor(max_workers=2) as jex:
            list(jex.map(grade, list(collected)))

    try:
        compare_history.append_run(load_settings().home, message, collected)
    except Exception:
        pass
    emit("done", {})


def compare_clear(payload: dict) -> dict:
    compare_history.clear(load_settings().home)
    return {"ok": True, "runs": [], "aggregate": []}


def _compare_history_response(runs: list[dict]) -> dict:
    for run in runs:
        for r in run.get("results", []):
            if r.get("error"):
                continue
            pin, pout = price_for(r.get("provider", "openai"), r.get("model", ""))
            r["cost_usd"] = round(
                (r.get("tokens_in") or 0) / 1e6 * pin
                + (r.get("tokens_out") or 0) / 1e6 * pout,
                4,
            )
    agg = compare_history.aggregate(runs)
    for row in agg:
        row["rate_in"], row["rate_out"] = price_for(
            row.get("provider") or "openai", row.get("model") or ""
        )
    return {"runs": runs[-20:][::-1], "aggregate": agg}


def compare_regrade(payload: dict) -> dict:
    home = load_settings().home
    runs = compare_history.load_runs(home)
    if not runs:
        return {"runs": [], "aggregate": []}
    only_missing = payload.get("only_missing", True)
    spec = payload.get("spec")
    jm = (payload.get("judge_model") or "").strip() or None
    last = runs[-1]
    for r in last.get("results", []):
        if r.get("error") or not (r.get("reply") or "").strip():
            continue
        if spec is not None and r.get("spec") != spec:
            continue
        if spec is None and only_missing and r.get("quality") is not None:
            continue
        q = judge_mod.judge_reply(
            last.get("message", ""),
            r["reply"],
            model=jm,
            tools=r.get("tools"),
        )
        if q is not None:
            r["quality"] = q
    compare_history.save_runs(home, runs)
    return _compare_history_response(runs)


def compare_delete_run(payload: dict) -> dict:
    home = load_settings().home
    ts = payload.get("ts")
    runs = [r for r in compare_history.load_runs(home) if r.get("ts") != ts]
    compare_history.save_runs(home, runs)
    return _compare_history_response(runs)


def run_query(payload: dict) -> dict:
    """Read-only SQL against state.db — SELECT / WITH only, one statement."""
    sql = (payload.get("sql") or "").strip().rstrip(";").strip()
    if not sql:
        return {"error": "Type a SELECT query."}
    low = sql.lower()
    if not (low.startswith("select") or low.startswith("with")):
        return {"error": "Only SELECT (or WITH … SELECT) queries are allowed."}
    if ";" in sql:
        return {"error": "One statement at a time (no semicolons)."}
    import sqlite3

    settings = load_settings()
    settings.ensure_home()
    db = (settings.home / "state.db").resolve()
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        c.row_factory = sqlite3.Row
        cur = c.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        data = [
            [str(r[i]) if r[i] is not None else "" for i in range(len(cols))]
            for r in cur.fetchmany(200)
        ]
        c.close()
        return {"columns": cols, "rows": data}
    except sqlite3.Error as exc:
        return {"error": str(exc)}


def _editor_cmd() -> list[str] | None:
    """User's editor CLI: $YAR_EDITOR, then cursor, then code."""
    import shutil

    custom = os.getenv("YAR_EDITOR")
    if custom and shutil.which(custom):
        return [custom]
    for cli in ("cursor", "code"):
        if shutil.which(cli):
            return [cli]
    return None


def reveal_path(rel: str) -> dict:
    """Open a path under .yar/ in the OS editor (or Finder on macOS)."""
    import subprocess
    import sys

    settings = load_settings()
    settings.ensure_home()
    home = settings.home.resolve()
    target = (home / (rel or ".")).resolve()
    if target != home and home not in target.parents:
        return {"error": "path is outside the .yar home"}
    if not target.exists():
        return {"error": f"not found: {target}"}

    editor = _editor_cmd()
    if editor and target.is_file() and target.suffix != ".db":
        subprocess.run([*editor, str(target)], check=False)
        return {"ok": True, "opened_in": editor[0], "path": str(target)}
    if sys.platform != "darwin":
        return {"error": f"no editor found and reveal is macOS-only — the path is {target}"}
    subprocess.run(
        ["open", "-R", str(target)] if target.is_file() else ["open", str(target)],
        check=False,
    )
    return {"ok": True, "revealed": str(target)}


def memory_action(payload: dict) -> dict:
    """CRUD on SOUL / skills / facts / episodes from the dashboard."""
    from yar.memory.episodic.store import SqliteEpisodeStore
    from yar.memory.semantic.store import SqliteFactStore

    settings = load_settings()
    settings.ensure_home()
    action = payload.get("action")
    if action == "save_soul":
        text = (payload.get("text") or payload.get("content") or "").strip()
        if not text:
            return {"error": "SOUL cannot be empty"}
        (settings.home / "SOUL.md").write_text(text + "\n", encoding="utf-8")
        return {"ok": True}
    if action == "save_skill":
        # SPA edits by path+content (frontend.md); api.md also allows name/description/body.
        # Writes always land in .yar/skills/ — never mutate packaged built-ins.
        path_raw = payload.get("path")
        content = (payload.get("content") or "").strip()
        if path_raw:
            from yar.memory import REPO_SKILLS
            from yar.memory.procedural.loader import _parse_text

            requested = Path(path_raw).resolve()
            home_skills = (settings.home / "skills").resolve()
            allowed = [REPO_SKILLS.resolve(), home_skills]
            if requested.name != "SKILL.md" or not any(
                a in requested.parents for a in allowed
            ):
                return {"error": "can only edit SKILL.md files inside the skills folders"}
            if _parse_text(content, requested) is None:
                return {
                    "error": "invalid SKILL.md — needs a name and description in the frontmatter"
                }
            # Built-in path → home override; home path stays put. Parent folder = slug.
            dest = home_skills / requested.parent.name / "SKILL.md"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content.rstrip() + "\n", encoding="utf-8")
            return {"ok": True}
        name = (payload.get("name") or "").strip().lower().replace(" ", "-")
        description = (payload.get("description") or "").strip()
        body = (payload.get("body") or "").strip()
        if not name or not description:
            return {"error": "save_skill needs name+description+body or path+content"}
        from yar.memory.procedural.loader import _parse_text
        from yar.tools.memory_admin import _SLUG

        if not _SLUG.match(name):
            return {"error": "skill name must be a short slug like 'weekly-review'"}
        dest = settings.home / "skills" / name / "SKILL.md"
        text = f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n"
        if _parse_text(text, dest) is None:
            return {"error": "invalid skill — description must be present and non-trivial"}
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        return {"ok": True}

    conn = connect(settings.home)
    facts, episodes = SqliteFactStore(conn), SqliteEpisodeStore(conn)
    try:
        rid = int(payload.get("id", 0))
    except (TypeError, ValueError):
        return {"error": "bad id"}
    if action == "update_fact":
        return {
            "ok": facts.update(
                rid, payload.get("content", ""), payload.get("subject") or None
            )
        }
    if action == "delete_fact":
        return {"ok": facts.delete(rid)}
    if action == "delete_episode":
        return {"ok": episodes.delete(rid)}
    return {"error": f"unknown action {action}"}


def _known_default_models(out: dict) -> list[dict]:
    ids = [out.get("model"), out.get("small_model"), "gpt-5.3-chat-latest", "gpt-4.1-mini"]
    return [{"id": m} for m in dict.fromkeys(m for m in ids if m)]


def list_models() -> dict:
    """Live OpenAI-compatible catalog + defaults/pins. On failure, defaults + error."""
    import time
    import urllib.request

    s = load_settings()
    base = (s.base_url or "").rstrip("/")
    out = {
        "model": s.model,
        "small_model": s.small_model,
        "endpoint": base or "openai",
        "pinned": pinned_ids(),
    }
    if not base:
        return {**out, "listed": False, "models": _known_default_models(out)}

    url = base + "/models"
    cached = _models_cache.get(url)
    if cached and time.time() - cached[0] < 300:
        _ts, cmodels, cerr = cached
        r = {**out, "listed": cerr is None, "models": cmodels}
        if cerr:
            r["error"] = cerr
        return r

    key = (s.api_key or "").strip()
    try:
        key.encode("latin-1")
    except UnicodeEncodeError:
        msg = "OPENAI_API_KEY contains a non-ASCII character — re-paste the key."
        return {
            **out,
            "listed": False,
            "models": _known_default_models(out),
            "error": msg,
        }

    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        msg = str(exc)
        try:
            msg = f"{msg} — {exc.read().decode()[:160]}"  # type: ignore[attr-defined]
        except Exception:
            pass
        known = _known_default_models(out)
        _models_cache[url] = (time.time() - 240, known, msg)
        return {**out, "listed": False, "models": known, "error": msg}

    models = []
    for m in data.get("data", []):
        mid = m.get("id", "")
        if mid:
            models.append({"id": mid})
    models.sort(key=lambda x: x["id"])
    _models_cache[url] = (time.time(), models, None)
    return {**out, "listed": True, "models": models}


def _models_json() -> Path:
    return load_settings().home / "models.json"


def pinned_ids() -> list[str]:
    """Curated model-id shortlist from .yar/models.json."""
    p = _models_json()
    if p.exists():
        try:
            return list(json.loads(p.read_text(encoding="utf-8")).get("pinned", []))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def pin_action(payload: dict) -> dict:
    """pin / unpin / default — persists model ids to .yar/models.json."""
    action = payload.get("action")
    mid = (payload.get("id") or payload.get("model") or "").strip()
    if not mid:
        return {"error": "id required"}
    specs = [s for s in pinned_ids() if s != mid]
    if action == "pin":
        specs.append(mid)
    elif action == "default":
        specs.insert(0, mid)
    elif action != "unpin":
        return {"error": f"unknown action {action}"}
    path = _models_json()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pinned": specs}, indent=1) + "\n", encoding="utf-8")
    return {"ok": True, **settings_info()}


def apply_settings(payload: dict) -> dict:
    """Rewrite .env + os.environ, rebuild the in-process agent. OpenAI only."""
    global _agent
    from dotenv import find_dotenv, set_key

    # Reject a provider picker — Yar is OpenAI-only.
    if "provider" in payload and payload["provider"] not in (None, "", "openai"):
        return {"error": "Yar supports OpenAI only — no provider field"}

    before_settings = load_settings()
    before = {
        "model": before_settings.model,
        "small_model": before_settings.small_model,
        "base_url": before_settings.base_url or "",
    }
    writable = {
        "YAR_MODEL",
        "YAR_SMALL_MODEL",
        "YAR_BASE_URL",
        "OPENAI_API_KEY",
        "YAR_API_KEY",
        "TAVILY_API_KEY",
    }
    env_path = find_dotenv(usecwd=True) or ".env"

    updates: dict[str, str] = {}
    if "model" in payload:
        updates["YAR_MODEL"] = payload.get("model") or ""
    if "small_model" in payload:
        updates["YAR_SMALL_MODEL"] = payload.get("small_model") or ""
    if "base_url" in payload and payload.get("base_url") is not None:
        updates["YAR_BASE_URL"] = payload.get("base_url") or ""
    api_key = payload.get("api_key") or payload.get("OPENAI_API_KEY")
    if api_key:
        updates["OPENAI_API_KEY"] = api_key
    for k, v in (payload.get("keys") or {}).items():
        if k in writable and v:
            updates[k] = v

    for k, v in updates.items():
        if k in writable:
            set_key(env_path, k, v)
            os.environ[k] = v

    with _agent_lock:
        old = _agent
        try:
            new_settings = load_settings()
            new_settings.ensure_home()
            conn = connect(new_settings.home, check_same_thread=False)
            from yar.app import Yar

            _agent = Yar(settings=new_settings, conn=conn)
        except (Exception, SystemExit) as exc:
            _agent = old
            return {"error": str(exc)}
    if old is not None:
        old.close()
    if _agent is not None:
        _agent.tracer.event(
            "config",
            {
                "from": before,
                "to": {
                    "model": updates.get("YAR_MODEL", before["model"]),
                    "small_model": updates.get("YAR_SMALL_MODEL", before["small_model"]),
                    "base_url": updates.get("YAR_BASE_URL", before["base_url"]),
                },
            },
        )
    return {"ok": True, **settings_info()}


def events_since(cursor):
    """New JSONL trace events past cursor (line count in today's file)."""
    settings = load_settings()
    settings.ensure_home()
    path = settings.home / "traces" / (datetime.now().strftime("%Y-%m-%d") + ".jsonl")
    if not path.exists():
        return {"events": [], "cursor": 0}
    try:
        lines = list(iter_trace_lines(path))
    except TraceEncodingError as exc:
        return {"events": [], "cursor": 0, "error": str(exc)}
    if cursor is None or cursor < 0 or cursor > len(lines):
        return {"events": [], "cursor": len(lines)}
    out = []
    for ln in lines[cursor:]:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    return {"events": out, "cursor": len(lines)}


def settings_info() -> dict:
    """Editable knobs for the Settings page — OpenAI only; never echo full keys."""
    s = load_settings()
    key = s.api_key or ""
    pinned = pinned_ids()
    return {
        "model": s.model,
        "small_model": s.small_model,
        "base_url": s.base_url or "",
        "api_key_set": bool(key.strip()),
        "api_key_last4": key[-4:] if key.strip() else "",
        "pinned": [
            {"id": mid, "default": i == 0} for i, mid in enumerate(pinned)
        ],
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

    # SPA Save always writes under .yar/skills — advertise that absolute path even
    # for built-ins (body still comes from whichever copy is loaded).
    home_skills = (home / "skills").resolve()
    skills = []
    for s in SkillLoader([REPO_SKILLS, home / "skills"]).skills:
        slug = s.path.parent.name
        dest = home_skills / slug / "SKILL.md"
        skills.append(
            {
                "name": s.name,
                "description": s.description,
                "body": s.body,
                "path": str(dest),
                "rel": f"skills/{slug}/SKILL.md",
                "editable": home_skills in s.path.resolve().parents,
            }
        )

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
        elif self.path == "/api/compare/history" or self.path.startswith(
            "/api/compare/history?"
        ):
            runs = compare_history.load_runs(load_settings().home)
            self._send(
                _json_bytes(_compare_history_response(runs)),
                "application/json; charset=utf-8",
            )
        elif self.path.startswith("/api/models"):
            self._send(_json_bytes(list_models()), "application/json; charset=utf-8")
        elif self.path.startswith("/api/events"):
            raw = parse_qs(urlparse(self.path).query).get("cursor", [None])[0]
            cursor = int(raw) if raw and raw.lstrip("-").isdigit() else None
            self._send(
                _json_bytes(events_since(cursor)), "application/json; charset=utf-8"
            )
        elif self.path.startswith("/api/reveal"):
            rel = unquote(parse_qs(urlparse(self.path).query).get("path", [""])[0])
            self._send(
                _json_bytes(reveal_path(rel)), "application/json; charset=utf-8"
            )
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

        if self.path == "/api/compare/stream":
            payload = json.loads(self.rfile.read(length) or b"{}")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            def emit_cmp(kind, ev):
                try:
                    line = json.dumps(
                        {"kind": kind, **ev}, ensure_ascii=False, default=str
                    )
                    self.wfile.write(f"data: {line}\n\n".encode())
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            try:
                compare_stream(
                    (payload.get("message") or "").strip(),
                    payload.get("models") or [],
                    emit_cmp,
                    judge=bool(payload.get("judge")),
                    judge_model=payload.get("judge_model") or "",
                )
            except Exception as exc:
                emit_cmp("done", {"error": f"{type(exc).__name__}: {exc}"})
            return

        routes = {
            "/api/chat": None,
            "/api/session": session_action,
            "/api/memory": memory_action,
            "/api/settings": apply_settings,
            "/api/query": run_query,
            "/api/pin": pin_action,
            "/api/compare": compare_models,
            "/api/compare/clear": compare_clear,
            "/api/compare/regrade": compare_regrade,
            "/api/compare/delete_run": compare_delete_run,
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
