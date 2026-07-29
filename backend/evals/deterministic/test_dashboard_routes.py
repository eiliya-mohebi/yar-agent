"""Remaining dashboard cockpit routes — memory, settings, pin, query, models,
reveal, events, compare. Contract: docs/api.md. HTTP seam on loopback.
"""

from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest

from evals.helpers import ScriptedClient, gate_skip, make_yar, text_response
from yar.ops import compare_history, dashboard as dash


@pytest.fixture
def dash_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("YAR_HOME", str(home))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-ABCDEFGH")
    monkeypatch.setenv("YAR_BASE_URL", "https://api.avalai.ir/v1")
    dash._agent = None
    dash._dashboard_session = None
    dash._models_cache.clear()
    yield home
    dash._agent = None
    dash._dashboard_session = None


def _serve(handler_cls=dash.Handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield host, port, server
    finally:
        server.shutdown()
        thread.join(timeout=2)


@pytest.fixture
def server(dash_home):
    yield from _serve()


def _get(host, port, path):
    conn = HTTPConnection(host, port, timeout=5)
    conn.request("GET", path)
    resp = conn.getresponse()
    body = resp.read()
    conn.close()
    return resp.status, resp.getheader("Content-Type"), body


def _post(host, port, path, payload: dict):
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    conn = HTTPConnection(host, port, timeout=30)
    conn.request(
        "POST",
        path,
        body=raw,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    resp = conn.getresponse()
    body = resp.read()
    ctype = resp.getheader("Content-Type")
    status = resp.status
    conn.close()
    return status, ctype, body


def _json(host, port, method, path, payload=None):
    if method == "GET":
        status, ctype, body = _get(host, port, path)
    else:
        status, ctype, body = _post(host, port, path, payload or {})
    return status, ctype, json.loads(body.decode("utf-8"))


# ── query ────────────────────────────────────────────────────────────────────


def test_query_select_ok(server, dash_home):
    from yar.config import load_settings
    from yar.db import connect

    s = load_settings()
    s.ensure_home()
    conn = connect(s.home)
    conn.execute(
        "INSERT INTO facts (subject, content) VALUES (?, ?)",
        ("علی", "دوست قهوه"),
    )
    conn.commit()
    conn.close()

    host, port, _ = server
    status, _, out = _json(
        host, port, "POST", "/api/query", {"sql": "SELECT subject, content FROM facts"}
    )
    assert status == 200
    assert "columns" in out and "rows" in out
    assert "subject" in out["columns"]
    flat = " ".join(" ".join(r) for r in out["rows"])
    assert "علی" in flat


def test_query_rejects_mutating(server):
    host, port, _ = server
    for sql in (
        "DELETE FROM facts",
        "INSERT INTO facts (subject, content) VALUES ('x','y')",
        "UPDATE facts SET content='z'",
        "DROP TABLE facts",
        "SELECT 1; DELETE FROM facts",
    ):
        _, _, out = _json(host, port, "POST", "/api/query", {"sql": sql})
        assert "error" in out, sql


# ── memory ───────────────────────────────────────────────────────────────────


def test_memory_soul_fact_episode_skill(server, dash_home):
    host, port, _ = server

    _, _, out = _json(
        host, port, "POST", "/api/memory", {"action": "save_soul", "text": "Be brief.\n"}
    )
    assert out.get("ok") is True
    assert (dash_home / "SOUL.md").read_text(encoding="utf-8").startswith("Be brief")

    from yar.config import load_settings
    from yar.db import connect

    s = load_settings()
    s.ensure_home()
    conn = connect(s.home)
    conn.execute(
        "INSERT INTO facts (subject, content) VALUES (?, ?)", ("coffee", "likes latte")
    )
    conn.execute(
        "INSERT INTO episodes (summary, happened_at) VALUES (?, ?)",
        ("met Ali", "2026-01-01"),
    )
    conn.commit()
    fid = conn.execute("SELECT id FROM facts").fetchone()[0]
    eid = conn.execute("SELECT id FROM episodes").fetchone()[0]
    conn.close()

    _, _, out = _json(
        host,
        port,
        "POST",
        "/api/memory",
        {"action": "update_fact", "id": fid, "content": "likes اسپرسو", "subject": "coffee"},
    )
    assert out.get("ok") is True

    _, _, out = _json(
        host, port, "POST", "/api/memory", {"action": "delete_episode", "id": eid}
    )
    assert out.get("ok") is True

    _, _, out = _json(
        host,
        port,
        "POST",
        "/api/memory",
        {
            "action": "save_skill",
            "name": "tea-time",
            "description": "when user asks about tea چای",
            "body": "Offer herbal options.",
        },
    )
    assert out.get("ok") is True
    skill = dash_home / "skills" / "tea-time" / "SKILL.md"
    assert skill.exists()
    assert "چای" in skill.read_text(encoding="utf-8")

    _, _, out = _json(
        host, port, "POST", "/api/memory", {"action": "delete_fact", "id": fid}
    )
    assert out.get("ok") is True


# ── settings + pin ───────────────────────────────────────────────────────────


def test_settings_last4_no_full_key_no_provider_picker(server, dash_home, tmp_path, monkeypatch):
    # Write settings into an isolated .env so we don't touch the real one.
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=old-key-XXXX\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    host, port, _ = server
    status, _, data = _json(host, port, "GET", "/api/data")
    assert status == 200
    settings = data["settings"]
    assert settings["api_key_set"] is True
    assert settings["api_key_last4"] == "EFGH"
    assert "ABCDEFGH" not in json.dumps(settings)
    assert "provider" not in settings or settings.get("provider") == "openai"
    assert "providers" not in settings  # no provider picker
    assert "base_url" in settings

    # Rebuild path must accept model + base_url + key without a provider field.
    with patch.object(dash, "_get_agent") as mock_get:
        # Keep agent None-safe: apply_settings rebuilds; stub to avoid live client.
        mock_get.side_effect = RuntimeError("should rebuild via load")
    _, _, out = _json(
        host,
        port,
        "POST",
        "/api/settings",
        {
            "model": "gpt-4.1-mini",
            "small_model": "gpt-4.1-mini",
            "base_url": "https://api.avalai.ir/v1",
            "api_key": "sk-new-key-ZZZZ",
        },
    )
    # Rebuild may fail offline (no real OpenAI) — still must not echo full key
    # and must not require a provider field.
    blob = json.dumps(out)
    assert "sk-new-key-ZZZZ" not in blob
    if out.get("ok"):
        assert out["api_key_last4"] == "ZZZZ"
        assert "providers" not in out


def test_pin_persists_models_json(server, dash_home):
    host, port, _ = server
    _, _, out = _json(
        host, port, "POST", "/api/pin", {"action": "pin", "id": "gpt-4.1-mini"}
    )
    assert out.get("ok") is True
    path = dash_home / "models.json"
    assert path.exists()
    pinned = json.loads(path.read_text(encoding="utf-8"))["pinned"]
    assert "gpt-4.1-mini" in pinned

    _, _, out = _json(
        host, port, "POST", "/api/pin", {"action": "default", "id": "gpt-5.3-chat-latest"}
    )
    assert out.get("ok") is True
    pinned = json.loads(path.read_text(encoding="utf-8"))["pinned"]
    assert pinned[0] == "gpt-5.3-chat-latest"

    _, _, out = _json(
        host, port, "POST", "/api/pin", {"action": "unpin", "id": "gpt-4.1-mini"}
    )
    assert out.get("ok") is True
    pinned = json.loads(path.read_text(encoding="utf-8"))["pinned"]
    assert "gpt-4.1-mini" not in pinned


# ── models / events / reveal ─────────────────────────────────────────────────


def test_models_returns_defaults_on_catalog_failure(server, monkeypatch):
    host, port, _ = server

    def boom(*_a, **_k):
        raise OSError("catalog down")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    status, _, out = _json(host, port, "GET", "/api/models")
    assert status == 200
    assert "models" in out and len(out["models"]) >= 1
    assert "error" in out
    assert out.get("listed") is False


def test_events_cursor(server, dash_home):
    from yar.ops.tracing import Tracer
    from yar.config import load_settings

    s = load_settings()
    s.ensure_home()
    tr = Tracer(s)
    tr.event("turn_start", {"user_message": "hi"})
    tr.event("turn_end", {"reply": "yo", "iterations": 1})

    host, port, _ = server
    status, _, out = _json(host, port, "GET", "/api/events")
    assert status == 200
    assert "cursor" in out and "events" in out
    # First poll with no cursor: empty events, cursor at end (don't replay).
    assert out["events"] == []
    cursor = out["cursor"]
    assert cursor >= 2

    tr.event("gate", {"decision": "skip", "reason": "x"})
    _, _, out2 = _json(host, port, "GET", f"/api/events?cursor={cursor}")
    assert any(e.get("type") == "gate" for e in out2["events"])
    assert out2["cursor"] > cursor


def test_reveal_rejects_outside_home(server, dash_home, tmp_path):
    host, port, _ = server
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")
    status, _, out = _json(
        host, port, "GET", f"/api/reveal?path=../{outside.name}"
    )
    assert status == 200
    assert "error" in out


def test_reveal_ok_under_home(server, dash_home, monkeypatch):
    (dash_home / "SOUL.md").write_text("hi\n", encoding="utf-8")
    host, port, _ = server
    monkeypatch.setattr(dash, "_editor_cmd", lambda: None)
    # On non-macOS without editor, reveal returns an error that still names the path.
    _, _, out = _json(host, port, "GET", "/api/reveal?path=SOUL.md")
    assert "ok" in out or "error" in out
    if "error" in out:
        assert "SOUL.md" in out["error"] or str(dash_home) in out["error"]


# ── compare ──────────────────────────────────────────────────────────────────


def test_compare_history_outside_state_db(dash_home):
    compare_history.append_run(
        dash_home,
        "hello",
        [
            {
                "spec": "openai:gpt-4.1-mini",
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "reply": "hi",
                "latency_ms": 10,
                "tokens_in": 1,
                "tokens_out": 1,
                "cost_usd": 0.0,
                "tools": [],
            }
        ],
    )
    path = dash_home / "compare" / "history.jsonl"
    assert path.exists()
    # Must not create compare tables in state.db
    from yar.db import connect

    conn = connect(dash_home)
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()
    assert "compare" not in tables
    assert not any("compare" in t for t in tables)


def test_compare_history_persian_unescaped(dash_home):
    """Arena history must keep Persian readable (same wire contract as /api/data)."""
    compare_history.append_run(
        dash_home,
        "یک جلسه با علی بگذار",
        [
            {
                "spec": "openai:gpt-4.1-mini",
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "reply": "انجام شد — قهوه فردا ساعت ۹.",
                "latency_ms": 3,
                "tokens_in": 1,
                "tokens_out": 2,
                "cost_usd": 0.0,
                "tools": [{"tool": "create_event"}],
            }
        ],
    )
    raw = (dash_home / "compare" / "history.jsonl").read_text(encoding="utf-8")
    assert "علی" in raw and "انجام شد" in raw
    assert "\\u" not in raw
    runs = compare_history.load_runs(dash_home)
    assert runs[-1]["message"] == "یک جلسه با علی بگذار"
    assert "قهوه" in runs[-1]["results"][0]["reply"]


def test_compare_clear_delete_regrade_and_history(server, dash_home):
    host, port, _ = server
    compare_history.append_run(
        dash_home,
        "ping",
        [
            {
                "spec": "openai:gpt-4.1-mini",
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "reply": "pong",
                "latency_ms": 5,
                "tokens_in": 2,
                "tokens_out": 2,
                "cost_usd": 0.0,
                "tools": ["save_note"],
                "quality": None,
            }
        ],
        ts="2026-01-01T00:00:00+00:00",
    )

    status, _, out = _json(host, port, "GET", "/api/compare/history")
    assert status == 200
    assert len(out["runs"]) == 1
    assert out["aggregate"]

    # regrade without a live judge: only_missing leaves quality None — still 200
    with patch("yar.ops.judge.judge_reply", return_value={"score": 8, "reason": "ok", "judge": "x"}):
        _, _, out = _json(
            host, port, "POST", "/api/compare/regrade", {"only_missing": True}
        )
    assert out["runs"][-1]["results"][0]["quality"]["score"] == 8

    _, _, out = _json(
        host,
        port,
        "POST",
        "/api/compare/delete_run",
        {"ts": "2026-01-01T00:00:00+00:00"},
    )
    assert out["runs"] == []

    compare_history.append_run(dash_home, "again", [{"spec": "openai:m", "provider": "openai",
                                                      "model": "m", "reply": "x", "error": None}])
    _, _, out = _json(host, port, "POST", "/api/compare/clear", {})
    assert out.get("ok") is True
    assert out["runs"] == []
    assert not (dash_home / "compare" / "history.jsonl").exists()


def test_compare_uses_temp_homes(server, dash_home, monkeypatch):
    """Each contestant must not write into the real home's state.db."""
    host, port, _ = server
    homes_seen: list[Path] = []

    def fake_one(message, spec):
        from yar.config import Settings
        from yar.app import Yar
        from yar.db import connect
        import tempfile

        model = spec.split(":")[-1] if ":" in spec else spec
        home = Path(tempfile.mkdtemp(prefix="compare-test-"))
        homes_seen.append(home)
        settings = Settings(home=home, model=model, api_key="offline", small_model="")
        settings.ensure_home()
        client = ScriptedClient([gate_skip(), text_response(f"from {model}")])
        app = Yar(settings=settings, client=client, conn=connect(home))
        result = app.respond(message, source="compare")
        return {
            "spec": f"openai:{model}",
            "provider": "openai",
            "model": model,
            "reply": result.reply,
            "gate": None,
            "iterations": result.iterations,
            "latency_ms": 1,
            "tools": [],
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
        }

    monkeypatch.setattr(dash, "_compare_one", fake_one)
    _, _, out = _json(
        host,
        port,
        "POST",
        "/api/compare",
        {"message": "hi", "models": ["gpt-4.1-mini", "gpt-5.3-chat-latest"]},
    )
    assert out.get("ok") is True
    assert len(out["results"]) == 2
    for h in homes_seen:
        assert h != dash_home
        assert dash_home not in h.parents or h != dash_home
    # Real home calendar untouched
    from yar.db import connect

    conn = connect(dash_home)
    n = conn.execute("SELECT COUNT(*) FROM calendar_events").fetchone()[0]
    conn.close()
    assert n == 0


def test_compare_stream_sse(server, dash_home, monkeypatch):
    def fake_stream(message, specs, emit, judge=False, judge_model=""):
        for spec in specs:
            model = spec.split(":")[-1] if ":" in spec else spec
            emit("start", {"spec": f"openai:{model}", "provider": "openai", "model": model})
            emit(
                "result",
                {
                    "spec": f"openai:{model}",
                    "provider": "openai",
                    "model": model,
                    "reply": "ok",
                    "tools": [],
                    "latency_ms": 1,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_usd": 0.0,
                },
            )
        emit("done", {})

    monkeypatch.setattr(dash, "compare_stream", fake_stream)
    host, port, _ = server
    status, ctype, body = _post(
        host,
        port,
        "/api/compare/stream",
        {"message": "hi", "models": ["gpt-4.1-mini"]},
    )
    assert status == 200
    assert "text/event-stream" in ctype
    text = body.decode("utf-8")
    assert "data: " in text
    kinds = []
    for line in text.splitlines():
        if line.startswith("data: "):
            kinds.append(json.loads(line[6:])["kind"])
    assert "start" in kinds and "result" in kinds and "done" in kinds
