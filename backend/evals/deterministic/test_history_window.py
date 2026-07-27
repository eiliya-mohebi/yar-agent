"""DETERMINISTIC EVAL — working memory is a bounded sliding window.

Older turns live in state.db; only the last history_turns exchanges enter the
prompt, so context/cost/latency stay flat.
"""

from __future__ import annotations

from evals.helpers import ScriptedClient, gate_skip, make_yar, text_response


def test_prompt_history_is_windowed(tmp_path):
    sent = []

    class Recorder(ScriptedClient):
        def _create(self, **kwargs):
            # snapshot now — run_loop mutates messages after this returns
            sent.append(list(kwargs.get("messages", [])))
            return self._script.pop(0)

    # 5 turns; each turn = gate (skip) + one loop call
    script = []
    for _ in range(5):
        script += [gate_skip(), text_response("ok")]
    app = make_yar(
        tmp_path / "home",
        client=Recorder(script),
        history_turns=3,
    )
    for i in range(5):
        app.respond(f"message number {i}")

    last = sent[-1]
    # system + at most 3 turns * 2 rows + the new user message
    non_system = [m for m in last if m.get("role") != "system"]
    assert len(non_system) <= 3 * 2 + 1, f"window not applied: {len(non_system)} msgs"
    text_blob = " ".join(str(m.get("content", "")) for m in non_system)
    # Before respond(4), history holds turns 0..3; window keeps last 3 → 1,2,3
    # plus the new user message 4. Turn 0 must have fallen out.
    assert "message number 4" in text_blob
    assert "message number 1" in text_blob
    assert "message number 0" not in text_blob


def test_default_window_is_generous_but_finite(tmp_path, monkeypatch):
    monkeypatch.delenv("YAR_HISTORY_TURNS", raising=False)
    app = make_yar(tmp_path / "home", client=ScriptedClient([]))
    assert app.settings.history_turns == 12


def test_older_turns_remain_in_state_db_after_window(tmp_path):
    """Full history stays in chat_log even when the prompt is windowed."""
    script = []
    for _ in range(5):
        script += [gate_skip(), text_response("ok")]
    app = make_yar(
        tmp_path / "home",
        client=ScriptedClient(script),
        history_turns=2,
    )
    for i in range(5):
        app.respond(f"turn {i}")

    count = app.conn.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0]
    assert count == 10  # 5 user + 5 assistant
    oldest = app.conn.execute(
        "SELECT content FROM chat_log WHERE role = 'user' ORDER BY id LIMIT 1"
    ).fetchone()
    assert oldest["content"] == "turn 0"
