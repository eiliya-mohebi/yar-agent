"""create_event / list_events — flagship local calendar (SQLite + calendar.ics).

No OS calendar sync. Dates are digit-folded then parsed as ISO 8601 / Gregorian
only; unparseable input returns an honest error instead of a guess.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from yar.text import normalize
from yar.tools.registry import Tool


def _write_ics(home: Path, title: str, start: str, end: str, attendees: str) -> None:
    """Append a minimal VEVENT. ISO like 2026-07-14T09:00 → 20260714T090000."""
    ics_path = home / "calendar.ics"

    def dt(s: str) -> str:
        return s.replace("-", "").replace(":", "") + ("00" if len(s) == 16 else "")

    event = (
        "BEGIN:VEVENT\n"
        f"SUMMARY:{title}\n"
        f"DTSTART:{dt(start)}\n"
        f"DTEND:{dt(end)}\n"
        f"DESCRIPTION:attendees: {attendees}\n"
        "END:VEVENT\n"
    )
    if ics_path.exists():
        body = ics_path.read_text().replace("END:VCALENDAR\n", "")
    else:
        body = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//yar-agent//EN\n"
    ics_path.write_text(body + event + "END:VCALENDAR\n")


def _parse_iso(value: str) -> str | None:
    """Digit-fold then require ISO datetime (date + time). Returns minutes form, or None."""
    folded = normalize(value).strip()
    if not folded or "T" not in folded:
        return None
    try:
        datetime.fromisoformat(folded)
    except ValueError:
        return None
    # Need at least YYYY-MM-DDTHH:MM — refuse date-only / truncated times.
    if len(folded) < 16:
        return None
    return folded[:16]


def make_tool(conn: sqlite3.Connection, home: Path) -> Tool:
    def create_event(
        title: str = "",
        start: str = "",
        end: str = "",
        attendees: str = "",
        notes: str = "",
    ) -> str:
        if not title or not start:
            return (
                "create_event needs at least a title and a start time "
                "(ISO 8601, e.g. 2026-07-14T09:00). Please call it again with both."
            )

        parsed_start = _parse_iso(start)
        if parsed_start is None:
            return (
                f"Could not parse start time {start!r} as ISO 8601 "
                "(e.g. 2026-07-14T09:00). A concrete Gregorian datetime with a time "
                "is required — ambiguous or unparseable dates are not invented."
            )

        if end:
            parsed_end = _parse_iso(end)
            if parsed_end is None:
                return (
                    f"Could not parse end time {end!r} as ISO 8601 "
                    "(e.g. 2026-07-14T10:00). A concrete Gregorian datetime with a time "
                    "is required — ambiguous or unparseable dates are not invented."
                )
        else:
            parsed_end = (
                datetime.fromisoformat(parsed_start) + timedelta(hours=1)
            ).isoformat(timespec="minutes")

        existing = conn.execute(
            "SELECT id FROM calendar_events WHERE title = ? AND start = ?",
            (title, parsed_start),
        ).fetchone()
        if existing:
            return f"Event '{title}' at {parsed_start} already exists (not duplicated)."

        conn.execute(
            'INSERT INTO calendar_events (title, start, "end", attendees, notes) '
            "VALUES (?,?,?,?,?)",
            (title, parsed_start, parsed_end, attendees, notes),
        )
        conn.commit()
        _write_ics(home, title, parsed_start, parsed_end, attendees)

        where = (
            f"Saved to the local calendar ({home / 'calendar.ics'}). "
            f"Import manually if you want it in another calendar app: "
            f"open {home / 'calendar.ics'}."
        )
        return (
            f"Event created: '{title}' {parsed_start} → {parsed_end}"
            + (f" with {attendees}" if attendees else "")
            + f". {where}"
        )

    return Tool(
        name="create_event",
        description=(
            "Create a calendar event on the user's local calendar. Use whenever the user "
            "wants to schedule, book, or plan something at a specific time."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short event title"},
                "start": {
                    "type": "string",
                    "description": "Start time, ISO 8601, e.g. 2026-07-14T09:00",
                },
                "end": {
                    "type": "string",
                    "description": "End time, ISO 8601. Defaults to start + 1h.",
                },
                "attendees": {
                    "type": "string",
                    "description": "Comma-separated names/emails",
                },
                "notes": {"type": "string", "description": "Optional context for the event"},
            },
            "required": ["title", "start"],
        },
        fn=create_event,
    )


def make_list_tool(conn: sqlite3.Connection, home: Path) -> Tool:
    def list_events(start: str = "", end: str = "", limit: int = 20) -> str:
        query = 'SELECT title, start, "end", attendees FROM calendar_events'
        clauses: list[str] = []
        params: list = []
        if start:
            folded = normalize(start).strip()
            if len(folded) < 10:
                return (
                    f"Could not parse start filter {start!r} as an ISO date "
                    "(e.g. 2026-07-14). Ambiguous filters are not invented."
                )
            clauses.append("start >= ?")
            params.append(folded[:10])
        if end:
            folded = normalize(end).strip()
            if len(folded) < 10:
                return (
                    f"Could not parse end filter {end!r} as an ISO date "
                    "(e.g. 2026-07-14). Ambiguous filters are not invented."
                )
            clauses.append("start <= ?")
            params.append(folded[:10] + "T23:59")
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY start LIMIT ?"
        params.append(max(1, min(int(limit or 20), 100)))
        rows = conn.execute(query, params).fetchall()
        if not rows:
            window = f" between {start} and {end}" if (start or end) else ""
            return (
                f"No events found{window}. "
                f"(This reads the local calendar in {home / 'state.db'}.)"
            )
        lines = ["Events on the local calendar:"]
        for r in rows:
            who = f" with {r['attendees']}" if r["attendees"] else ""
            lines.append(f"- {r['title']}: {r['start']} → {r['end']}{who}")
        return "\n".join(lines)

    return Tool(
        name="list_events",
        description=(
            "Read the user's calendar: list events, optionally within a date range. "
            "Use whenever the user asks what's on their calendar / schedule for a day, "
            "week, yesterday, etc. Dates are ISO (e.g. 2026-07-10); omit both to list "
            "everything upcoming. For 'yesterday'/'today' resolve the date from the "
            "current time given in your system prompt."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "start": {
                    "type": "string",
                    "description": "earliest date to include, ISO (e.g. 2026-07-10)",
                },
                "end": {
                    "type": "string",
                    "description": "latest date to include, ISO (e.g. 2026-07-10)",
                },
                "limit": {
                    "type": "integer",
                    "description": "max events to return (default 20)",
                },
            },
            "required": [],
        },
        fn=list_events,
    )
