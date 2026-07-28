"""CLI gateway — routing, /memory · /quit, brief, skill install. Issue #10."""

from __future__ import annotations

import io
from datetime import date

import pytest
from rich.console import Console

from evals.helpers import ScriptedClient, gate_skip, make_yar, text_response
from yar.db import connect
from yar.loop.agent import LoopResult

# ---------------------------------------------------------------------------
# Seam: yar.__main__.main(argv) — subcommand router
# ---------------------------------------------------------------------------


def test_main_no_args_runs_cli(monkeypatch):
    called = {}

    def fake_cli():
        called["cli"] = True

    import yar.gateway.cli as cli_mod

    monkeypatch.setattr(cli_mod, "main", fake_cli)
    from yar.__main__ import main

    main([])
    assert called.get("cli") is True


def test_main_dashboard_dispatches(monkeypatch):
    called = {}

    def fake_dash():
        called["dash"] = True

    import yar.ops.dashboard as dash

    monkeypatch.setattr(dash, "main", fake_dash)
    from yar.__main__ import main

    main(["dashboard"])
    assert called.get("dash") is True


def test_main_brief_dispatches(monkeypatch):
    called = {}

    def fake_brief():
        called["brief"] = True

    import yar.ops.brief as brief

    monkeypatch.setattr(brief, "main", fake_brief)
    from yar.__main__ import main

    main(["brief"])
    assert called.get("brief") is True


def test_main_skill_install_dispatches(monkeypatch):
    called = {}

    def fake_install(url: str):
        called["url"] = url

    import yar.memory.procedural.installer as installer

    monkeypatch.setattr(installer, "install", fake_install)
    from yar.__main__ import main

    main(["skill", "install", "https://example.com/SKILL.md"])
    assert called.get("url") == "https://example.com/SKILL.md"


def test_main_unknown_prints_usage_and_exits():
    from yar.__main__ import main

    with pytest.raises(SystemExit) as exc:
        main(["voice"])
    assert exc.value.code == 1


def test_main_rejects_telegram_subcommand():
    """Voice/Telegram gateways are out of scope — must not be routed."""
    from yar.__main__ import main

    with pytest.raises(SystemExit) as exc:
        main(["telegram"])
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# Seam: gateway.cli._memory_snapshot + slash commands
# ---------------------------------------------------------------------------


def test_memory_snapshot_includes_facts_and_persian(tmp_path):
    from yar.gateway.cli import _memory_snapshot

    home = tmp_path / "home"
    home.mkdir()
    conn = connect(home)
    conn.execute(
        "INSERT INTO facts (subject, content) VALUES (?, ?)",
        ("user", "نام من ایلیاست"),
    )
    conn.execute(
        "INSERT INTO episodes (happened_at, summary) VALUES (?, ?)",
        ("2026-07-28", "بحث درباره برنامه"),
    )
    conn.commit()

    text = _memory_snapshot(conn)
    assert "نام من ایلیاست" in text
    assert "بحث درباره برنامه" in text
    assert "Unconsolidated" in text


def test_cli_quit_and_memory_skip_respond(monkeypatch, tmp_path):
    """ /memory and /quit must not call Yar.respond; /quit ends the loop. """
    from yar.gateway import cli as cli_mod

    home = tmp_path / "home"
    home.mkdir()
    app = make_yar(home, client=ScriptedClient([]))
    respond_calls: list[str] = []

    def fake_respond(msg, observer=None, source="cli"):
        respond_calls.append(msg)
        return LoopResult(reply="should-not-run", tool_calls=[], iterations=0)

    app.respond = fake_respond  # type: ignore[method-assign]

    inputs = iter(["/memory", "/quit"])
    monkeypatch.setattr(cli_mod.console, "input", lambda _prompt="": next(inputs))
    monkeypatch.setattr(cli_mod, "Yar", lambda: app)

    # Capture prints so Rich doesn't need a real TTY.
    monkeypatch.setattr(cli_mod.console, "print", lambda *a, **k: None)

    cli_mod.main()
    assert respond_calls == []


