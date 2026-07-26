"""Configuration — every knob is an env var, documented in .env.example.

No settings framework: a dataclass read once at startup. App code reads
Settings via load_settings(); it must not scatter os.getenv for knobs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # reads .env in the current directory, if present

# AvalAI OpenAI-compatible endpoint — this deployment's default wire target.
DEFAULT_BASE_URL = "https://api.avalai.ir/v1"


def _api_key() -> str:
    return os.getenv("OPENAI_API_KEY") or os.getenv("YAR_API_KEY") or ""


@dataclass
class Settings:
    # --- LLM (OpenAI chat.completions wire format only; AvalAI via base_url)
    api_key: str = field(default_factory=_api_key)
    base_url: str = field(
        default_factory=lambda: os.getenv("YAR_BASE_URL") or DEFAULT_BASE_URL
    )
    model: str = field(
        default_factory=lambda: os.getenv("YAR_MODEL", "gpt-5.3-chat-latest")
    )
    # Cheap model used by the retrieval gate and the consolidation summarizer.
    small_model: str = field(
        default_factory=lambda: os.getenv("YAR_SMALL_MODEL", "gpt-4.1-mini")
    )

    # --- Home: memory DB, calendar, outbox, traces (local-first, always inspectable)
    home: Path = field(default_factory=lambda: Path(os.getenv("YAR_HOME", ".yar")))

    # --- Loop guardrails
    max_iterations: int = field(
        default_factory=lambda: int(os.getenv("YAR_MAX_ITERATIONS", "10"))
    )
    max_tokens: int = field(default_factory=lambda: int(os.getenv("YAR_MAX_TOKENS", "8192")))
    history_turns: int = field(
        default_factory=lambda: int(os.getenv("YAR_HISTORY_TURNS", "12"))
    )

    # --- Memory
    consolidate_every: int = field(
        default_factory=lambda: int(os.getenv("YAR_CONSOLIDATE_EVERY", "6"))
    )
    retrieval_top_k: int = field(
        default_factory=lambda: int(os.getenv("YAR_RETRIEVAL_TOP_K", "4"))
    )

    # --- Tools
    experimental: bool = field(
        default_factory=lambda: os.getenv("YAR_EXPERIMENTAL", "") in ("1", "true", "yes")
    )

    # --- Tracing (JSONL always; OTel exports if an endpoint is set)
    otel_endpoint: str = field(
        default_factory=lambda: os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    )

    def ensure_home(self) -> Path:
        self.home.mkdir(parents=True, exist_ok=True)
        (self.home / "traces").mkdir(exist_ok=True)
        (self.home / "outbox").mkdir(exist_ok=True)
        return self.home

    def require_api_key(self) -> None:
        """Fail clearly at startup — never fall back to a mock client."""
        if not self.api_key.strip():
            raise SystemExit(
                "Missing OPENAI_API_KEY (or YAR_API_KEY). "
                "Set it in backend/.env — see .env.example. "
                "For AvalAI, also keep YAR_BASE_URL=https://api.avalai.ir/v1."
            )


def load_settings() -> Settings:
    return Settings()
