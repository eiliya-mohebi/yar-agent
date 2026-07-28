"""DETERMINISTIC EVAL — delegate_task hands coding work to pi, honestly.

Hermetic: pi is NEVER spawned. subprocess.run and shutil.which are monkeypatched.
"""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from evals.helpers import ScriptedClient, gate_skip, make_yar, text_response, tool_response
from yar.config import Settings
from yar.tools import experimental


@pytest.fixture(autouse=True)
def _tmp_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("YAR_WORKSPACE", str(tmp_path / "ws"))


def fake_run(record, stdout="Done. Created hello.py.", returncode=0):
    def run(argv, **kwargs):
        record["argv"] = argv
        record["kwargs"] = kwargs
        return SimpleNamespace(stdout=stdout, stderr="", returncode=returncode)

    return run


def test_delegate_task_invokes_pi_print_mode(tmp_path, monkeypatch):
    record = {}
    monkeypatch.setenv("YAR_EXPERIMENTAL", "1")
    monkeypatch.setattr(experimental.shutil, "which", lambda _: "/fake/bin/pi")
    monkeypatch.setattr(experimental.subprocess, "run", fake_run(record))

    script = [
        gate_skip(),
        tool_response("delegate_task", {"task": "create hello.py"}),
        text_response("pi handled it."),
    ]
    app = make_yar(
        tmp_path / "home",
        client=ScriptedClient(script),
        experimental=True,
        workspace=tmp_path / "ws",
    )
    result = app.respond("have pi create hello.py")

    assert [c["tool"] for c in result.tool_calls] == ["delegate_task"]
    argv = record["argv"]
    assert argv[0] == "/fake/bin/pi"
    assert "-p" in argv and "create hello.py" in argv
    assert "-a" in argv and "--no-session" in argv
    output = result.tool_calls[0]["output"]
    assert "Done. Created hello.py." in output and "saved to" in output.lower()
    manifests = list((tmp_path / "ws").rglob("MANIFEST.md"))
    assert len(manifests) == 1 and "create hello.py" in manifests[0].read_text()
    assert list((tmp_path / "ws").rglob("pi-transcript.log"))


def test_delegate_runs_pi_on_the_calling_model(tmp_path, monkeypatch):
    """Sub-agent codes with the loop's own model + OpenAI key."""
    record = {}
    monkeypatch.setattr(experimental.shutil, "which", lambda _: "/fake/bin/pi")
    monkeypatch.setattr(experimental.subprocess, "run", fake_run(record))
    tool = experimental.make_delegate_tool(
        Settings(
            home=tmp_path,
            model="gpt-4.1-mini",
            api_key="sk-test",
            workspace=tmp_path / "ws",
        )
    )
    tool.fn(task="write fizzbuzz")
    argv = record["argv"]
    assert "--provider" in argv and "openai" in argv
    assert "--model" in argv and "gpt-4.1-mini" in argv
    assert "--api-key" in argv and "sk-test" in argv


def test_delegate_without_pi_returns_install_hint(tmp_path, monkeypatch):
    monkeypatch.setattr(experimental.shutil, "which", lambda _: None)
    tool = experimental.make_delegate_tool(
        Settings(home=tmp_path, workspace=tmp_path / "ws")
    )
    out = tool.fn(task="anything")
    assert experimental.PI_INSTALL_HINT in out
    assert "isn't installed" in out


def test_delegate_timeout_is_honest(tmp_path, monkeypatch):
    monkeypatch.setattr(experimental.shutil, "which", lambda _: "/fake/bin/pi")

    def run(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs.get("timeout", 300))

    monkeypatch.setattr(experimental.subprocess, "run", run)
    tool = experimental.make_delegate_tool(
        Settings(home=tmp_path, workspace=tmp_path / "ws")
    )
    out = tool.fn(task="huge refactor", timeout_seconds=7)
    assert "7s" in out and "YAR_DELEGATE_TIMEOUT" in out


def test_delegate_rejects_missing_cwd_and_empty_task(tmp_path, monkeypatch):
    monkeypatch.setattr(experimental.shutil, "which", lambda _: "/fake/bin/pi")
    tool = experimental.make_delegate_tool(
        Settings(home=tmp_path, workspace=tmp_path / "ws")
    )
    assert "doesn't exist" in tool.fn(task="fix tests", cwd=str(tmp_path / "nope"))
    assert "needs a 'task'" in tool.fn()


def test_delegate_failure_surfaces_stderr(tmp_path, monkeypatch):
    monkeypatch.setattr(experimental.shutil, "which", lambda _: "/fake/bin/pi")

    def run(argv, **kwargs):
        return SimpleNamespace(stdout="", stderr="No API key found", returncode=1)

    monkeypatch.setattr(experimental.subprocess, "run", run)
    tool = experimental.make_delegate_tool(
        Settings(home=tmp_path, workspace=tmp_path / "ws")
    )
    out = tool.fn(task="anything")
    assert "pi hit an error" in out and "No API key found" in out


def test_experimental_flag_gates_registration(tmp_path, monkeypatch):
    monkeypatch.delenv("YAR_EXPERIMENTAL", raising=False)
    app_off = make_yar(tmp_path / "off", client=ScriptedClient([]), experimental=False)
    assert "delegate_task" not in app_off.tools._tools

    app_on = make_yar(tmp_path / "on", client=ScriptedClient([]), experimental=True)
    assert "delegate_task" in app_on.tools._tools
    assert "run_command" in app_on.tools._tools
