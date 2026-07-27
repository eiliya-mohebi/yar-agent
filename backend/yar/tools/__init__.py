"""The agent's tools. Flagship calendar first; other tools land in later issues."""

from __future__ import annotations

import sqlite3

from yar.config import Settings
from yar.tools import calendar
from yar.tools.registry import ToolRegistry


def build_registry(conn: sqlite3.Connection, settings: Settings) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(calendar.make_tool(conn, settings.home))
    registry.register(calendar.make_list_tool(conn, settings.home))
    return registry
