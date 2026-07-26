"""get_client — one OpenAI client, base_url from Settings, production quirks."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from yar.config import Settings
from yar.loop import models


def test_get_client_uses_settings_base_url_and_key(monkeypatch, tmp_path):
    captured = {}

    class StubOpenAI:
        def __init__(self, *, api_key, base_url, timeout):
            captured.update(api_key=api_key, base_url=base_url, timeout=timeout)

    monkeypatch.setattr(models, "OpenAI", StubOpenAI)
    settings = Settings(
        api_key="test-key",
        base_url="https://api.avalai.ir/v1",
        home=tmp_path,
    )

    client = models.get_client(settings)

    assert client is not None
    assert captured["api_key"] == "test-key"
    assert captured["base_url"] == "https://api.avalai.ir/v1"
    assert captured["timeout"] == 120.0
    assert captured["base_url"] != "https://api.openai.com/v1"


def test_get_client_requires_api_key(tmp_path):
    settings = Settings(api_key="", home=tmp_path)
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        models.get_client(settings)


def test_no_providers_table():
    assert not hasattr(models, "PROVIDERS")


def test_default_model_constants():
    assert models.DEFAULT_MODEL == "gpt-5.3-chat-latest"
    assert models.DEFAULT_SMALL_MODEL == "gpt-4.1-mini"


def _stub_client(monkeypatch) -> models.YarClient:
    monkeypatch.setattr(models, "OpenAI", lambda **kw: SimpleNamespace())
    return models.YarClient(api_key="k", base_url="https://api.avalai.ir/v1")


def test_empty_choices_raises_clear_error(monkeypatch):
    client = _stub_client(monkeypatch)
    resp = SimpleNamespace(choices=[], error="rate limited")
    client._call = lambda kwargs, **extra: resp

    with pytest.raises(RuntimeError, match="rate limited"):
        client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": "hi"}],
            max_completion_tokens=16,
        )

    client._call = lambda kwargs, **extra: SimpleNamespace(choices=[])
    with pytest.raises(RuntimeError, match="no choices"):
        client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": "hi"}],
            max_completion_tokens=16,
        )


def test_max_completion_tokens_retries_as_max_tokens(monkeypatch):
    client = _stub_client(monkeypatch)
    calls: list[dict] = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        if "max_completion_tokens" in kwargs:
            raise ValueError("Unsupported parameter: 'max_completion_tokens'")
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="ok", tool_calls=None),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        )

    client._raw = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )

    out = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": "hi"}],
        max_completion_tokens=16,
    )
    assert out.choices[0].message.content == "ok"
    assert "max_completion_tokens" in calls[0]
    assert "max_tokens" in calls[1]
    assert "max_completion_tokens" not in calls[1]


def test_stream_reassembles_tool_call_argument_fragments(monkeypatch):
    client = _stub_client(monkeypatch)

    def chunks():
        yield SimpleNamespace(
            usage=None,
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(
                        content=None,
                        tool_calls=[
                            SimpleNamespace(
                                index=0,
                                id="call_1",
                                function=SimpleNamespace(name="create_event", arguments='{"ti'),
                            )
                        ],
                    )
                )
            ],
        )
        yield SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=2, completion_tokens=3),
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(
                        content=None,
                        tool_calls=[
                            SimpleNamespace(
                                index=0,
                                id=None,
                                function=SimpleNamespace(name=None, arguments='tle":"x"}'),
                            )
                        ],
                    )
                )
            ],
        )

    client._call = lambda kwargs, **extra: chunks()

    with client.chat.completions.stream(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": "hi"}],
        max_completion_tokens=16,
    ) as s:
        list(s.text_stream)  # drain
        final = s.get_final_response()

    call = final.choices[0].message.tool_calls[0]
    assert call.id == "call_1"
    assert call.function.name == "create_event"
    assert call.function.arguments == '{"title":"x"}'
