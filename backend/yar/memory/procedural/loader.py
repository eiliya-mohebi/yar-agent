"""Procedural memory — SKILL.md files: how to act, loaded only when relevant.

Official Anthropic Agent Skills format: YAML frontmatter with `name` and
`description` (the description doubles as the trigger — no custom `triggers:`
field).

Progressive disclosure:
  1. frontmatter of every skill is always scanned (cheap)
  2. a skill's BODY is loaded into the prompt only when it matches the message
  3. files a skill references are only read if the model asks

Matching uses yar.text.tokens() + bilingual STOPWORDS — never an ASCII
character class (waku's [a-z0-9]{3,} silently zeros Persian).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from yar.text import STOPWORDS, tokens


@dataclass
class Skill:
    name: str
    description: str
    body: str
    path: Path


def _parse_text(text: str, path: Path) -> Skill | None:
    """Validate SKILL.md content (used by the loader AND create_skill later)."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        return None
    front, body = match.groups()
    fields = dict(
        (k.strip(), v.strip().strip("'\""))
        for k, _, v in (line.partition(":") for line in front.splitlines() if ":" in line)
    )
    if "name" not in fields or "description" not in fields:
        return None
    return Skill(fields["name"], fields["description"], body.strip(), path)


def _parse(path: Path) -> Skill | None:
    return _parse_text(path.read_text(encoding="utf-8"), path)


def _content_words(text: str) -> set[str]:
    return {t for t in tokens(text) if t not in STOPWORDS}


class SkillLoader:
    """Scans skill directories: the repo's skills/ (built-in) and .yar/skills
    (installed or agent-authored). Re-scans when any SKILL.md changes."""

    def __init__(self, dirs: list[Path]):
        self.dirs = dirs
        self.skills: list[Skill] = []
        self._sig: tuple = ()
        self.refresh()

    def _scan_sig(self) -> tuple:
        sig = []
        for d in self.dirs:
            if d.is_dir():
                for f in sorted(d.rglob("SKILL.md")):
                    sig.append((str(f), f.stat().st_mtime))
        return tuple(sig)

    def refresh(self) -> None:
        # Later dirs win on name (repo built-ins first, then .yar/skills overrides).
        by_name: dict[str, Skill] = {}
        for d in self.dirs:
            if not d.is_dir():
                continue
            for f in sorted(d.rglob("SKILL.md")):
                skill = _parse(f)
                if skill:
                    by_name[skill.name] = skill
        self.skills = list(by_name.values())
        self._sig = self._scan_sig()

    def match(self, message: str, max_skills: int = 2) -> list[Skill]:
        """Keyword overlap between the message and each skill's name+description.

        Unicode tokens via text.tokens(); bilingual STOPWORDS subtracted so
        short Persian function words don't match every skill. Overlap ≥ 2,
        top max_skills by score.
        """
        if self._scan_sig() != self._sig:
            self.refresh()
        msg_words = _content_words(message)
        scored: list[tuple[int, Skill]] = []
        for skill in self.skills:
            skill_words = _content_words(f"{skill.name} {skill.description}")
            overlap = len(msg_words & skill_words)
            if overlap >= 2:
                scored.append((overlap, skill))
        scored.sort(key=lambda pair: -pair[0])
        return [skill for _, skill in scored[:max_skills]]
