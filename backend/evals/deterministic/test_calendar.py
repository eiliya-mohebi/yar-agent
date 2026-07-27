"""Flagship calendar tools — DB + ICS side effects, idempotency, honest dates."""

from __future__ import annotations

from yar.db import connect
from yar.tools.calendar import make_list_tool, make_tool
from yar.tools.registry import ToolRegistry


def _calendar_registry(home):
    conn = connect(home)
    registry = ToolRegistry()
    registry.register(make_tool(conn, home))
    registry.register(make_list_tool(conn, home))
    return conn, registry


def test_create_event_writes_db_and_ics(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    conn, tools = _calendar_registry(home)

    out = tools.execute(
        "create_event",
        {"title": "Coffee with Alex", "start": "2026-07-14T09:00"},
    )

    assert "Event created" in out
    row = conn.execute("SELECT title, start, \"end\" FROM calendar_events").fetchone()
    assert row["title"] == "Coffee with Alex"
    assert row["start"] == "2026-07-14T09:00"
    assert row["end"] == "2026-07-14T10:00"
    ics = (home / "calendar.ics").read_text()
    assert "SUMMARY:Coffee with Alex" in ics
    assert "DTSTART:20260714T090000" in ics


def test_create_event_is_idempotent(tmp_path):
    """Same title+start must never duplicate (even 17:00 vs 17:00:00)."""
    home = tmp_path / "home"
    home.mkdir()
    conn, tools = _calendar_registry(home)
    args = {"title": "Swim with Sergey", "start": "2026-07-11T17:00"}

    first = tools.execute("create_event", args)
    second = tools.execute(
        "create_event", {**args, "start": "2026-07-11T17:00:00"}
    )

    assert "Event created" in first
    assert "already exists" in second
    count = conn.execute("SELECT COUNT(*) FROM calendar_events").fetchone()[0]
    assert count == 1
    ics = (home / "calendar.ics").read_text()
    assert ics.count("SUMMARY:Swim with Sergey") == 1


def test_create_event_digit_folds_persian_start(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    conn, tools = _calendar_registry(home)

    out = tools.execute(
        "create_event",
        {"title": "جلسه با علی", "start": "۲۰۲۶-۰۷-۱۴T۰۹:۰۰"},
    )

    assert "Event created" in out
    row = conn.execute("SELECT title, start FROM calendar_events").fetchone()
    assert row["title"] == "جلسه با علی"
    assert row["start"] == "2026-07-14T09:00"


def test_create_event_rejects_unparseable_date(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    conn, tools = _calendar_registry(home)

    out = tools.execute(
        "create_event",
        {"title": "Something", "start": "۵ مرداد"},
    )

    assert "Could not parse" in out or "ISO" in out
    assert "invent" in out.lower() or "not invent" in out.lower()
    count = conn.execute("SELECT COUNT(*) FROM calendar_events").fetchone()[0]
    assert count == 0
    assert not (home / "calendar.ics").exists()


def test_create_event_rejects_date_only_as_ambiguous(tmp_path):
    """A day without a time is ambiguous for booking — refuse to invent HH:MM."""
    home = tmp_path / "home"
    home.mkdir()
    conn, tools = _calendar_registry(home)

    out = tools.execute(
        "create_event",
        {"title": "Something", "start": "2026-07-14"},
    )

    assert "ambiguous" in out.lower() or "Could not parse" in out or "time" in out.lower()
    count = conn.execute("SELECT COUNT(*) FROM calendar_events").fetchone()[0]
    assert count == 0


def test_list_events_filters_by_day(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    conn, tools = _calendar_registry(home)
    tools.execute(
        "create_event",
        {"title": "Morning", "start": "2026-07-14T09:00"},
    )
    tools.execute(
        "create_event",
        {"title": "Later", "start": "2026-07-20T09:00"},
    )

    out = tools.execute("list_events", {"start": "2026-07-14", "end": "2026-07-14"})

    assert "Morning" in out
    assert "Later" not in out
