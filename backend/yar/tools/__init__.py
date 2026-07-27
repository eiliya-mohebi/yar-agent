"""The agent's tools. Calendar (flagship), notes/outbox/search, memory admin."""

from __future__ import annotations

import sqlite3

from yar.config import Settings
from yar.tools import calendar, memory_admin, messages, notes, search
from yar.tools.registry import ToolRegistry


def build_registry(
    conn: sqlite3.Connection, settings: Settings, memory=None
) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(calendar.make_tool(conn, settings.home))
    registry.register(calendar.make_list_tool(conn, settings.home))
    registry.register(notes.make_tool(conn))
    registry.register(messages.make_tool(settings.home))
    registry.register(search.make_tool())

    # Memory self-management — only when Memory is wired (evals can omit it).
    if memory is not None:
        registry.register(memory_admin.make_manage_memory_tool(memory))
        registry.register(memory_admin.make_update_soul_tool(settings))
        registry.register(memory_admin.make_create_skill_tool(settings, memory))

    return registry
