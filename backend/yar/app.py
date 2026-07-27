"""Wiring — builds one Yar from its parts. Gateways call `respond()`.

This issue lands session + SOUL + history fold-in. Retrieval gate,
consolidation, and tracers arrive in later issues; `respond()` here assembles
system prompt + sliding history window → loop → add_exchange.
"""

from __future__ import annotations

from yar.config import Settings, load_settings
from yar.db import connect
from yar.loop.agent import LoopResult, Observer, run_loop
from yar.loop.models import get_client
from yar.memory import Memory
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
        self.tools = build_registry(self.conn, self.settings)
        self.session = Session(self.settings, memory=self.memory)

    def respond(
        self,
        user_message: str,
        observer: Observer | None = None,
        source: str = "cli",
        stream: bool = False,
    ) -> LoopResult:
        """One turn: assemble working memory → run the loop → persist exchange.

        `source` tags which gateway the message arrived through (cli /
        dashboard). Gate / consolidation / tracing wire in later issues."""
        system = self.session.build_system(user_message, notify=observer)
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
            observer=observer,
            stream=stream,
        )

        self.session.add_exchange(
            user_message,
            result.reply,
            tool_calls=result.tool_calls,
            source=source,
        )
        return result
