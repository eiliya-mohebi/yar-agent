"""DETERMINISTIC EVAL — [tools used:…] fold-in and chat_log session labels.

Without the fold-in line the model re-fires create_event (triple-book bug).
Sessions are just labels on chat_log rows; switch reloads working memory.
"""

from __future__ import annotations

from evals.helpers import ScriptedClient, make_yar, text_response, tool_response


def test_history_records_tool_use(tmp_path):
    """Regression companion: next turn's working memory must show tools used."""
    home = tmp_path / "home"
    app = make_yar(
        home,
        client=ScriptedClient(
            [
                tool_response(
                    "create_event", {"title": "X", "start": "2026-07-14T09:00"}
                ),
                text_response("Done."),
            ]
        ),
    )
    app.respond("book X monday 9am")
    assert "[tools used: create_event" in app.session.history[-1]["content"]


def test_foldin_appears_in_next_turn_prompt(tmp_path):
    """Triple-book fix: the next LLM call must see [tools used:…] in history."""
    sent = []

    class Recorder(ScriptedClient):
        def _create(self, **kwargs):
            sent.append(list(kwargs.get("messages", [])))
            return self._script.pop(0)

    app = make_yar(
        tmp_path / "home",
        client=Recorder(
            [
                tool_response(
                    "create_event",
                    {"title": "Swim", "start": "2026-07-11T17:00"},
                ),
                text_response("Booked."),
                text_response("Already booked — see history."),
            ]
        ),
    )
    app.respond("swim saturday 5pm")
    app.respond("did you book that?")

    second_turn = sent[-1]
    blob = " ".join(str(m.get("content", "")) for m in second_turn)
    assert "[tools used: create_event" in blob


def test_add_exchange_persists_to_chat_log_with_session_id(tmp_path):
    home = tmp_path / "home"
    app = make_yar(home, client=ScriptedClient([text_response("hi back")]))
    app.session.start_new("s-persist")
    app.respond("hello")

    rows = app.conn.execute(
        "SELECT role, content, session_id, source FROM chat_log ORDER BY id"
    ).fetchall()
    assert len(rows) == 2
    assert rows[0]["role"] == "user" and rows[0]["content"] == "hello"
    assert rows[0]["session_id"] == "s-persist"
    assert rows[0]["source"] == "cli"
    assert rows[1]["role"] == "assistant"
    assert "hi back" in rows[1]["content"]


def test_switch_reloads_recent_history_from_chat_log(tmp_path):
    home = tmp_path / "home"
    app = make_yar(
        home,
        client=ScriptedClient(
            [text_response("one"), text_response("two"), text_response("fresh")]
        ),
    )
    app.session.start_new("s-a")
    app.respond("msg a1")
    app.respond("msg a2")

    app.session.start_new("s-b")
    app.respond("msg b1")
    assert all("msg a" not in m["content"] for m in app.session.history)

    app.session.switch("s-a")
    assert app.session.session_id == "s-a"
    blob = " ".join(m["content"] for m in app.session.history)
    assert "msg a1" in blob and "msg a2" in blob
    assert "msg b1" not in blob
