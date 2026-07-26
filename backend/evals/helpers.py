"""Shared eval plumbing: a scripted fake LLM client for offline tests."""

from __future__ import annotations

import json
import os
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
