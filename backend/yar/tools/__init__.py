"""The agent's tools. Calendar (flagship), notes/outbox/search, memory admin,
and opt-in adapters: experimental (YAR_EXPERIMENTAL=1) and MCP (.yar/mcp.json)."""

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

    # Experimental — off by default; opt in with YAR_EXPERIMENTAL=1.
    if settings.experimental:
        from yar.tools import experimental

        for t in experimental.make_tools(settings):
            registry.register(t)

    # MCP servers (opt-in via .yar/mcp.json + [mcp] extra).
    mcp_config = settings.home / "mcp.json"
    if mcp_config.exists():
        try:
            from yar.tools.mcp_client import MCPBridge

            bridge = MCPBridge(mcp_config)
            for t in bridge.start():
                registry.register(t)
            registry.mcp_bridge = bridge  # so Yar.close() can stop the servers
        except ImportError as exc:
            raise ImportError(
                "mcp.json found but the 'mcp' package is missing — "
                "install with: uv sync --extra mcp"
            ) from exc

    return registry
