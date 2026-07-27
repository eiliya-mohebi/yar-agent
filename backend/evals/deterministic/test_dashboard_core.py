"""Core dashboard API — /api/data, chat, SSE, session; Persian unescaped on wire."""

from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from evals.helpers import ScriptedClient, make_yar, text_response
from yar.ops import dashboard as dash

REQUIRED_DATA_KEYS = {
    "model",
    "home",
    "stats",
    "chat_log",
    "turns",
    "facts",
    "episodes",
    "soul",
    "skills",
    "calendar",
    "outbox",
    "sessions",
    "current_session",
    "eval_report",
    "db",
    "settings",
    "tools",
    "usage",
}


@pytest.fixture
def dash_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("YAR_HOME", str(home))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    # Reset process-global agent between tests.
    dash._agent = None
    dash._dashboard_session = None
    yield home
    dash._agent = None
    dash._dashboard_session = None


def _serve(handler_cls=dash.Handler):
    """Bind an ephemeral loopback server; yield (host, port, server)."""
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
    conn = HTTPConnection(host, port, timeout=10)
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


def test_api_data_has_required_keys(server, dash_home):
    host, port, _ = server
    status, ctype, body = _get(host, port, "/api/data")
    assert status == 200
    assert "application/json" in ctype
    assert "charset=utf-8" in ctype
    data = json.loads(body.decode("utf-8"))
    assert REQUIRED_DATA_KEYS <= set(data)
    assert data["home"].endswith(str(dash_home.resolve())) or str(dash_home) in data["home"]


def test_api_data_persian_unescaped_on_wire(server, dash_home):
    from yar.config import load_settings
    from yar.db import connect

    settings = load_settings()
    settings.ensure_home()
    conn = connect(settings.home)
    conn.execute(
        "INSERT INTO facts (subject, content) VALUES (?, ?)",
        ("علی", "علی قهوه صبحگاهی دوست دارد"),
    )
    conn.commit()
    conn.close()

    host, port, _ = server
    _, _, body = _get(host, port, "/api/data")
    raw = body.decode("utf-8")
    assert "علی" in raw
    assert "\\u" not in raw


def test_session_new_switch_history(server, dash_home):
    host, port, _ = server

    # Seed a past session via make_yar so switch has something to load.
    client = ScriptedClient([text_response("سلام!")])
    yar = make_yar(dash_home, client=client, model="gpt-4.1-mini")
    yar.session.session_id = "past-1"
    yar.respond("سلام", source="dashboard")
    # Drop process agent so dashboard rebuilds against same home.
    dash._agent = None

    status, _, body = _post(host, port, "/api/session", {"action": "new"})
    assert status == 200
    new = json.loads(body)
    assert new["ok"] is True
    assert new["session_id"].startswith("s-")
    assert new["history"] == []

    status, _, body = _post(
        host, port, "/api/session", {"action": "history", "session_id": "past-1"}
    )
    hist = json.loads(body)
    assert hist["ok"] is True
    assert any(m["role"] == "user" and "سلام" in m["content"] for m in hist["history"])

    status, _, body = _post(
        host, port, "/api/session", {"action": "switch", "session_id": "past-1"}
    )
    switched = json.loads(body)
    assert switched["ok"] is True
    assert switched["session_id"] == "past-1"
    assert len(switched["history"]) >= 2


def _scripted_agent(home, client):
    """Dashboard HTTP workers are other threads — need check_same_thread=False."""
    from yar.app import Yar
    from yar.config import Settings
    from yar.db import connect

    settings = Settings(home=home, model="gpt-4.1-mini", api_key="offline")
    settings.ensure_home()
    return Yar(settings=settings, client=client, conn=connect(home, check_same_thread=False))


def test_chat_returns_reply(server, dash_home, monkeypatch):
    # Inject a scripted agent so chat never hits the network.
    client = ScriptedClient([text_response("پاسخ فارسی")])
    agent = _scripted_agent(dash_home, client)
    monkeypatch.setattr(dash, "_get_agent", lambda: agent)

    host, port, _ = server
    status, ctype, body = _post(host, port, "/api/chat", {"message": "سلام"})
    assert status == 200
    assert "charset=utf-8" in ctype
    out = json.loads(body.decode("utf-8"))
    assert out["reply"] == "پاسخ فارسی"
    assert "پاسخ" in body.decode("utf-8")
    assert "\\u" not in body.decode("utf-8")
    assert "iterations" in out
    assert "meta" in out or "tools" in out


def test_chat_stream_sse_kinds(server, dash_home, monkeypatch):
    client = ScriptedClient([text_response("done")])
    agent = _scripted_agent(dash_home, client)
    monkeypatch.setattr(dash, "_get_agent", lambda: agent)

    host, port, _ = server
    status, ctype, body = _post(host, port, "/api/chat/stream", {"message": "hi"})
    assert status == 200
    assert "text/event-stream" in ctype
    text = body.decode("utf-8")
    assert "data: " in text
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    kinds = {e["kind"] for e in events}
    assert "done" in kinds
    assert "llm" in kinds  # at least one harness event
    done = next(e for e in events if e["kind"] == "done")
    assert done.get("reply") == "done"


def test_port_walk_finds_free_port(monkeypatch, dash_home):
    """main() walks +10 when the preferred port is busy."""
    busy = ThreadingHTTPServer(("127.0.0.1", 0), dash.Handler)
    busy_port = busy.server_address[1]
    thread = threading.Thread(target=busy.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("YAR_DASHBOARD_PORT", str(busy_port))
        chosen = []

        class Capture(ThreadingHTTPServer):
            def __init__(self, addr, handler):
                super().__init__(addr, handler)
                chosen.append(addr[1])
                raise SystemExit("captured")  # stop after first successful bind

        monkeypatch.setattr(dash, "ThreadingHTTPServer", Capture)
        with pytest.raises(SystemExit, match="captured"):
            dash.main()
        assert chosen
        assert chosen[0] != busy_port
        assert busy_port < chosen[0] <= busy_port + 9
    finally:
        busy.shutdown()
        thread.join(timeout=2)
