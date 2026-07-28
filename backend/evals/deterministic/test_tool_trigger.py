"""DETERMINISTIC EVAL — "did the meeting trigger?" This is a unit test.

No LLM judges anything here. Each case asserts a binary, checkable outcome:
the right tool fired (or didn't), with the right arguments. 0 or 1.

Two tiers:
  offline  — ScriptedClient, always runs, network-free (OUR plumbing)
  live     — real model via AvalAI when OPENAI_API_KEY / YAR_API_KEY is set
             (`evals/dataset.jsonl`, scored through yar.ops.scoring)
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

from evals.helpers import (
    HAS_KEY,
    ScriptedClient,
    gate_skip,
    make_yar,
    text_response,
    tool_response,
)
from yar.ops import scoring

DATASET = scoring.load_cases()

# Search-first multi-hop cases need a working search backend. DuckDuckGo's free
# HTML endpoint is often blocked; without TAVILY_API_KEY the model aborts mid-turn
# and the live assert becomes a flaky network test, not a model+prompt check.
_SEARCH_STRETCH_IDS = frozenset({"pokemon-team", "worldcup-final"})


def _live_cases() -> list[dict]:
    if os.getenv("TAVILY_API_KEY") or os.getenv("YAR_SEARCH_API_KEY"):
        return DATASET
    return [c for c in DATASET if c["id"] not in _SEARCH_STRETCH_IDS]


LIVE_DATASET = _live_cases()


# ---------- offline tier: plumbing without any network ----------


def test_offline_no_tool_turn_ends_in_one_iteration(tmp_path):
    app = make_yar(
        tmp_path / "home",
        client=ScriptedClient([gate_skip(), text_response("Paris.")]),
    )
    result = app.respond("What is the capital of France?")
    assert result.reply == "Paris."
    assert result.iterations == 1
    assert result.tool_calls == []
    ok, why = scoring.check_case({"expect_tool": None}, result.tool_calls)
    assert ok, why


def test_offline_mixed_script_schedules_via_create_event(tmp_path):
    """§7: mixed-script turn must drive the same tool path as English."""
    client = ScriptedClient(
        [
            gate_skip(),
            tool_response(
                "create_event",
                {"title": "جلسه with Alex", "start": "2026-07-29T15:00"},
            ),
            text_response("Booked."),
        ]
    )
    app = make_yar(tmp_path / "home", client=client)
    result = app.respond("book جلسه with Alex فردا at 3pm")
    ok, why = scoring.check_case(
        {
            "expect_tool": "create_event",
            "expect_in_args": {"title": "alex", "start": "T15:00"},
        },
        result.tool_calls,
    )
    assert ok, why
    row = app.conn.execute("SELECT title, start FROM calendar_events").fetchone()
    assert row["start"] == "2026-07-29T15:00"


def test_offline_multi_tool_stretch_scores_when_model_completes_all(tmp_path):
    """Regression: search-stretch cases stay in dataset.jsonl and remain scoreable."""
    case = next(c for c in DATASET if c["id"] == "pokemon-team")
    multi = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[
                        SimpleNamespace(
                            id="c1",
                            type="function",
                            function=SimpleNamespace(
                                name="search_web",
                                arguments=json.dumps({"query": "kanto pikachu"}),
                            ),
                        ),
                        SimpleNamespace(
                            id="c2",
                            type="function",
                            function=SimpleNamespace(
                                name="save_note",
                                arguments=json.dumps(
                                    {
                                        "subject": "starter",
                                        "content": "Pikachu is my starter",
                                    }
                                ),
                            ),
                        ),
                        SimpleNamespace(
                            id="c3",
                            type="function",
                            function=SimpleNamespace(
                                name="create_event",
                                arguments=json.dumps(
                                    {
                                        "title": "Team training 1",
                                        "start": "2026-07-29T18:00",
                                    }
                                ),
                            ),
                        ),
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=0, completion_tokens=0),
    )
    app = make_yar(
        tmp_path / "home",
        client=ScriptedClient([gate_skip(), multi, text_response("Done.")]),
    )
    result = app.respond(case["input"])
    ok, why = scoring.check_case(case, result.tool_calls)
    assert ok, why


def test_offline_dataset_cases_are_scoreable_without_network():
    """Gate CI must not need AvalAI — the offline contract is the scorer + dataset."""
    assert DATASET, "evals/dataset.jsonl must ship with the package"
    for case in DATASET:
        assert isinstance(case["input"], str) and case["input"].strip()
        assert "expect_tool" in case
    # Stretch cases stay in the battery even when live skips them without Tavily.
    assert {c["id"] for c in DATASET} >= _SEARCH_STRETCH_IDS


# ---------- live tier: AvalAI / OpenAI when keyed ----------


@pytest.mark.skipif(not HAS_KEY, reason="live eval needs OPENAI_API_KEY or YAR_API_KEY")
@pytest.mark.parametrize("case", LIVE_DATASET, ids=[c["id"] for c in LIVE_DATASET])
def test_dataset_case(case, tmp_path):
    app = make_yar(tmp_path / "home")
    if "setup_fact" in case:
        app.memory.facts.add(case["setup_fact"]["subject"], case["setup_fact"]["content"])

    result = app.respond(case["input"])
    ok, why = scoring.check_case(case, result.tool_calls)
    assert ok, why
