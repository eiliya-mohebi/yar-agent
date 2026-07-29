"""LLM-as-referee quality scoring for the Compare arena.

Completion (yar.ops.scoring) is deterministic — did the right tool fire. Quality
is the other half: how good was the answer. An LLM grades 0–10 + a one-line
reason. Default judge is YAR_JUDGE_MODEL (gpt-5.6-sol) — OpenAI chat.completions
only. A judge hiccup must never fail a race.
"""

from __future__ import annotations

import json
import os
import threading
import time

from yar.config import Settings, load_settings
from yar.loop.models import get_client

JUDGE_MODEL = os.getenv("YAR_JUDGE_MODEL", "gpt-5.6-sol")
_JUDGE_SEM = threading.Semaphore(int(os.getenv("YAR_JUDGE_CONCURRENCY", "2")))

_RUBRIC = """You are a strict, fair judge scoring an AI assistant's reply.

The user asked:
{task}

The assistant replied:
{reply}
{actions}
Score how well the reply serves the user's request on a 0-10 scale:
- 9-10: fully addresses the request, correct, concise, honest about any limits.
- 5-8: mostly addresses it, minor gaps, padding, or small errors.
- 1-4: partial, vague, or partly wrong.
- 0: ignores the request, or claims an action that is NOT in the tool list above.

IMPORTANT: the tools listed above REALLY ran — this assistant can take those
actions. Do NOT penalize the reply for saying it did something that appears in
that list; those claims are true. Only "hallucinating" counts against it when it
claims an action with no matching tool call.

Reply with ONLY a JSON object, no prose:
{{"score": <int 0-10>, "reason": "<one short sentence>"}}"""


def judge_reply(
    task: str,
    reply: str,
    model: str | None = None,
    tools: list | None = None,
) -> dict | None:
    """Grade one reply. Returns {score, reason, judge} or None on failure."""
    if not (reply or "").strip():
        return None
    model = model or JUDGE_MODEL
    # History may store tools as name strings or {tool: name} dicts.
    names = []
    for t in tools or []:
        if isinstance(t, dict):
            names.append(t.get("tool") or "")
        else:
            names.append(str(t))
    names = [n for n in names if n]
    actions = (
        f"\nTools the assistant actually ran this turn (ground truth): "
        f"{', '.join(names)}.\n"
        if names
        else "\nThe assistant ran no tools this turn.\n"
    )
    prompt = _RUBRIC.format(task=task[:2000], reply=reply[:4000], actions=actions)
    base = load_settings()
    settings = Settings(
        api_key=base.api_key,
        base_url=base.base_url,
        model=model,
        small_model="",
        home=base.home,
    )
    resp = None
    for attempt in range(4):
        try:
            client = get_client(settings)
            with _JUDGE_SEM:
                resp = client.chat.completions.create(
                    model=settings.model,
                    max_completion_tokens=300,
                    messages=[{"role": "user", "content": prompt}],
                )
            break
        except Exception:
            if attempt < 3:
                time.sleep(1.2 * (attempt + 1))
    if resp is None:
        return None
    try:
        text = (resp.choices[0].message.content or "").strip()
        obj = json.loads(text[text.index("{") : text.rindex("}") + 1])
        score = max(0, min(10, int(obj["score"])))
        return {
            "score": score,
            "reason": str(obj.get("reason", ""))[:200],
            "judge": settings.model,
        }
    except Exception:
        return None
