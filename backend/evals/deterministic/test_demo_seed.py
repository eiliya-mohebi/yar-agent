"""DETERMINISTIC EVAL — demo_seed safety: --yes, backup, keep usage.jsonl."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "demo_seed.py"


def _run_demo_seed(argv: list[str], monkeypatch, home: Path):
    monkeypatch.setenv("YAR_HOME", str(home))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(sys, "argv", ["demo_seed.py", *argv])
    try:
        runpy.run_path(str(SCRIPT), run_name="__main__")
        return 0
    except SystemExit as exc:
        return int(exc.code or 0)


def test_demo_seed_refuses_without_yes(tmp_path, monkeypatch, capsys):
    home = tmp_path / ".yar"
    home.mkdir()
    code = _run_demo_seed([], monkeypatch, home)
    assert code == 2
    err = capsys.readouterr().out
    assert "REFUSING" in err and "--yes" in err
    assert home.exists()


def test_demo_seed_backs_up_and_keeps_usage(tmp_path, monkeypatch, capsys):
    home = tmp_path / ".yar"
    home.mkdir()
    (home / "usage.jsonl").write_text('{"tokens": 42}\n')
    (home / "traces").mkdir()
    (home / "traces" / "old.jsonl").write_text("{}\n")
    (home / "outbox").mkdir()
    (home / "outbox" / "draft.txt").write_text("x")

    code = _run_demo_seed(["--yes"], monkeypatch, home)
    assert code == 0

    backups = list(tmp_path.glob(".yar.bak-*"))
    assert len(backups) == 1
    assert (backups[0] / "usage.jsonl").read_text() == '{"tokens": 42}\n'
    # Spend ledger kept in the live home.
    assert (home / "usage.jsonl").exists()
    assert (home / "usage.jsonl").read_text() == '{"tokens": 42}\n'
    assert not (home / "traces" / "old.jsonl").exists()
    out = capsys.readouterr().out
    assert "backed up" in out and "KEPT" in out


def test_demo_seed_reset_spend_wipes_usage(tmp_path, monkeypatch):
    home = tmp_path / ".yar"
    home.mkdir()
    (home / "usage.jsonl").write_text('{"tokens": 99}\n')

    code = _run_demo_seed(["--yes", "--reset-spend"], monkeypatch, home)
    assert code == 0
    assert not (home / "usage.jsonl").exists()
    backups = list(tmp_path.glob(".yar.bak-*"))
    assert len(backups) == 1
    assert (backups[0] / "usage.jsonl").read_text() == '{"tokens": 99}\n'
