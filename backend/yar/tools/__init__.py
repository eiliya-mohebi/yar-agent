"""The agent's tools. Calendar (flagship) plus notes, outbox, and web search."""

from __future__ import annotations

import sqlite3

from yar.config import Settings
from yar.tools import calendar, messages, notes, search
from yar.tools.registry import ToolRegistry


def build_registry(conn: sqlite3.Connection, settings: Settings) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(calendar.make_tool(conn, settings.home))
    registry.register(calendar.make_list_tool(conn, settings.home))
    registry.register(notes.make_tool(conn))
    registry.register(messages.make_tool(settings.home))
    registry.register(search.make_tool())
    return registry
