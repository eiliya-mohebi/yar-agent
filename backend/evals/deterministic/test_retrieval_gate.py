"""DETERMINISTIC EVAL — retrieval gate: JSON contract, fail-open, Persian round-trip."""

from __future__ import annotations

from evals.helpers import ScriptedClient, gate_retrieve, gate_skip, make_yar, text_response
from yar.memory.retrieval_gate import should_retrieve
from yar.memory.semantic.store import SqliteFactStore


def test_gate_skip_does_not_inject_memory(tmp_path):
    sent = []

    class Recorder(ScriptedClient):
        def _create(self, **kwargs):
            sent.append(list(kwargs.get("messages", [])))
            return self._script.pop(0)

    home = tmp_path / "home"
    app = make_yar(home, client=ScriptedClient([]))
    SqliteFactStore(app.conn).add("alex", "Alex prefers morning meetings")

    client = Recorder([gate_skip(), text_response("4")])
    app.client = client
    app.memory.client = client
    events = []
    app.respond("what's 2+2?", observer=lambda k, e: events.append((k, e)))

    gate_ev = next(e for k, e in events if k == "gate")
    assert gate_ev["decision"] == "skip"
    # Loop prompt (last create) must not carry the stored fact.
    loop_blob = " ".join(str(m.get("content", "")) for m in sent[-1])
    assert "Alex prefers morning" not in loop_blob


def test_gate_retrieve_injects_matching_facts(tmp_path):
    sent = []

    class Recorder(ScriptedClient):
        def _create(self, **kwargs):
            sent.append(list(kwargs.get("messages", [])))
            return self._script.pop(0)

    home = tmp_path / "home"
    app = make_yar(home, client=ScriptedClient([]))
    SqliteFactStore(app.conn).add("alex", "Alex prefers morning meetings")

    client = Recorder(
        [gate_retrieve("alex", "asks about alex"), text_response("Mornings.")]
    )
    app.client = client
    app.memory.client = client
    events = []
    app.respond("when does Alex like meetings?", observer=lambda k, e: events.append((k, e)))

    gate_ev = next(e for k, e in events if k == "gate")
    assert gate_ev["decision"] == "retrieve"
    loop_blob = " ".join(str(m.get("content", "")) for m in sent[-1])
    assert "Relevant memory:" in loop_blob
    assert "Alex prefers morning" in loop_blob


def test_gate_fails_open_on_bad_json(tmp_path):
    """Parse error → retrieve anyway (a stale memory beats a lost one)."""
    client = ScriptedClient([text_response("not json at all")])
    retrieve, query, reason = should_retrieve(client, "gpt-4.1-mini", "where is Alex?")
    assert retrieve is True
    assert query == "where is Alex?"
    assert "fail" in reason.lower() or "no JSON" in reason


def test_gate_fails_open_on_llm_error():
    class Boom:
        chat = type(
            "C",
            (),
            {
                "completions": type(
                    "X",
                    (),
                    {
                        "create": staticmethod(
                            lambda **kw: (_ for _ in ()).throw(RuntimeError("boom"))
                        )
                    },
                )()
            },
        )()

    retrieve, query, reason = should_retrieve(Boom(), "gpt-4.1-mini", "remember this?")
    assert retrieve is True
    assert query == "remember this?"
    assert "RuntimeError" in reason


def test_persian_fact_round_trip_via_gate(tmp_path):
    """Write Persian fact → gate query in Persian → fact appears in system prompt."""
    sent = []

    class Recorder(ScriptedClient):
        def _create(self, **kwargs):
            sent.append(list(kwargs.get("messages", [])))
            return self._script.pop(0)

    home = tmp_path / "home"
    app = make_yar(home, client=ScriptedClient([]))
    SqliteFactStore(app.conn).add("علی", "علی صبح‌ها را ترجیح می‌دهد")

    client = Recorder(
        [gate_retrieve("علی صبح", "asks about علی"), text_response("صبح‌ها.")]
    )
    app.client = client
    app.memory.client = client
    app.respond("علی کی وقت آزاد دارد؟")

    loop_blob = " ".join(str(m.get("content", "")) for m in sent[-1])
    assert "Relevant memory:" in loop_blob
    assert "علی" in loop_blob
    assert "صبح" in loop_blob
