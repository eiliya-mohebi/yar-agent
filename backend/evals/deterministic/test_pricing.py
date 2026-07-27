"""price_for + usage_summary — OpenAI price map + permanent ledger aggregates."""

from __future__ import annotations

import json

from yar.ops.dashboard import MODEL_PRICING, price_for, usage_summary


def test_price_for_known_openai_model():
    # Lifted from waku's date-stamped OpenAI rates (gpt-5.3-chat-latest).
    assert price_for("openai", "gpt-5.3-chat-latest") == (1.75, 14.0)
    assert "gpt-5.3-chat-latest" in MODEL_PRICING


def test_price_for_falls_back_to_openai_provider_rate():
    assert price_for("openai", "some-unknown-model") == (2.5, 15.0)


def test_usage_summary_aggregates_ledger(tmp_path):
    ledger = tmp_path / "usage.jsonl"
    rows = [
        {"ts": "2026-07-01T10:00:00+00:00", "provider": "openai",
         "model": "gpt-5.3-chat-latest", "in": 1_000_000, "out": 0},
        {"ts": "2026-07-01T11:00:00+00:00", "provider": "openai",
         "model": "gpt-5.3-chat-latest", "in": 0, "out": 1_000_000},
    ]
    ledger.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    summary = usage_summary(tmp_path)
    assert summary["calls"] == 2
    assert summary["total_in"] == 1_000_000
    assert summary["total_out"] == 1_000_000
    # 1M in @ 1.75 + 1M out @ 14.0 = 15.75
    assert summary["total_cost"] == 15.75
    assert summary["by_day"][0]["date"] == "2026-07-01"
