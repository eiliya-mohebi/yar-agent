"""Reset .yar to a clean, curated state for a demo / recording.

    python scripts/demo_seed.py --yes                 # clean slate, KEEPS spend ledger
    python scripts/demo_seed.py --yes --reset-spend   # also wipe usage.jsonl

What it does (your old state is backed up first, never just deleted):
  1. copies the current .yar aside to .yar.bak-<timestamp>
  2. clears calendar / traces / outbox / skills / eval history in place
  3. seeds a small, clean memory and ONE calendar event
  4. never deletes usage.jsonl unless --reset-spend

Permission never carries over — refuse without --yes every run.
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime

from yar.config import load_settings
from yar.db import connect
from yar.memory.episodic.store import SqliteEpisodeStore
from yar.memory.semantic.store import SqliteFactStore
from yar.tools.calendar import make_tool

FACTS = [
    (
        "user",
        "The user is building Yar (یار), a local-first personal assistant. "
        "They care about clear, honest code and bilingual Persian/English support.",
    ),
    (
        "raj",
        "Raj is a close friend who plays really great tennis and always teaches "
        "great British slang.",
    ),
    (
        "sergey",
        "Sergey is the close friend who loves swimming and often cooks delicious food.",
    ),
]
EPISODE = ("2026-07-11", "Confirmed the standing Saturday 5 PM swim with Sergey.")
EVENT = {
    "title": "Swim with Sergey",
    "start": "2026-07-11T17:00",
    "end": "2026-07-11T18:00",
    "attendees": "Sergey",
}


def main(reset_spend: bool = False) -> None:
    settings = load_settings()
    home = settings.home

    if home.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = home.with_name(f"{home.name}.bak-{stamp}")
        shutil.copytree(home, backup)
        print(f"backed up {home} -> {backup}")
        (home / "calendar.ics").unlink(missing_ok=True)
        for sub in ("outbox", "skills", "traces"):
            d = home / sub
            if d.exists():
                shutil.rmtree(d)
        (home / "eval_runs.jsonl").unlink(missing_ok=True)
        (home / "eval_report.json").unlink(missing_ok=True)
        # Permanent spend ledger — only wiped on explicit request.
        if reset_spend:
            (home / "usage.jsonl").unlink(missing_ok=True)

    settings.ensure_home()
    conn = connect(home)

    # Clear DB rows in place — never delete state.db (live gateways hold the inode).
    for table in ("chat_log", "calendar_events", "facts", "episodes"):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()

    facts, episodes = SqliteFactStore(conn), SqliteEpisodeStore(conn)
    for subject, content in FACTS:
        facts.add(subject, content, source="user")
    episodes.add(EPISODE[1], happened_at=EPISODE[0])

    create_event = make_tool(conn, home).fn
    print(create_event(**EVENT))

    from yar.memory import Memory

    Memory(conn, settings, None).export_markdown()

    print(f"\nclean demo state ready in {home}")
    print(f"  facts: {len(FACTS)}  ·  episodes: 1  ·  events: 1  ·  chat log: cleared")
    print("  CLEARED: loop/tool traces, Ops eval history, outbox, skills.")
    if reset_spend:
        print("  CLEARED: usage.jsonl (money/token spend) — you approved this.")
    else:
        print(
            "  KEPT: SOUL.md and usage.jsonl "
            "(your real spend — pass --reset-spend to wipe)."
        )
    print("  Run `yar dashboard` and start filming.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset .yar to a clean demo state.")
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="required confirmation: yes, wipe .yar (it is backed up first)",
    )
    parser.add_argument(
        "--reset-spend",
        action="store_true",
        help="also wipe usage.jsonl (the money/token spend ledger)",
    )
    args = parser.parse_args()
    if not args.yes:
        print(
            "REFUSING to run: demo_seed clears .yar (memory, calendar, chat, traces"
            + (", AND spend" if args.reset_spend else "")
            + ")."
        )
        print("This is destructive. If you truly mean it, re-run with --yes:")
        print(
            "    python scripts/demo_seed.py --yes"
            + (" --reset-spend" if args.reset_spend else "")
        )
        raise SystemExit(2)
    main(reset_spend=args.reset_spend)
