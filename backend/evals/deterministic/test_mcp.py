"""DETERMINISTIC EVAL — MCP bridge stays opt-in; ImportError is clear."""

from __future__ import annotations

import sys

import pytest

from yar.config import Settings
from yar.db import connect
from yar.tools import build_registry


def test_mcp_absent_from_default_path(tmp_path):
    """No mcp.json → no MCP tools, no bridge, no ImportError."""
    settings = Settings(home=tmp_path / "home", api_key="test")
    settings.ensure_home()
    conn = connect(settings.home)
    registry = build_registry(conn, settings)
    assert getattr(registry, "mcp_bridge", None) is None
    assert registry.mcp_bridge is None
    assert not any(n.startswith("fs_") for n in registry._tools)


def test_mcp_missing_extra_raises_clear_importerror(tmp_path, monkeypatch):
    """mcp.json present without the [mcp] package → clear ImportError."""
    settings = Settings(home=tmp_path / "home", api_key="test")
    settings.ensure_home()
    (settings.home / "mcp.json").write_text(
        '{"servers": [{"name": "fs", "command": "echo", "args": []}]}'
    )
    # Simulate a missing [mcp] extra: `import mcp` must fail.
    monkeypatch.setitem(sys.modules, "mcp", None)

    conn = connect(settings.home)
    with pytest.raises(ImportError, match=r"uv sync --extra mcp"):
        build_registry(conn, settings)
