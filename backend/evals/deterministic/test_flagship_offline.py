"""Offline flagship evals — ScriptedClient books the same meeting in EN and FA."""

from __future__ import annotations

import json
from types import SimpleNamespace

from evals.helpers import ScriptedClient, make_yar, text_response, tool_response


def test_make_yar_isolates_home(tmp_path, monkeypatch):
    """Evals must never touch the developer's real .yar/ home."""
    real_home = tmp_path / "real-dot-yar"
    real_home.mkdir()
    monkeypatch.setenv("YAR_HOME", str(real_home))
    # Poison the real home so any accidental write is obvious.
    (real_home / "MUST_NOT_TOUCH").write_text("sentinel")

    isolated = tmp_path / "eval-home"
    app = make_yar(isolated, client=ScriptedClient([text_response("hi")]))
    app.respond("hello")

    assert app.settings.home == isolated
    assert (isolated / "state.db").exists()
    assert list(real_home.iterdir()) == [real_home / "MUST_NOT_TOUCH"]


def test_offline_book_meeting_english(tmp_path):
    home = tmp_path / "home"
    client = ScriptedClient(
        [
            tool_response(
                "create_event",
                {"title": "Coffee with Alex", "start": "2026-07-14T09:00"},
            ),
            text_response("Booked!"),
        ]
    )
    app = make_yar(home, client=client)
    result = app.respond("Schedule a coffee with Alex next Tuesday at 9am")

    assert [c["tool"] for c in result.tool_calls] == ["create_event"]
    row = app.conn.execute("SELECT title, start FROM calendar_events").fetchone()
    assert row["title"] == "Coffee with Alex"
    assert row["start"] == "2026-07-14T09:00"
    assert "SUMMARY:Coffee with Alex" in (home / "calendar.ics").read_text()


def test_offline_book_meeting_persian(tmp_path):
    """-fa counterpart: same calendar_events row / ICS as the English case."""
    home = tmp_path / "home"
    client = ScriptedClient(
        [
            tool_response(
                "create_event",
                # Same meeting as EN; Persian digits fold to the same ISO start.
                {"title": "Coffee with Alex", "start": "۲۰۲۶-۰۷-۱۴T۰۹:۰۰"},
            ),
            text_response("رزرو شد!"),
        ]
    )
    app = make_yar(home, client=client)
    result = app.respond("یک قهوه با الکس برای سه‌شنبه آینده ساعت ۹ صبح بگذار")

    assert [c["tool"] for c in result.tool_calls] == ["create_event"]
    row = app.conn.execute("SELECT title, start FROM calendar_events").fetchone()
    assert row["title"] == "Coffee with Alex"
    assert row["start"] == "2026-07-14T09:00"
    assert "SUMMARY:Coffee with Alex" in (home / "calendar.ics").read_text()


def test_offline_rebook_is_idempotent_via_respond(tmp_path):
    """Same title+start in one turn (17:00 vs 17:00:00) must not duplicate."""
    home = tmp_path / "home"
    args = {"title": "Swim with Sergey", "start": "2026-07-11T17:00"}
    multi = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[
                        SimpleNamespace(
                            id="c1",
                            type="function",
                            function=SimpleNamespace(
                                name="create_event", arguments=json.dumps(args)
                            ),
                        ),
                        SimpleNamespace(
                            id="c2",
                            type="function",
                            function=SimpleNamespace(
                                name="create_event",
                                arguments=json.dumps(
                                    {**args, "start": "2026-07-11T17:00:00"}
                                ),
                            ),
                        ),
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=0, completion_tokens=0),
    )
    app = make_yar(
        home,
        client=ScriptedClient([multi, text_response("Booked once.")]),
    )
    result = app.respond("swim with sergey saturday 5pm")

    count = app.conn.execute("SELECT COUNT(*) FROM calendar_events").fetchone()[0]
    assert count == 1
    assert "already exists" in result.tool_calls[1]["output"]
    assert (home / "calendar.ics").read_text().count("SUMMARY:Swim with Sergey") == 1
