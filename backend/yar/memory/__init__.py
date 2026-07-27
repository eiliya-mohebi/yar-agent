"""Memory facade — chat_log + procedural skills; gate/consolidation arrive next.

    procedural  SKILL.md files      how to act
    semantic    facts table (FTS5)  what is true   (already in semantic/)
    episodic    episodes table      what happened  (already in episodic/)

gated_retrieve stays a no-op until the retrieval-gate issue.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from yar.config import Settings
from yar.memory.procedural.loader import SkillLoader

# Built-in skills live next to the package under backend/skills/.
REPO_SKILLS = Path(__file__).resolve().parents[2] / "skills"


class Memory:
    def __init__(self, conn: sqlite3.Connection, settings: Settings, client=None):
        self.conn = conn
        self.settings = settings
        self.client = client
        self.skills = SkillLoader([REPO_SKILLS, settings.home / "skills"])

    def gated_retrieve(self, message: str, notify=None) -> str:
        # Filled in by the retrieval-gate issue. Empty = skip memory section.
        return ""

    def matching_skills(self, message: str) -> str:
        matched = self.skills.match(message)
        return "\n\n".join(f"### {s.name}\n{s.body}" for s in matched)

    def log_chat(
        self,
        user_message: str,
        reply: str,
        session_id: str = "default",
        source: str = "cli",
        meta: dict | None = None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO chat_log (role, content, session_id, source) "
            "VALUES ('user', ?, ?, ?)",
            (user_message, session_id, source),
        )
        # meta (gate/latency/iterations/tools) rides on the assistant row so a
        # reopened thread can render the full turn card, not just the text.
        self.conn.execute(
            "INSERT INTO chat_log (role, content, session_id, source, meta) "
            "VALUES ('assistant', ?, ?, ?, ?)",
            (reply, session_id, source, json.dumps(meta) if meta else None),
        )
        self.conn.commit()

    def session_history(self, session_id: str) -> list[tuple[str, str]]:
        """The (user, assistant) exchanges of one past session, in order — used
        to reload working memory when the user switches back to a conversation."""
        rows = self.conn.execute(
            "SELECT role, content FROM chat_log WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        pairs, pending = [], None
        for r in rows:
            if r["role"] == "user":
                pending = r["content"]
            elif pending is not None:
                pairs.append((pending, r["content"]))
                pending = None
        return pairs

    def list_sessions(self) -> list[dict]:
        """One row per conversation: id, first user message (the title), message
        count, and when it started — newest first."""
        rows = self.conn.execute(
            """SELECT session_id,
                      COUNT(*) AS messages,
                      MIN(created_at) AS started_at,
                      MAX(created_at) AS last_at
               FROM chat_log GROUP BY session_id ORDER BY last_at DESC"""
        ).fetchall()
        out = []
        for r in rows:
            first = self.conn.execute(
                "SELECT content FROM chat_log WHERE session_id = ? AND role = 'user' "
                "ORDER BY id LIMIT 1",
                (r["session_id"],),
            ).fetchone()
            out.append(
                {
                    "id": r["session_id"],
                    "title": (first["content"][:60] if first else "(empty)"),
                    "messages": r["messages"],
                    "started_at": r["started_at"],
                    "last_at": r["last_at"],
                }
            )
        return out
