"""DETERMINISTIC EVAL — consolidation loss-safety, threshold, MEMORY.md mirror."""

from __future__ import annotations

from evals.helpers import (
    ScriptedClient,
    gate_skip,
    make_yar,
    text_response,
)


def _seed_unconsolidated(conn, n_exchanges: int) -> None:
    for i in range(n_exchanges):
        conn.execute(
            "INSERT INTO chat_log (role, content, consolidated) VALUES ('user', ?, 0)",
            (f"user msg {i}",),
        )
        conn.execute(
            "INSERT INTO chat_log (role, content, consolidated) VALUES ('assistant', ?, 0)",
            (f"assistant msg {i}",),
        )
    conn.commit()


def test_consolidation_not_due_below_threshold(tmp_path):
    """Default consolidate_every=6 → need 12 rows; 10 rows must not fire."""
    app = make_yar(
        tmp_path / "home",
        client=ScriptedClient([]),
        consolidate_every=6,
    )
    _seed_unconsolidated(app.conn, 5)  # 10 rows
    events = []
    app.memory.maybe_consolidate(notify=lambda k, e: events.append((k, e)))
    assert events == []
    left = app.conn.execute(
        "SELECT COUNT(*) AS n FROM chat_log WHERE consolidated = 0"
    ).fetchone()["n"]
    assert left == 10


def test_consolidation_writes_facts_episode_and_marks_rows(tmp_path):
    summary = text_response(
        '{"facts": [{"subject": "alex", "content": "Alex prefers mornings"}],'
        ' "episode": "Talked about Alex meeting prefs"}'
    )
    app = make_yar(
        tmp_path / "home",
        client=ScriptedClient([summary]),
        consolidate_every=2,  # trigger at 4 rows
    )
    app.memory.client = app.client
    _seed_unconsolidated(app.conn, 2)  # 4 rows

    events = []
    app.memory.maybe_consolidate(notify=lambda k, e: events.append((k, e)))

    assert events == [("consolidation", {"new_facts": 1})]
    facts = app.conn.execute("SELECT subject, content, source FROM facts").fetchall()
    assert len(facts) == 1
    assert facts[0]["source"] == "consolidation"
    assert "mornings" in facts[0]["content"]
    eps = app.conn.execute("SELECT summary FROM episodes").fetchall()
    assert len(eps) == 1
    assert "Alex" in eps[0]["summary"]
    left = app.conn.execute(
        "SELECT COUNT(*) AS n FROM chat_log WHERE consolidated = 0"
    ).fetchone()["n"]
    assert left == 0


def test_consolidation_loss_safe_on_summarizer_failure(tmp_path):
    """Exception → return 0, leave rows unmarked (never lose the log)."""
    app = make_yar(
        tmp_path / "home",
        client=ScriptedClient([text_response("NOT JSON")]),
        consolidate_every=1,
    )
    app.memory.client = app.client
    _seed_unconsolidated(app.conn, 1)  # 2 rows ≥ 1*2

    app.memory.maybe_consolidate()
    left = app.conn.execute(
        "SELECT COUNT(*) AS n FROM chat_log WHERE consolidated = 0"
    ).fetchone()["n"]
    assert left == 2
    assert app.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 0


def test_consolidation_keeps_persian_facts(tmp_path):
    """Summarizer output in Persian must land searchable (source language)."""
    summary = text_response(
        '{"facts": [{"subject": "علی", "content": "علی صبح‌ها را ترجیح می‌دهد"}],'
        ' "episode": "درباره ترجیح زمانی علی صحبت شد"}'
    )
    app = make_yar(
        tmp_path / "home",
        client=ScriptedClient([summary]),
        consolidate_every=1,
    )
    app.memory.client = app.client
    _seed_unconsolidated(app.conn, 1)

    app.memory.maybe_consolidate()
    hits = app.memory.facts.search("علی صبح")
    assert hits, "Persian consolidation facts must be FTS-searchable"
    assert any("صبح" in h for h in hits)


def test_respond_exports_memory_md(tmp_path):
    home = tmp_path / "home"
    app = make_yar(home, client=ScriptedClient([gate_skip(), text_response("hi")]))
    from yar.memory.semantic.store import SqliteFactStore

    SqliteFactStore(app.conn).add("tea", "User likes green tea")
    app.respond("hello")

    md = (home / "MEMORY.md").read_text()
    assert "Yar memory" in md
    assert "green tea" in md
    assert "## Facts" in md
    assert "## Episodes" in md


def test_respond_runs_consolidation_when_due(tmp_path):
    summary = text_response(
        '{"facts": [{"subject": "project", "content": "Acme demo Friday"}],'
        ' "episode": "Planned Acme demo"}'
    )
    # consolidate_every=1 → due after every exchange (2 rows). One respond
    # logs 2 rows then consolidates: gate + loop + summarizer.
    app = make_yar(
        tmp_path / "home",
        client=ScriptedClient([gate_skip(), text_response("ok"), summary]),
        consolidate_every=1,
    )
    events = []
    app.respond("plan the demo", observer=lambda k, e: events.append((k, e)))

    cons = [e for k, e in events if k == "consolidation"]
    assert cons and cons[0]["new_facts"] == 1
    assert app.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 1
