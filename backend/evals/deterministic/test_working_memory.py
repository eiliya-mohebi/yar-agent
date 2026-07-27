"""DETERMINISTIC EVAL — working-memory assembly is pure string logic.

Regression: the agent must carry a real Gregorian+Jalali clock so it never
asks "what time is it?" / can ground «۵ مرداد». SOUL is seeded once.
"""

from __future__ import annotations

import re

from yar.config import Settings
from yar.runtime.session import DEFAULT_SOUL, Session, load_soul
from yar.text import jalali


def test_system_prompt_includes_bilingual_clock(tmp_path):
    settings = Settings(home=tmp_path / "home")
    settings.ensure_home()
    system = Session(settings, memory=None).build_system("what should I do in 30 minutes?")
    assert "Right now it is" in system
    assert re.search(r"\b\d{2}:\d{2}\b", system), "system prompt is missing a HH:MM time"
    # Jalali date with Persian digits (ARCHITECTURE §7 clock line)
    assert jalali() in system


def test_system_prompt_clock_grounds_persian_turn(tmp_path):
    """Persian requests like «۵ مرداد» need both calendars in the prompt."""
    settings = Settings(home=tmp_path / "home")
    settings.ensure_home()
    system = Session(settings, memory=None).build_system(
        "جلسه با الکس برای ۵ مرداد ساعت ۹ صبح بگذار"
    )
    assert "Right now it is" in system
    assert jalali() in system
    assert re.search(r"\b\d{2}:\d{2}\b", system)


def test_system_prompt_includes_own_model_identity(tmp_path):
    settings = Settings(home=tmp_path / "home", model="gpt-4.1-mini")
    settings.ensure_home()
    system = Session(settings, memory=None).build_system("what model are you?")
    assert "gpt-4.1-mini" in system
    assert "local-first" in system.lower()


def test_default_soul_requires_user_language_and_canonical_tools():
    soul = DEFAULT_SOUL.lower()
    assert "reply in the language" in soul or "language the user" in soul
    assert "create_event" in DEFAULT_SOUL
    assert "ISO" in DEFAULT_SOUL or "canonical" in soul


def test_soul_seeded_once_does_not_overwrite_edits(tmp_path):
    settings = Settings(home=tmp_path / "home")
    settings.ensure_home()
    first = load_soul(settings)
    assert "Yar" in first
    soul_path = settings.home / "SOUL.md"
    soul_path.write_text("Custom persona — do not overwrite.\n")
    assert load_soul(settings) == "Custom persona — do not overwrite.\n"


def test_session_start_new_clears_history_and_retags(tmp_path):
    settings = Settings(home=tmp_path / "home")
    s = Session(settings, memory=None)
    assert s.session_id == "default"
    s.history = [{"role": "user", "content": "hi"}]
    s.start_new("s-test")
    assert s.session_id == "s-test" and s.history == []
