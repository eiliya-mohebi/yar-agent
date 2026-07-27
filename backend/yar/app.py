"""Wiring — builds one Yar from its parts. Gateways call `respond()`.

This issue lands a thin assembly: config → db → calendar tools → loop.
Session, retrieval gate, consolidation, and tracers arrive in later issues;
`respond()` here is enough for isolated offline calendar evals.
"""

from __future__ import annotations

from yar.config import Settings, load_settings
from yar.db import connect
from yar.loop.agent import LoopResult, Observer, run_loop
from yar.loop.models import get_client
from yar.tools import build_registry


class Yar:
    def __init__(self, settings: Settings | None = None, client=None, conn=None):
        # `client` and `conn` are injectable: evals swap in a scripted model,
        # the dashboard injects a cross-thread connection. Same seam either way.
        self.settings = settings or load_settings()
        self.settings.ensure_home()
        self.conn = conn or connect(self.settings.home)
        self.client = client or get_client(self.settings)
        self.tools = build_registry(self.conn, self.settings)

    def respond(
        self,
        user_message: str,
        observer: Observer | None = None,
        stream: bool = False,
    ) -> LoopResult:
        """One turn: run the loop with calendar tools. Persistence / system
        prompt / memory arrive with later issues — offline evals only need the
        tool side effects (calendar_events + calendar.ics)."""
        messages = [{"role": "user", "content": user_message}]
        return run_loop(
            client=self.client,
            model=self.settings.model,
            messages=messages,
            tools=self.tools,
            max_iterations=self.settings.max_iterations,
            max_tokens=self.settings.max_tokens,
            observer=observer,
            stream=stream,
        )
