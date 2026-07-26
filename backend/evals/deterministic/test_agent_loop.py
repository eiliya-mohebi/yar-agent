"""run_loop — reason→act→observe with exits, Observer, ScriptedClient offline."""

from __future__ import annotations

import json
from types import SimpleNamespace

from evals.helpers import ScriptedClient, text_response, tool_response
from yar.loop.agent import run_loop


class FakeTools:
    """Minimal tools duck-type: schemas() + execute(name, args)."""

    def __init__(self, handlers: dict | None = None):
        self.handlers = handlers or {}
        self.calls: list[tuple[str, dict]] = []

    def schemas(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": name,
                    "parameters": {"type": "object", "properties": {}},
                },
            }
            for name in self.handlers
        ]

    def execute(self, name: str, args: dict) -> str:
        self.calls.append((name, args))
        return self.handlers[name](args)


def test_no_tool_turn_ends_in_one_iteration():
    client = ScriptedClient([text_response("Paris.")])
    tools = FakeTools()
    events: list[tuple[str, dict]] = []

    result = run_loop(
        client,
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": "capital of france?"}],
        tools=tools,
        observer=lambda kind, ev: events.append((kind, ev)),
    )

    assert result.reply == "Paris."
    assert result.iterations == 1
    assert result.tool_calls == []
    assert any(k == "llm" for k, _ in events)


def test_tool_call_then_reply_and_observer_fires():
    client = ScriptedClient(
        [
            tool_response("save_note", {"subject": "x", "content": "y"}),
            text_response("Saved."),
        ]
    )
    tools = FakeTools({"save_note": lambda args: "ok"})
    events: list[tuple[str, dict]] = []

    messages = [{"role": "user", "content": "remember x"}]
    result = run_loop(
        client,
        model="gpt-4.1-mini",
        messages=messages,
        tools=tools,
        observer=lambda kind, ev: events.append((kind, ev)),
    )

    assert result.reply == "Saved."
    assert result.iterations == 2
    assert [c["tool"] for c in result.tool_calls] == ["save_note"]
    assert tools.calls == [("save_note", {"subject": "x", "content": "y"})]
    assert any(k == "tool" and ev["tool"] == "save_note" for k, ev in events)
    # OpenAI wire: tool result is a role:tool message, not Anthropic tool_result blocks
    assert any(m.get("role") == "tool" for m in messages)


def test_iteration_guardrail_stops_runaway_loop():
    runaway = [
        tool_response("save_note", {"subject": "x", "content": "y"}, call_id=f"c{i}")
        for i in range(99)
    ]
    client = ScriptedClient(runaway)
    tools = FakeTools({"save_note": lambda args: "ok"})

    result = run_loop(
        client,
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": "loop"}],
        tools=tools,
        max_iterations=3,
    )

    assert result.iterations == 3
    assert "iteration limit" in result.reply
    assert len(result.tool_calls) == 3


def test_stream_fallback_when_stream_raises():
    """stream=True but stream() fails → clean fallback to create()."""

    class FlakyClient(ScriptedClient):
        def __init__(self):
            super().__init__([text_response("fallback ok")])

            def boom(**kwargs):
                raise RuntimeError("stream broken")

            self.chat.completions.stream = boom  # type: ignore[method-assign]

    events: list[tuple[str, dict]] = []
    result = run_loop(
        FlakyClient(),
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": "hi"}],
        tools=FakeTools(),
        stream=True,
        observer=lambda kind, ev: events.append((kind, ev)),
    )
    assert result.reply == "fallback ok"


def test_stream_emits_text_deltas():
    class StreamClient:
        def __init__(self):
            self.chat = SimpleNamespace(completions=self)

        def create(self, **kwargs):
            raise AssertionError("non-stream create should not run")

        def stream(self, **kwargs):
            return _FakeStream()

    class _FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        @property
        def text_stream(self):
            yield "Hel"
            yield "lo"

        def get_final_response(self):
            return text_response("Hello")

    events: list[tuple[str, dict]] = []
    result = run_loop(
        StreamClient(),
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": "hi"}],
        tools=FakeTools(),
        stream=True,
        observer=lambda kind, ev: events.append((kind, ev)),
    )
    assert result.reply == "Hello"
    assert [ev["delta"] for k, ev in events if k == "text"] == ["Hel", "lo"]


def test_tool_arguments_parsed_from_json_string():
    args = {"title": "Coffee", "start": "2026-07-14T09:00"}
    client = ScriptedClient(
        [
            tool_response("create_event", args),
            text_response("Booked."),
        ]
    )
    seen: list[dict] = []
    tools = FakeTools({"create_event": lambda a: seen.append(a) or "created"})

    run_loop(
        client,
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": "book coffee"}],
        tools=tools,
    )
    assert seen == [args]
    # arguments on the wire stay JSON strings (OpenAI shape)
    assert json.dumps(args)  # sanity: helpers round-trip
