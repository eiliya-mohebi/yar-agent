"""Settings / load_settings — single config path, AvalAI base URL, clear key failure."""

from __future__ import annotations

from pathlib import Path

import pytest

from yar.config import Settings, load_settings


def test_defaults_match_architecture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("YAR_API_KEY", raising=False)
    monkeypatch.delenv("YAR_BASE_URL", raising=False)
    monkeypatch.delenv("YAR_MODEL", raising=False)
    monkeypatch.delenv("YAR_SMALL_MODEL", raising=False)
    monkeypatch.delenv("YAR_HOME", raising=False)
    monkeypatch.delenv("YAR_MAX_ITERATIONS", raising=False)
    monkeypatch.delenv("YAR_MAX_TOKENS", raising=False)
    monkeypatch.delenv("YAR_HISTORY_TURNS", raising=False)
    monkeypatch.delenv("YAR_CONSOLIDATE_EVERY", raising=False)
    monkeypatch.delenv("YAR_RETRIEVAL_TOP_K", raising=False)
    monkeypatch.delenv("YAR_EXPERIMENTAL", raising=False)
    monkeypatch.delenv("YAR_WORKSPACE", raising=False)
    monkeypatch.delenv("YAR_DELEGATE_AUTORUN", raising=False)
    monkeypatch.delenv("YAR_AUTORUN_TIMEOUT", raising=False)

    s = load_settings()
    assert s.base_url == "https://api.avalai.ir/v1"
    assert s.model == "gpt-5.3-chat-latest"
    assert s.small_model == "gpt-4.1-mini"
    assert s.max_iterations == 10
    assert s.max_tokens == 8192
    assert s.history_turns == 12
    assert s.consolidate_every == 6
    assert s.retrieval_top_k == 4
    assert s.home == Path(".yar")
    assert s.experimental is False
    assert s.workspace == Path("yar_workspace")
    assert s.delegate_autorun is True
    assert s.autorun_timeout == 30
    assert s.api_key == ""


def test_api_key_from_openai_or_yar(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("YAR_API_KEY", "yar-secret")
    assert load_settings().api_key == "yar-secret"

    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    # OPENAI_API_KEY wins when both set (documented primary).
    assert load_settings().api_key == "openai-secret"


def test_require_api_key_fails_clearly(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("YAR_API_KEY", raising=False)
    s = load_settings()
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        s.require_api_key()


def test_ensure_home_creates_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("YAR_HOME", str(tmp_path / "home"))
    s = load_settings()
    root = s.ensure_home()
    assert root.is_dir()
    assert (root / "traces").is_dir()
    assert (root / "outbox").is_dir()


def test_no_provider_field():
    assert not hasattr(Settings, "provider")
    assert "provider" not in Settings.__dataclass_fields__
