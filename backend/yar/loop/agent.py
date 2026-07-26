"""THE LOOP — reason → act → observe. This file is the whole trick.

Every agent framework is ultimately this while-loop with more indirection:

    while not done:
        response = llm(messages, tools)          # reason
        if response asks for tools:
            results = run(tool_calls)            # act
            messages += results                  # observe
        else:
            done                                 # reply to the human

End-loop guardrails:
  1. the model stops asking for tools  → natural end of turn
  2. max_iterations reached            → hard stop, never spin forever

Wire format is OpenAI chat.completions end to end (role: tool, tool_calls).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

# Observers let the gateway show tool calls live and let ops/tracing record
# them — without either being wired into the loop's logic.
LoopEvent = dict[str, Any]
Observer = Callable[[str, LoopEvent], None]


class ToolSurface(Protocol):
    def schemas(self) -> list[dict]: ...
    def execute(self, name: str, args: dict) -> str: ...


@dataclass
class LoopResult:
    reply: str
    tool_calls: list[LoopEvent] = field(default_factory=list)
    iterations: int = 0


def run_loop(
    client: Any,
    model: str,
    messages: list[dict],
    tools: ToolSurface,
    max_iterations: int = 10,
    max_tokens: int = 8192,
    observer: Observer | None = None,
    stream: bool = False,
) -> LoopResult:
    """Run one agent turn. `messages` is mutated in place — after the call it
    contains the full working memory of the turn (assistant thoughts, tool
    calls, tool results), which is exactly what gets traced.

    The system prompt is messages[0] when present — there is no separate
    system kwarg. stream=True emits text deltas via notify("text",
    {"delta": ...}); any streaming hiccup falls back to a single call."""
    notify = observer or (lambda kind, ev: None)
    result = LoopResult(reply="")
    completions = client.chat.completions
    can_stream = stream and hasattr(completions, "stream")

    for iteration in range(1, max_iterations + 1):
        result.iterations = iteration
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_completion_tokens": max_tokens,
        }
        schemas = tools.schemas()
        if schemas:
            kwargs["tools"] = schemas

        # ---- reason: one LLM call with the current working memory
        response = None
        if can_stream:
            try:
                with completions.stream(**kwargs) as s:
                    for delta in s.text_stream:
                        notify("text", {"delta": delta})
                    response = s.get_final_response()
            except Exception:
                response = None  # any streaming hiccup → fall back to one call
        if response is None:
            response = completions.create(**kwargs)

        choice = response.choices[0]
        message = choice.message
        usage = getattr(response, "usage", None)
        notify(
            "llm",
            {
                "iteration": iteration,
                "stop_reason": getattr(choice, "finish_reason", None),
                "usage": {
                    "in": getattr(usage, "prompt_tokens", 0),
                    "out": getattr(usage, "completion_tokens", 0),
                },
            },
        )

        # the assistant's turn joins working memory (OpenAI dict shape)
        messages.append(_assistant_message(message))
        tool_calls = list(getattr(message, "tool_calls", None) or [])

        # ---- guardrail 1: no tool calls → the model is talking to the human
        if not tool_calls:
            result.reply = message.content or ""
            return result

        # ---- act: execute each requested tool; observe: feed results back
        for call in tool_calls:
            args = json.loads(call.function.arguments or "{}")
            output = tools.execute(call.function.name, args)
            event = {"tool": call.function.name, "args": args, "output": output}
            result.tool_calls.append(event)
            notify("tool", event)
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": output}
            )

    # ---- guardrail 2: ran out of iterations
    result.reply = (
        "(I hit my iteration limit before finishing — try breaking the "
        "request into smaller steps.)"
    )
    return result


def _assistant_message(message: Any) -> dict:
    entry: dict[str, Any] = {"role": "assistant", "content": message.content}
    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        entry["tool_calls"] = [
            {
                "id": c.id,
                "type": "function",
                "function": {
                    "name": c.function.name,
                    "arguments": c.function.arguments,
                },
            }
            for c in tool_calls
        ]
    return entry
