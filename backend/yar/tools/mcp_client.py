"""MCP connector — plug any Model Context Protocol server into Yar's tools.

Yar's loop is synchronous; the MCP SDK is async. This bridge runs one asyncio
event loop on a daemon thread and lets the sync loop call tools via
run_coroutine_threadsafe.

Config: $YAR_HOME/mcp.json
  {"servers": [{"name": "fs", "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "env": {}}]}

Each server's tools register as `<server>_<tool>`. A server that fails to
connect is skipped with a warning — Yar still starts. Requires the `[mcp]` extra.
"""

from __future__ import annotations

import asyncio
import json
import threading
from contextlib import AsyncExitStack
from pathlib import Path

from yar.tools.registry import Tool


class MCPBridge:
    def __init__(self, config_path: Path, timeout: float = 30.0):
        self.config_path = config_path
        self.timeout = timeout
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._stack: AsyncExitStack | None = None
        self._sessions: dict = {}

    def start(self) -> list[Tool]:
        """Connect every configured server and return their tools."""
        # Fail fast with a clear message if the [mcp] extra isn't installed.
        try:
            import mcp  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "mcp.json found but the 'mcp' package is missing — "
                "install with: uv sync --extra mcp"
            ) from exc
        self._thread.start()
        servers = json.loads(self.config_path.read_text()).get("servers", [])
        fut = asyncio.run_coroutine_threadsafe(self._connect_all(servers), self._loop)
        listed = fut.result(self.timeout * 2)
        tools: list[Tool] = []
        for srv, metas in listed.items():
            for meta in metas:
                tools.append(
                    Tool(
                        name=f"{srv}_{meta['name']}",
                        description=f"[MCP:{srv}] {meta.get('description', '') or ''}",
                        input_schema=meta.get("inputSchema")
                        or {"type": "object", "properties": {}},
                        fn=(
                            lambda srv=srv, tname=meta["name"], **kw: self.call(
                                srv, tname, kw
                            )
                        ),
                    )
                )
        return tools

    async def _connect_all(self, servers) -> dict:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        self._stack = AsyncExitStack()
        listed: dict = {}
        for spec in servers:
            name = spec["name"]
            try:
                params = StdioServerParameters(
                    command=spec["command"],
                    args=spec.get("args", []),
                    env=spec.get("env") or None,
                )
                read, write = await self._stack.enter_async_context(stdio_client(params))
                session = await self._stack.enter_async_context(
                    ClientSession(read, write)
                )
                await session.initialize()
                self._sessions[name] = session
                tools = (await session.list_tools()).tools
                listed[name] = [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.inputSchema,
                    }
                    for t in tools
                ]
            except Exception as exc:
                print(f"MCP server '{name}' failed to connect: {exc}")
        return listed

    def call(self, server: str, tool: str, args: dict) -> str:
        try:
            fut = asyncio.run_coroutine_threadsafe(
                self._acall(server, tool, args), self._loop
            )
            return fut.result(self.timeout)
        except Exception as exc:
            return f"MCP call {server}_{tool} failed: {exc}"

    async def _acall(self, server: str, tool: str, args: dict) -> str:
        session = self._sessions.get(server)
        if session is None:
            return f"MCP server '{server}' is not connected."
        result = await session.call_tool(tool, args)
        parts = []
        for block in result.content:
            parts.append(getattr(block, "text", None) or "[non-text content]")
        return "\n".join(parts) or "(no output)"

    def close(self) -> None:
        if self._stack is not None:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._stack.aclose(), self._loop
                ).result(10)
            except Exception:
                pass
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)
