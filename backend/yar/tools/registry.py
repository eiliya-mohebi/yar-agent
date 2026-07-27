"""Tool registry — name + description + JSON schema + Python fn.

schemas() emits OpenAI chat.completions function shape. execute() surfaces
errors as text so a bad tool call never crashes the loop.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable[..., str]  # tools return a string the model observes

    def to_api(self) -> dict[str, Any]:
        """OpenAI tools[] entry: type=function wrapping name/description/parameters."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def schemas(self) -> list[dict[str, Any]]:
        return [t.to_api() for t in self._tools.values()]

    def execute(self, name: str, args: dict[str, Any]) -> str:
        """Run one tool call safely: the model observes errors as text."""
        tool = self._tools.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'"
        try:
            return tool.fn(**args)
        except Exception as exc:  # surface, don't crash — the model can retry
            return f"Error running {name}: {exc}"
