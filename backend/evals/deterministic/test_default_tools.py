"""DETERMINISTIC EVAL — default tools: save_note, send_message, search_web."""

from __future__ import annotations

from yar.config import Settings
from yar.db import connect
from yar.memory.semantic.store import SqliteFactStore
from yar.tools import build_registry, messages, notes, search


def test_save_note_writes_normalized_user_fact(tmp_path):
    settings = Settings(home=tmp_path / "home", api_key="test-key")
    settings.ensure_home()
    conn = connect(settings.home)
    tool = notes.make_tool(conn)

    out = tool.fn(subject="علی", content="علی صبح‌ها را ترجیح می‌دهد")
    assert "Saved to memory" in out

    rows = conn.execute("SELECT subject, content, source FROM facts").fetchall()
    assert len(rows) == 1
    assert rows[0]["source"] == "user"
    # Normalize-on-write so Persian folds are searchable.
    hits = SqliteFactStore(conn).search("علی صبح")
    assert hits, "saved note must be FTS-searchable after normalize"


def test_save_note_english_preference(tmp_path):
    settings = Settings(home=tmp_path / "home", api_key="test-key")
    settings.ensure_home()
    conn = connect(settings.home)
    notes.make_tool(conn).fn(subject="alex", content="Alex prefers morning meetings")
    hits = SqliteFactStore(conn).search("alex morning")
    assert any("prefers morning" in h for h in hits)


def test_send_message_writes_outbox_draft(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / "outbox").mkdir()
    tool = messages.make_tool(home)

    out = tool.fn(to="sara@example.com", body="سلام، فردا می‌بینمت")
    assert "Nothing was sent" in out
    files = list((home / "outbox").glob("*.txt"))
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    assert text.startswith("To: sara@example.com\n")
    assert "سلام، فردا می‌بینمت" in text


def test_search_web_formats_mocked_duckduckgo_results(monkeypatch):
    html = """
    <a class="result__a" href="https://ddg.example/l/?uddg=https%3A%2F%2Fex.com%2Fa">
    Alpha Title</a>
    <a class="result__snippet">Alpha snippet here</a>
    <a class="result__a" href="https://example.com/b">Beta Title</a>
    <a class="result__snippet">Beta snippet here</a>
    """

    class _Resp:
        def read(self):
            return html.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setattr(search.urllib.request, "urlopen", lambda *a, **k: _Resp())

    out = search.make_tool().fn(query="world cup", max_results=2)
    assert "Web results for 'world cup'" in out
    assert "DuckDuckGo" in out
    assert "1. Alpha Title" in out
    assert "https://ex.com/a" in out
    assert "2. Beta Title" in out


def test_search_web_hints_tavily_when_ddg_empty(monkeypatch):
    class _Resp:
        def read(self):
            return b"<html>no results</html>"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setattr(search.urllib.request, "urlopen", lambda *a, **k: _Resp())

    out = search.make_tool().fn(query="obscure thing")
    assert "TAVILY_API_KEY" in out


def test_build_registry_includes_default_tools(tmp_path):
    settings = Settings(home=tmp_path / "home", api_key="test-key")
    settings.ensure_home()
    conn = connect(settings.home)
    names = {s["function"]["name"] for s in build_registry(conn, settings).schemas()}
    assert {"create_event", "list_events", "save_note", "send_message", "search_web"} <= names
