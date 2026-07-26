"""Offline seam tests for SQLite schema + bilingual fact/episode stores (§7)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from yar.db import connect
from yar.memory.episodic.store import SqliteEpisodeStore
from yar.memory.semantic.store import SqliteFactStore


@pytest.fixture
def home(tmp_path: Path) -> Path:
    home = tmp_path / ".yar"
    home.mkdir()
    return home


@pytest.fixture
def conn(home: Path) -> sqlite3.Connection:
    return connect(home)


def test_connect_creates_schema_tables_and_fts(conn: sqlite3.Connection):
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
        ).fetchall()
    }
    for name in (
        "calendar_events",
        "facts",
        "facts_fts",
        "episodes",
        "episodes_fts",
        "chat_log",
    ):
        assert name in tables


def test_migrate_adds_chat_log_columns_idempotently(tmp_path: Path):
    """Older homes without source/meta still upgrade; second connect is a no-op."""
    home = tmp_path / "old-home"
    home.mkdir()
    raw = sqlite3.connect(home / "state.db")
    raw.executescript(
        """
        CREATE TABLE chat_log (
            id INTEGER PRIMARY KEY,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            consolidated INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    raw.close()

    c1 = connect(home)
    cols = {r[1] for r in c1.execute("PRAGMA table_info(chat_log)").fetchall()}
    assert {"session_id", "source", "meta"} <= cols
    c1.close()

    c2 = connect(home)
    cols2 = {r[1] for r in c2.execute("PRAGMA table_info(chat_log)").fetchall()}
    assert cols2 == cols
    c2.close()


def test_persian_fact_round_trip(conn: sqlite3.Connection):
    store = SqliteFactStore(conn)
    store.add("کاربر", "علی قهوه دوست دارد")
    hits = store.search("قهوه علی")
    assert hits
    assert any("قهوه" in h for h in hits)


def test_arabic_letter_folding_retrieves_same_fact(conn: sqlite3.Connection):
    store = SqliteFactStore(conn)
    # Write Persian, query Arabic codepoints.
    store.add("person", "علی کتاب می‌خواند")
    hits = store.search("علي كتاب")
    assert hits
    assert any("کتاب" in h for h in hits)

    # Write Arabic, query Persian — normalize-on-write must fold both ways.
    store.add("person2", "علي يحب كتاب")
    hits2 = store.search("علی کتاب")
    assert hits2
    assert any("علی" in h and "کتاب" in h for h in hits2)


def test_digit_folding_retrieves_same_fact(conn: sqlite3.Connection):
    store = SqliteFactStore(conn)
    # min_len=2 drops single digits; multi-digit forms must fold both ways.
    store.add("schedule", "جلسه اتاق ۴۲")
    hits = store.search("42")
    assert hits
    assert any("42" in h for h in hits)


def test_mixed_script_fact_round_trip(conn: sqlite3.Connection):
    store = SqliteFactStore(conn)
    store.add("plans", "book جلسه with Alex فردا")
    hits = store.search("جلسه Alex")
    assert hits
    assert any("جلسه" in h and "Alex" in h for h in hits)


def test_zwnj_stem_is_searchable(conn: sqlite3.Connection):
    store = SqliteFactStore(conn)
    # ZWNJ kept on write; FTS unicode61 splits so stem "جلسه" matches.
    store.add("meetings", "جلسه‌های هفتگی")
    hits = store.search("جلسه")
    assert hits


def test_empty_fact_query_returns_empty(conn: sqlite3.Connection):
    store = SqliteFactStore(conn)
    store.add("x", "something memorable")
    assert store.search("؟؟") == []


def test_episode_search_and_empty_falls_back_to_recent(conn: sqlite3.Connection):
    store = SqliteEpisodeStore(conn)
    store.add("گفتگو درباره پروژه یار", "2026-07-20")
    store.add("English standup notes", "2026-07-21")
    hits = store.search("یار")
    assert hits
    assert any("یار" in h for h in hits)

    recent = store.search("؟؟", top_k=1)
    assert len(recent) == 1
    assert "2026-07-21" in recent[0]
