"""Consolidation — distill chats into durable memory, but only sometimes.

Batch every N exchanges so the summarizer has enough context. A cheap model
reads unconsolidated chat_log rows and produces facts + one episode, then
marks those rows consolidated=1.

Loss-safe: on summarizer/parse failure, return 0 and leave rows unmarked.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from yar.memory.episodic.store import SqliteEpisodeStore
from yar.memory.semantic.store import SqliteFactStore

# Lifted from waku, plus §7: keep fact/episode text in the source language.
SUMMARIZER_PROMPT = """\
You distill a personal assistant's recent conversation into long-term memory.

From the exchanges below, extract:
1. durable facts about the user, their people, projects, or preferences —
   only things worth remembering in a month; skip chit-chat and one-offs.
2. one single-sentence episode summarizing what happened in this conversation.

Exchanges may be in Persian (فارسی), English, or mixed. Reply with ONLY this
JSON (English keys). Write each fact's subject/content and the episode in the
language of the source text — do not translate Persian into English (Persian
queries must still retrieve them):
{{"facts": [{{"subject": "<who/what>", "content": "<one sentence>"}}], "episode": "<one sentence>"}}

Exchanges:
{log}"""


def _completion_text(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    return getattr(choices[0].message, "content", None) or ""


def consolidate_if_due(
    conn,
    client: Any,
    small_model: str,
    every_n: int,
    facts: SqliteFactStore,
    episodes: SqliteEpisodeStore,
) -> int:
    """Returns how many new facts were written (0 = not due or nothing kept)."""
    rows = conn.execute(
        "SELECT id, role, content FROM chat_log WHERE consolidated = 0 ORDER BY id"
    ).fetchall()
    if len(rows) < every_n * 2:  # each exchange = 2 rows (user + assistant)
        return 0

    log = "\n".join(f"{r['role']}: {r['content']}" for r in rows)
    try:
        response = client.chat.completions.create(
            model=small_model,
            max_completion_tokens=600,
            messages=[{"role": "user", "content": SUMMARIZER_PROMPT.format(log=log)}],
        )
        text = _completion_text(response)
        distilled = json.loads(text[text.index("{") : text.rindex("}") + 1])
    except Exception:
        return 0  # never lose the log — stays unconsolidated for next time

    for fact in distilled.get("facts", []):
        if fact.get("subject") and fact.get("content"):
            facts.add(fact["subject"], fact["content"], source="consolidation")
    if distilled.get("episode"):
        episodes.add(distilled["episode"], happened_at=date.today().isoformat())

    conn.execute(
        f"UPDATE chat_log SET consolidated = 1 WHERE id IN ({','.join('?' * len(rows))})",
        [r["id"] for r in rows],
    )
    conn.commit()
    return len(distilled.get("facts", []))
