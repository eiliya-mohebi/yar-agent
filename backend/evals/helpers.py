"""Shared eval plumbing: a scripted fake LLM client for offline tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace


def _has_key() -> bool:
    """True when OPENAI_API_KEY or YAR_API_KEY is set (live AvalAI smoke)."""
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("YAR_API_KEY"))


HAS_KEY = _has_key()


def text_response(text: str):
    """OpenAI chat.completions-shaped response with assistant text only."""
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=text, tool_calls=None),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=0, completion_tokens=0),
    )


def gate_skip(reason: str = "test"):
    """Scripted small-model reply: retrieval gate says skip."""
    return text_response(
        f'{{"retrieve": false, "query": "", "reason": "{reason}"}}'
    )


def gate_retrieve(query: str, reason: str = "needs memory"):
    """Scripted small-model reply: retrieval gate says retrieve."""
    return text_response(
        f'{{"retrieve": true, "query": "{query}", "reason": "{reason}"}}'
    )


def tool_response(name: str, args: dict, call_id: str = "call_1"):
    """OpenAI-shaped response that requests one tool call."""
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[
                        SimpleNamespace(
                            id=call_id,
                            type="function",
                            function=SimpleNamespace(
                                name=name, arguments=json.dumps(args)
                            ),
                        )
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=0, completion_tokens=0),
    )


class ScriptedClient:
    """Plays back a fixed list of OpenAI-shaped responses — offline 'model'."""

    def __init__(self, script: list):
        self._script = list(script)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        if not self._script:
            raise LookupError("ScriptedClient: no more scripted responses")
        return self._script.pop(0)


def make_yar(home: Path, client=None, **settings_overrides):
    """Build a Yar with an isolated home dir; optionally swap in a fake client."""
    from yar.app import Yar
    from yar.config import Settings

    settings = Settings(home=home, **settings_overrides)
    if client is not None and not settings.api_key:
        settings.api_key = "offline"  # never require a real key for scripted runs
    return Yar(settings=settings, client=client)
