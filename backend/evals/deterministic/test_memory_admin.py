"""DETERMINISTIC EVAL — manage_memory / update_soul / create_skill when memory wired."""

from __future__ import annotations

from evals.helpers import ScriptedClient, gate_skip, make_yar, text_response, tool_response
from yar.config import Settings
from yar.db import connect
from yar.memory import Memory
from yar.memory.semantic.store import SqliteFactStore
from yar.tools import build_registry
from yar.tools.memory_admin import (
    make_create_skill_tool,
    make_manage_memory_tool,
    make_update_soul_tool,
)


def test_build_registry_includes_memory_admin_when_wired(tmp_path):
    settings = Settings(home=tmp_path / "home", api_key="offline")
    settings.ensure_home()
    conn = connect(settings.home)
    memory = Memory(conn, settings, client=ScriptedClient([]))

    with_mem = build_registry(conn, settings, memory)
    names = {t["function"]["name"] for t in with_mem.schemas()}
    assert {"manage_memory", "update_soul", "create_skill"} <= names

    without = build_registry(conn, settings)
    names_off = {t["function"]["name"] for t in without.schemas()}
    assert "manage_memory" not in names_off


def test_manage_memory_search_update_delete(tmp_path):
    settings = Settings(home=tmp_path / "home", api_key="offline")
    settings.ensure_home()
    conn = connect(settings.home)
    memory = Memory(conn, settings, client=ScriptedClient([]))
    SqliteFactStore(conn).add("alex", "Alex likes tea")
    tool = make_manage_memory_tool(memory)

    found = tool.fn(action="search", query="alex")
    assert "Alex likes tea" in found
    fact_id = int(found.split("#", 1)[1].split()[0])

    assert "Updated" in tool.fn(action="update", id=fact_id, content="Alex likes coffee")
    hits = SqliteFactStore(conn).search("alex coffee")
    assert hits

    assert "Deleted" in tool.fn(action="delete", id=fact_id)
    assert SqliteFactStore(conn).search("alex") == []


def test_manage_memory_search_persian_fact(tmp_path):
    settings = Settings(home=tmp_path / "home", api_key="offline")
    settings.ensure_home()
    conn = connect(settings.home)
    memory = Memory(conn, settings, client=ScriptedClient([]))
    # Store with Persian ی; query with Arabic ي — normalize must fold both.
    SqliteFactStore(conn).add("علی", "علی صبح‌ها را ترجیح می‌دهد")
    tool = make_manage_memory_tool(memory)

    found = tool.fn(action="search", query="علي صبح")
    assert "علی" in found or "صبح" in found
    assert "ترجیح" in found


def test_update_soul_appends_learned_rule(tmp_path):
    settings = Settings(home=tmp_path / "home", api_key="offline")
    settings.ensure_home()
    tool = make_update_soul_tool(settings)
    out = tool.fn(rule="Always prefer morning meetings")
    assert "Always prefer morning meetings" in out
    text = (settings.home / "SOUL.md").read_text()
    assert "## Learned rules" in text
    assert "Always prefer morning meetings" in text


def test_create_skill_writes_and_refreshes(tmp_path):
    settings = Settings(home=tmp_path / "home", api_key="offline")
    settings.ensure_home()
    conn = connect(settings.home)
    memory = Memory(conn, settings, client=ScriptedClient([]))
    tool = make_create_skill_tool(settings, memory)

    out = tool.fn(
        name="weekly-review",
        description="weekly review retrospection جلسه مرور هفتگی",
        body="1. List wins\n2. List risks",
    )
    assert "Created skill" in out
    path = settings.home / "skills" / "weekly-review" / "SKILL.md"
    assert path.exists()
    matched = memory.skills.match("مرور هفتگی این هفته")
    assert any(s.name == "weekly-review" for s in matched)


def test_respond_can_call_manage_memory(tmp_path):
    home = tmp_path / "home"
    app = make_yar(home, client=ScriptedClient([]))
    SqliteFactStore(app.conn).add("tea", "User likes green tea")
    client = ScriptedClient(
        [
            gate_skip(),
            tool_response("manage_memory", {"action": "search", "query": "tea"}),
            text_response("You like green tea."),
        ]
    )
    app.client = client
    app.memory.client = client
    result = app.respond("what tea do I like?")
    assert [c["tool"] for c in result.tool_calls] == ["manage_memory"]
    assert "green tea" in result.tool_calls[0]["output"]
