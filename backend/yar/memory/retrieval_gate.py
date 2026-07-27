"""HERO MOMENT #1 — the gate that decides WHETHER to retrieve memory at all.

Default-on retrieval is (a) slow and (b) biases answers with irrelevant
memories. A cheap model answers: does THIS message need the user's memory?
"what's 2+2" → no. "when am I meeting Alex?" → yes, with a search query.

Fails open: parse/LLM error → retrieve anyway (a stale memory beats a lost one).
"""

from __future__ import annotations

import json
from typing import Any

# Lifted from waku, plus §7 bilingual rules: input may be Persian; JSON keys
# stay English; query values stay in the source language so FTS can match.
GATE_PROMPT = """\
You are a retrieval gate for a personal assistant's long-term memory.
Given the user's message, decide if answering well requires the user's stored
memories (facts about people, projects, preferences, or past events).

The message may be in Persian (فارسی), English, or mixed. Reply with ONLY this
JSON (English keys); if retrieve is true, write "query" in the same language
as the user's message so keyword search can match stored facts:
{{"retrieve": true/false, "query": "<search keywords if true, else empty>", "reason": "<5 words>"}}

General knowledge, math, small talk, or self-contained requests → false.
Anything referencing the user's life, people, plans, or history → true.

User message: {message}"""


def _completion_text(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    return getattr(choices[0].message, "content", None) or ""


def should_retrieve(
    client: Any, small_model: str, message: str
) -> tuple[bool, str, str]:
    """Returns (retrieve?, search_query, reason). Fails open on any error."""
    try:
        response = client.chat.completions.create(
            model=small_model,
            # generous budget: reasoning models spend tokens before the JSON
            max_completion_tokens=600,
            messages=[{"role": "user", "content": GATE_PROMPT.format(message=message)}],
        )
        text = _completion_text(response)
        if "{" not in text:  # reasoning-only / truncated reply, not an error
            return True, message, "gate returned no JSON — failing open"
        decision = json.loads(text[text.index("{") : text.rindex("}") + 1])
        return (
            bool(decision.get("retrieve")),
            decision.get("query", message),
            decision.get("reason", ""),
        )
    except Exception as exc:
        return True, message, f"gate failed open ({type(exc).__name__})"
