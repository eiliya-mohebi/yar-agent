"""Wiring — builds one Yar from its parts. Gateways call `respond()`.

Assembly: config → db → memory → tools → session → loop → tracer.
Gateways pass an optional Observer; the tracer always records.
"""

from __future__ import annotations

import time

from yar.config import Settings, load_settings
from yar.db import connect
from yar.loop.agent import LoopResult, Observer, run_loop
from yar.loop.models import get_client
from yar.memory import Memory
from yar.ops.tracing import Tracer, compose
from yar.runtime.session import Session
from yar.tools import build_registry


class Yar:
    def __init__(self, settings: Settings | None = None, client=None, conn=None):
        # `client` and `conn` are injectable: evals swap in a scripted model,
        # the dashboard injects a cross-thread connection. Same seam either way.
        self.settings = settings or load_settings()
        self.settings.ensure_home()
        self.conn = conn or connect(self.settings.home)
        self.client = client or get_client(self.settings)
        self.memory = Memory(self.conn, self.settings, self.client)
        self.tools = build_registry(self.conn, self.settings, self.memory)
        self.session = Session(self.settings, memory=self.memory)
        self.tracer = Tracer(self.settings)

    def respond(
        self,
        user_message: str,
        observer: Observer | None = None,
        source: str = "cli",
        stream: bool = False,
    ) -> LoopResult:
        """One turn: assemble working memory → run the loop → persist exchange.

        Everything is both shown (observer) and recorded (tracer). `source`
        tags which gateway the message arrived through (cli / dashboard)."""
        captured: dict = {}

        def _capture(kind, ev):
            if kind == "gate":
                captured["gate"] = {
                    "decision": ev.get("decision"),
                    "reason": ev.get("reason"),
                }

        notify = compose(observer, self.tracer.event, _capture)
        t0 = time.perf_counter()

        with self.tracer.turn(user_message):
            system = self.session.build_system(user_message, notify=notify)
            # Working memory is a bounded window: only the last N turns (2 rows
            # each) enter the prompt. Older turns live in state.db.
            window = self.settings.history_turns * 2
            messages = (
                [{"role": "system", "content": system}]
                + self.session.history[-window:]
                + [{"role": "user", "content": user_message}]
            )

            result = run_loop(
                client=self.client,
                model=self.settings.model,
                messages=messages,
                tools=self.tools,
                max_iterations=self.settings.max_iterations,
                max_tokens=self.settings.max_tokens,
                observer=notify,
                stream=stream,
            )

            meta = {
                "gate": captured.get("gate"),
                "iterations": result.iterations,
                "latency_ms": int((time.perf_counter() - t0) * 1000),
                "tools": [c["tool"] for c in result.tool_calls],
                "model": self.settings.model,
            }
            self.session.add_exchange(
                user_message,
                result.reply,
                tool_calls=result.tool_calls,
                source=source,
                meta=meta,
            )
            self.memory.maybe_consolidate(notify=notify)
            self.memory.export_markdown()

        self.tracer.end_turn(result.reply, result.iterations)
        return result
