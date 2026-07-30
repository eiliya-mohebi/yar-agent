"""DETERMINISTIC EVAL — bilingual skill match via Unicode tokens + stopwords.

Waku's ASCII [a-z0-9]{3,} prefilter silently zeros Persian. Matching must go
through text.tokens() and bilingual STOPWORDS (ARCHITECTURE §6 / §7).
"""

from __future__ import annotations

from pathlib import Path

from yar.config import Settings
from yar.db import connect
from yar.memory import Memory
from yar.memory.procedural.loader import SkillLoader
from yar.runtime.session import Session


def _write_skill(root: Path, name: str, description: str, body: str = "do the thing") -> Path:
    path = root / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return path


def test_loader_parses_valid_skill_and_skips_invalid(tmp_path):
    _write_skill(tmp_path, "ok", "book a meeting appointment schedule")
    bad = tmp_path / "bad" / "SKILL.md"
    bad.parent.mkdir()
    bad.write_text("no frontmatter here\n", encoding="utf-8")

    loader = SkillLoader([tmp_path])
    assert [s.name for s in loader.skills] == ["ok"]


def test_home_skill_overrides_repo_skill_by_name(tmp_path):
    """Later dirs win — .yar/skills overrides a packaged built-in of the same name."""
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    _write_skill(repo, "schedule-meeting", "repo trigger words meeting", "repo body")
    _write_skill(home, "schedule-meeting", "home trigger words meeting", "home body")

    loader = SkillLoader([repo, home])
    assert len(loader.skills) == 1
    assert loader.skills[0].body == "home body"
    assert "home" in str(loader.skills[0].path)


def test_english_schedule_message_matches_skill(tmp_path):
    _write_skill(
        tmp_path,
        "schedule-meeting",
        "Schedule meetings calls events book plan appointment جلسه قرار برنامه‌ریزی",
    )
    matched = SkillLoader([tmp_path]).match("please schedule a meeting with Alex tomorrow")
    assert [s.name for s in matched] == ["schedule-meeting"]


def test_persian_schedule_message_matches_skill(tmp_path):
    """Persian must fire — the silent failure mode of an ASCII tokenizer."""
    _write_skill(
        tmp_path,
        "schedule-meeting",
        "Schedule meetings calls events book plan appointment جلسه قرار برنامه‌ریزی",
        body="Call create_event with an ISO start.",
    )
    matched = SkillLoader([tmp_path]).match("یک جلسه با علی برنامه‌ریزی کن")
    assert [s.name for s in matched] == ["schedule-meeting"]


def test_stopwords_alone_do_not_match(tmp_path):
    _write_skill(
        tmp_path,
        "schedule-meeting",
        "Schedule meetings with someone at a time جلسه با قرار",
    )
    # Only bilingual stopwords — overlap must stay below threshold.
    assert SkillLoader([tmp_path]).match("با به در از the and of") == []


def test_overlap_requires_two_content_words(tmp_path):
    _write_skill(tmp_path, "schedule-meeting", "schedule meeting appointment book")
    # One shared content word is not enough.
    assert SkillLoader([tmp_path]).match("please schedule lunch") == []
    # Two shared content words fire.
    matched = SkillLoader([tmp_path]).match("please schedule a meeting")
    assert [s.name for s in matched] == ["schedule-meeting"]


def test_top_two_skills_by_overlap(tmp_path):
    _write_skill(tmp_path, "alpha", "alpha bravo charlie delta echo")
    _write_skill(tmp_path, "bravo", "alpha bravo charlie foxtrot")
    _write_skill(tmp_path, "charlie", "alpha bravo golf hotel")
    matched = SkillLoader([tmp_path]).match("alpha bravo charlie delta")
    names = [s.name for s in matched]
    assert len(names) == 2
    assert names[0] == "alpha"  # highest overlap
    assert "charlie" not in names  # third place dropped


def test_matching_skills_returns_markdown_bodies(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_skill(
        skills_dir,
        "schedule-meeting",
        "schedule meeting appointment جلسه برنامه‌ریزی",
        body="Use create_event.",
    )
    settings = Settings(home=tmp_path / "home", api_key="test-key")
    settings.ensure_home()
    # Point the facade at our fixture skills dir via the home install path.
    dest = settings.home / "skills" / "schedule-meeting"
    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text(
        (skills_dir / "schedule-meeting" / "SKILL.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    mem = Memory(connect(settings.home), settings, client=None)
    # Isolate from repo skills: only home skills should be needed for this assert.
    text = mem.matching_skills("یک جلسه برنامه‌ریزی کن")
    assert "### schedule-meeting" in text
    assert "Use create_event." in text


def test_session_injects_persian_skill_body(tmp_path):
    settings = Settings(home=tmp_path / "home", api_key="test-key")
    settings.ensure_home()
    _write_skill(
        settings.home / "skills",
        "schedule-meeting",
        "schedule meeting appointment جلسه برنامه‌ریزی",
        body="Call create_event with ISO times.",
    )
    mem = Memory(connect(settings.home), settings, client=None)
    system = Session(settings, memory=mem).build_system("یک جلسه با سارا برنامه‌ریزی کن")
    assert "Relevant skill instructions:" in system
    assert "Call create_event with ISO times." in system


def test_builtin_schedule_meeting_fires_on_persian():
    """Built-in skill descriptions carry fa triggers — not English-only."""
    from yar.memory import REPO_SKILLS

    matched = SkillLoader([REPO_SKILLS]).match("یک جلسه با علی برنامه‌ریزی کن")
    assert any(s.name == "schedule-meeting" for s in matched)


def test_builtin_weekly_brief_fires_on_persian():
    from yar.memory import REPO_SKILLS

    matched = SkillLoader([REPO_SKILLS]).match("خلاصه هفته‌ام را بده و بگو تمرکز امروز چیست")
    assert any(s.name == "weekly-brief" for s in matched)
