"""Offline unit tests for the release gate helpers (no network, no full suite)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from yar.ops import release_gate


def test_report_writes_eval_report_and_appends_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("YAR_HOME", str(tmp_path / "home"))
    release_gate.report(
        "pass",
        "skipped",
        suites={"deterministic": {"passed": 3, "failed": 0}},
    )

    home = Path(tmp_path / "home")
    report = json.loads((home / "eval_report.json").read_text(encoding="utf-8"))
    assert report["deterministic"] == "pass"
    assert report["judge"] == "skipped"
    assert report["suites"]["deterministic"]["passed"] == 3
    assert "ran_at" in report

    runs = (home / "eval_runs.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(runs) == 1
    assert json.loads(runs[0])["deterministic"] == "pass"


def test_run_parses_pytest_summary_counts(tmp_path, monkeypatch):
    """run() scrapes the -q summary; stub subprocess keeps this network-free."""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(
            returncode=1,
            stdout="... 2 passed, 1 failed in 0.01s\n",
            stderr="",
        )

    monkeypatch.setattr(release_gate.subprocess, "run", fake_run)
    code, counts = release_gate.run("deterministic")
    assert code == 1
    assert counts == {"passed": 2, "failed": 1}
    assert any("deterministic" in str(part) for part in calls[0])