def test_cli_message_calls_respond_with_observer(monkeypatch, tmp_path):
    from yar.gateway import cli as cli_mod

    home = tmp_path / "home"
    home.mkdir()
    app = make_yar(
        home, client=ScriptedClient([gate_skip(), text_response("سلام!")])
    )
    seen: dict = {"kinds": []}

    real_respond = app.respond

    def wrap(msg, observer=None, source="cli"):
        seen["observer"] = observer
        seen["source"] = source
        seen["msg"] = msg

        def capturing(kind, event):
            seen["kinds"].append(kind)
            if observer:
                observer(kind, event)

        return real_respond(msg, observer=capturing, source=source)

    app.respond = wrap  # type: ignore[method-assign]

    inputs = iter(["hello", "/quit"])
    monkeypatch.setattr(cli_mod.console, "input", lambda _prompt="": next(inputs))
    monkeypatch.setattr(cli_mod, "Yar", lambda: app)
    monkeypatch.setattr(cli_mod.console, "print", lambda *a, **k: None)

    cli_mod.main()
    assert seen["msg"] == "hello"
    assert seen["source"] == "cli"
    assert callable(seen["observer"])
    assert "gate" in seen["kinds"]


def test_observer_prints_tool_and_gate(monkeypatch):
    import yar.gateway.cli as cli_mod
    from yar.gateway.cli import _observer

    buf = io.StringIO()
    monkeypatch.setattr(
        cli_mod, "console", Console(file=buf, force_terminal=False, width=120)
    )

    _observer("tool", {"tool": "create_event", "args": {"title": "x"}, "output": "ok" * 50})
    _observer("gate", {"decision": "retrieve", "reason": "needs memory"})
    _observer("consolidation", {"new_facts": 2})

    out = buf.getvalue()
    assert "tool · create_event" in out
    assert "gate · retrieve" in out
    assert "consolidated 2" in out


# ---------------------------------------------------------------------------
# Seam: procedural.installer
# ---------------------------------------------------------------------------


def test_raw_url_rewrites_github_blob_and_gist():
    from yar.memory.procedural.installer import _raw_url

    assert (
        _raw_url("https://github.com/u/r/blob/main/skills/foo/SKILL.md")
        == "https://raw.githubusercontent.com/u/r/main/skills/foo/SKILL.md"
    )
    assert (
        _raw_url("https://gist.github.com/u/abc123")
        == "https://gist.github.com/u/abc123/raw"
    )
    assert _raw_url("https://example.com/raw.md") == "https://example.com/raw.md"


def test_install_writes_validated_skill(tmp_path, monkeypatch):
    from yar.memory.procedural import installer

    skill_body = (
        "---\nname: demo-skill\ndescription: demo triggers demo skill\n---\n\nDo the demo.\n"
    )

    class _Resp:
        def read(self):
            return skill_body.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(installer.urllib.request, "urlopen", lambda *a, **k: _Resp())
    monkeypatch.setenv("YAR_HOME", str(tmp_path / "home"))

    installer.install("https://example.com/SKILL.md")

    dest = tmp_path / "home" / "skills" / "demo-skill" / "SKILL.md"
    assert dest.is_file()
    assert "demo-skill" in dest.read_text(encoding="utf-8")


def test_install_rejects_invalid_skill(tmp_path, monkeypatch):
    from yar.memory.procedural import installer

    class _Resp:
        def read(self):
            return b"not a skill"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(installer.urllib.request, "urlopen", lambda *a, **k: _Resp())
    monkeypatch.setenv("YAR_HOME", str(tmp_path / "home"))

    with pytest.raises(SystemExit):
        installer.install("https://example.com/bad.md")


# ---------------------------------------------------------------------------
# Seam: ops.brief.main
# ---------------------------------------------------------------------------


def test_brief_saves_reply_to_outbox(tmp_path, monkeypatch):
    from yar.ops import brief

    home = tmp_path / "home"
    home.mkdir()
    (home / "outbox").mkdir()
    app = make_yar(
        home, client=ScriptedClient([gate_skip(), text_response("Focus on deep work.")])
    )
    monkeypatch.setattr(brief, "Yar", lambda: app)

    brief.main()

    out = home / "outbox" / f"brief-{date.today().isoformat()}.txt"
    assert out.is_file()
    assert "Focus on deep work." in out.read_text(encoding="utf-8")
    assert "Brief me" in brief.PROMPT or "brief" in brief.PROMPT.lower()
