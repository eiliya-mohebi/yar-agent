"""DETERMINISTIC EVAL — delegated-coding workspace (yar.tools.workspace)."""

from __future__ import annotations

from datetime import datetime

from yar.tools import workspace as ws


def test_run_folder_is_dated_and_named(tmp_path):
    when = datetime(2026, 7, 19, 12, 48, 31)
    folder = ws.new_run_folder(
        "gpt-4.1-mini", "build me a snake game", now=when, root=tmp_path
    )
    assert folder.parent.name == "2026-07-19"
    assert folder.name == "124831-gpt-4-build-me-a-snake"
    assert folder.is_dir()


def test_run_folder_slugs_persian_task(tmp_path):
    when = datetime(2026, 7, 19, 12, 0, 0)
    folder = ws.new_run_folder("m", "ساخت بازی مار", now=when, root=tmp_path)
    assert "ساخت" in folder.name or "بازی" in folder.name
    assert folder.is_dir()


def test_autorun_runs_the_entry_and_captures_output(tmp_path):
    folder = ws.new_run_folder(
        "m", "print hello", now=datetime(2026, 7, 19, 1, 2, 3), root=tmp_path
    )
    (folder / "main.py").write_text("print('hello from the script')\n")
    entry, code, out, secs = ws.autorun(folder)
    assert entry == "main.py" and code == 0
    assert "hello from the script" in out
    assert (folder / "run.log").exists()


def test_autorun_picks_main_over_a_helper(tmp_path):
    folder = ws.new_run_folder(
        "m", "t", now=datetime(2026, 7, 19, 1, 2, 4), root=tmp_path
    )
    (folder / "helper.py").write_text("X = 1\n")
    (folder / "main.py").write_text("print('main ran')\n")
    entry, code, out, _ = ws.autorun(folder)
    assert entry == "main.py" and "main ran" in out


def test_autorun_disabled_by_flag(tmp_path):
    folder = ws.new_run_folder(
        "m", "t", now=datetime(2026, 7, 19, 1, 2, 5), root=tmp_path
    )
    (folder / "main.py").write_text("print('hi')\n")
    assert ws.autorun(folder, enabled=False) is None


def test_autorun_none_when_nothing_runnable(tmp_path):
    folder = ws.new_run_folder(
        "m", "t", now=datetime(2026, 7, 19, 1, 2, 6), root=tmp_path
    )
    (folder / "notes.txt").write_text("no python here\n")
    assert ws.autorun(folder) is None


def test_manifest_documents_the_run(tmp_path):
    folder = ws.new_run_folder(
        "gpt-4.1", "make a game", now=datetime(2026, 7, 19, 1, 2, 7), root=tmp_path
    )
    (folder / "game.py").write_text("print('ok')\n")
    files = ws.created_files(folder)
    run = ws.autorun(folder)
    ws.write_manifest(folder, "openai", "gpt-4.1", "make a game", files, run)
    text = (folder / "MANIFEST.md").read_text()
    assert "openai:gpt-4.1" in text and "make a game" in text
    assert "game.py" in text and "Auto-run" in text
