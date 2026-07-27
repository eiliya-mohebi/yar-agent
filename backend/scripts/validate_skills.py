"""Validate every SKILL.md in the repo — run by CI on community PRs.

Checks the official Agent Skills frontmatter (name + description), name
uniqueness, a soft body-length budget, and warns when a skill has no Persian
trigger words (ARCHITECTURE §7). Exit 1 on hard failures; warnings print only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from yar.memory.procedural.loader import _parse  # noqa: E402
from yar.text import tokens  # noqa: E402

MAX_BODY_LINES = 80
# Arabic script block covers Persian letters used in trigger vocabulary.
_PERSIAN_LETTER = re.compile(r"[\u0600-\u06FF]")


def main() -> None:
    problems: list[str] = []
    warnings: list[str] = []
    names: dict[str, Path] = {}

    files = sorted((REPO / "skills").rglob("SKILL.md"))
    if not files:
        problems.append("no SKILL.md files found under skills/")

    for path in files:
        rel = path.relative_to(REPO)
        if "TEMPLATE" in path.parts or path.name == "TEMPLATE.md":
            continue
        # Skip the template copy under community if present.
        if path.parent.name == "community" and path.name == "README.md":
            continue
        skill = _parse(path)
        if skill is None:
            problems.append(
                f"{rel}: missing/invalid frontmatter (need `name` and `description`)"
            )
            continue
        if skill.name in names:
            problems.append(
                f"{rel}: duplicate name '{skill.name}' (also in {names[skill.name]})"
            )
        names[skill.name] = rel
        if len(skill.description.split()) < 5:
            problems.append(
                f"{rel}: description too short to match anything — say when to use it"
            )
        if len(skill.body.splitlines()) > MAX_BODY_LINES:
            problems.append(
                f"{rel}: body over {MAX_BODY_LINES} lines — skills load into the "
                "prompt, keep them tight"
            )
        # Soft: English-only descriptions silently miss فارسی (§7).
        if not _PERSIAN_LETTER.search(skill.description):
            warnings.append(
                f"{rel}: description has no Persian trigger words — "
                "add fa vocabulary so فارسی messages can match"
            )
        elif len(tokens(skill.description)) < 2:
            warnings.append(f"{rel}: description tokenizes to fewer than 2 words")

    for w in warnings:
        print(f"warning: {w}")

    if problems:
        print("skill validation FAILED:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print(f"skill validation OK — {len(names)} skill(s): {', '.join(sorted(names))}")


if __name__ == "__main__":
    main()
