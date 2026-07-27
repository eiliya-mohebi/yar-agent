"""Tracer — always-on JSONL + permanent usage.jsonl; Persian stays unescaped."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from yar.config import Settings
from yar.ops.tracing import TraceEncodingError, Tracer, compose, iter_trace_lines


def _today_trace(home: Path) -> Path:
    return home / "traces" / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"


def test_tracer_writes_persian_unescaped(tmp_path):
    settings = Settings(home=tmp_path, model="gpt-4.1-mini")
    settings.ensure_home()
    msg = "جلسه‌ای با علی"

    with Tracer(settings).turn(msg):
        pass

    raw = _today_trace(tmp_path).read_text(encoding="utf-8")
    assert "علی" in raw
    assert "\\u" not in raw
    record = json.loads(raw.splitlines()[0])
    assert record["type"] == "turn_start"
    assert record["user_message"] == msg


def test_llm_event_appends_usage_ledger(tmp_path):
    settings = Settings(home=tmp_path, model="gpt-4.1-mini")
    settings.ensure_home()
    tracer = Tracer(settings)

    tracer.event("llm", {"iteration": 1, "usage": {"in": 10, "out": 4}})

    ledger = (tmp_path / "usage.jsonl").read_text(encoding="utf-8")
    row = json.loads(ledger.strip())
    assert row["in"] == 10
    assert row["out"] == 4
    assert row["model"] == "gpt-4.1-mini"
    assert row["provider"] == "openai"
    # usage ledger is append-only permanent spend — not wiped by anything here
    assert (tmp_path / "usage.jsonl").exists()


def test_text_deltas_are_not_traced(tmp_path):
    settings = Settings(home=tmp_path)
    settings.ensure_home()
    tracer = Tracer(settings)
    tracer.event("text", {"delta": "سلام"})
    assert not _today_trace(tmp_path).exists()


def test_compose_fans_out_to_all_observers():
    seen: list[tuple[str, dict]] = []
    fan = compose(lambda k, e: seen.append(("a", k)), lambda k, e: seen.append(("b", k)))
    fan("gate", {"decision": "skip"})
    assert seen == [("a", "gate"), ("b", "gate")]


def test_tracer_refuses_legacy_non_utf8_trace(tmp_path):
    settings = Settings(home=tmp_path)
    settings.ensure_home()
    trace = _today_trace(tmp_path)
    original = (
        json.dumps({"type": "turn_start", "user_message": "中文"}, ensure_ascii=False) + "\n"
    ).encode("gbk")
    trace.write_bytes(original)

    with pytest.raises(TraceEncodingError, match="not valid UTF-8"):
        with Tracer(settings).turn("next"):
            pass

    assert trace.read_bytes() == original


def test_iter_trace_lines_reads_utf8(tmp_path):
    path = tmp_path / "t.jsonl"
    path.write_text(
        json.dumps({"type": "gate", "decision": "retrieve"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    lines = list(iter_trace_lines(path))
    assert json.loads(lines[0])["decision"] == "retrieve"
