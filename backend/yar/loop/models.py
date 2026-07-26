"""Model access — one provider (OpenAI), one wire format (chat.completions).

Client construction lives here. base_url comes from Settings (AvalAI by
default via YAR_BASE_URL). No PROVIDERS table, no Anthropic adapter — the
loop speaks OpenAI shape natively.

Production quirks that would otherwise break the tool loop:
  - prefer max_completion_tokens; retry as max_tokens only when the error
    mentions that param name
  - empty choices → clear RuntimeError (not choices[0] TypeError)
  - streaming reassembles incremental tool-call argument fragments
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

from openai import OpenAI

from yar.config import Settings

DEFAULT_MODEL = "gpt-5.3-chat-latest"
DEFAULT_SMALL_MODEL = "gpt-4.1-mini"


def get_client(settings: Settings) -> YarClient:
    """Build the OpenAI client from Settings. Fail clearly when no key."""
    settings.require_api_key()
    api_key = settings.api_key.strip()
    try:
        api_key.encode("latin-1")
    except UnicodeEncodeError as exc:
        raise SystemExit(
            "OPENAI_API_KEY (or YAR_API_KEY) contains a non-ASCII character "
            "(e.g. a smart quote from a bad paste). Re-paste the key with no "
            "spaces or line breaks."
        ) from exc

    timeout = float(os.getenv("YAR_LLM_TIMEOUT", "120"))
    return YarClient(api_key=api_key, base_url=settings.base_url, timeout=timeout)


class YarClient:
    """Thin OpenAI chat.completions wrapper with the quirks above.

    Duck-types as something with `.chat.completions.create(...)` and
    `.chat.completions.stream(...)` so ScriptedClient can stand in offline.
    """

    def __init__(self, api_key: str, base_url: str | None = None, timeout: float = 120.0):
        self._raw = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self.chat = SimpleNamespace(completions=_Completions(self))

    def _call(self, kwargs: dict[str, Any], **extra: Any):
        """chat.completions.create with max_tokens key-name fallback.

        Only retry when the error is ABOUT that param — retrying on any error
        masks the real failure under a confusing max_tokens message.
        """
        try:
            return self._raw.chat.completions.create(**kwargs, **extra)
        except Exception as exc:
            m = str(exc).lower()
            if "max_completion_tokens" not in m and "max_tokens" not in m:
                raise
            k = dict(kwargs)
            k["max_tokens"] = k.pop("max_completion_tokens", None)
            return self._raw.chat.completions.create(**k, **extra)


class _Completions:
    def __init__(self, client: YarClient):
        self._client = client

    def create(self, **kwargs: Any):
        response = self._client._call(kwargs)
        if not getattr(response, "choices", None):
            err = getattr(response, "error", None) or "endpoint returned no choices"
            model = kwargs.get("model", "?")
            raise RuntimeError(f"{model}: {err}")
        return response

    def stream(self, **kwargs: Any) -> _CompletionStream:
        return _CompletionStream(self._client, kwargs)


class _CompletionStream:
    """Context manager: iterate .text_stream for deltas, then
    .get_final_response() for the reassembled OpenAI-shaped completion
    (text + tool calls whose arguments arrived as partial JSON fragments)."""

    def __init__(self, client: YarClient, kwargs: dict[str, Any]):
        self._client = client
        self._kwargs = kwargs
        self._text: list[str] = []
        self._tools: dict[int, dict[str, str | None]] = {}
        self._usage = None

    def __enter__(self) -> _CompletionStream:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    @property
    def text_stream(self):
        stream = self._client._call(
            self._kwargs, stream=True, stream_options={"include_usage": True}
        )
        for chunk in stream:
            if getattr(chunk, "usage", None):
                self._usage = chunk.usage
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if getattr(delta, "content", None):
                self._text.append(delta.content)
                yield delta.content
            for tc in getattr(delta, "tool_calls", None) or []:
                slot = self._tools.setdefault(
                    tc.index, {"id": None, "name": "", "args": ""}
                )
                if tc.id:
                    slot["id"] = tc.id
                fn = getattr(tc, "function", None)
                if fn and fn.name:
                    slot["name"] = fn.name
                if fn and fn.arguments:
                    slot["args"] = (slot["args"] or "") + fn.arguments

    def get_final_response(self):
        text = "".join(self._text) or None
        tool_calls = []
        for slot in self._tools.values():
            tool_calls.append(
                SimpleNamespace(
                    id=slot["id"],
                    type="function",
                    function=SimpleNamespace(
                        name=slot["name"] or "",
                        arguments=slot["args"] or "{}",
                    ),
                )
            )
        usage = self._usage
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=text,
                        tool_calls=tool_calls or None,
                    ),
                    finish_reason="tool_calls" if tool_calls else "stop",
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=getattr(usage, "prompt_tokens", 0),
                completion_tokens=getattr(usage, "completion_tokens", 0),
            ),
        )
