"""Persian/English normalization and the only tokenizer in the package.

See docs/ARCHITECTURE.md §7. Every human-text path (skill match, FTS query,
date args) must go through normalize()/tokens() — never an ASCII character class.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

# Bilingual stopwords for skill matching. Persian's most common words are 2–3
# letters; without this, overlap ≥ 2 matches every skill on every message.
STOPWORDS: frozenset[str] = frozenset(
    {
        # English
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "for",
        "on",
        "is",
        "are",
        "was",
        "were",
        "be",
        "with",
        "at",
        "by",
        "from",
        "as",
        "it",
        "this",
        "that",
        "my",
        "your",
        "me",
        "you",
        # Persian
        "با",
        "به",
        "در",
        "از",
        "که",
        "این",
        "را",
        "و",
        "یا",
        "هم",
        "تا",
        "برای",
        "یک",
        "می",
        "او",
        "ما",
        "تو",
        "آن",
        "ها",
        "های",
    }
)

_ARABIC_TO_PERSIAN = str.maketrans(
    {
        "ي": "ی",  # Arabic yeh → Persian yeh
        "ى": "ی",  # Alef maksura → Persian yeh
        "ك": "ک",  # Arabic kaf → Persian kaf
    }
)

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
_ARABIC_INDIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_TO_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

# Presentation-form ligatures → their decomposed letter sequences.
_PRESENTATION_FORMS = {
    "\ufefb": "لا",  # ﻻ
    "\ufefc": "لا",  # ﻼ
    "\ufef7": "لأ",  # ﻷ
    "\ufef8": "لأ",  # ﻸ
    "\ufef9": "لإ",  # ﻹ
    "\ufefa": "لإ",  # ﻺ
    "\ufef5": "لآ",  # ﻵ
    "\ufef6": "لآ",  # ﻶ
}

_BIDI_CONTROLS = dict.fromkeys(
    (
        0x200E,  # LRM
        0x200F,  # RLM
        0x202A,  # LRE
        0x202B,  # RLE
        0x202C,  # PDF
        0x202D,  # LRO
        0x202E,  # RLO
    ),
    None,
)


def normalize(text: str) -> str:
    """Canonical form for searchable / matchable human text (not for display storage)."""
    if not text:
        return ""
    # Order matches ARCHITECTURE §7: NFC → letters → digits → presentation/bidi.
    out = unicodedata.normalize("NFC", text)
    out = out.translate(_ARABIC_TO_PERSIAN)
    out = out.translate(_PERSIAN_DIGITS)
    out = out.translate(_ARABIC_INDIC_DIGITS)
    for src, dst in _PRESENTATION_FORMS.items():
        out = out.replace(src, dst)
    out = out.translate(_BIDI_CONTROLS)
    # ZWNJ (U+200C) is intentionally kept — FTS5 unicode61 splits on it.
    return out


def tokens(text: str, min_len: int = 2) -> list[str]:
    """Unicode word tokens from normalized text. Never use ASCII classes on user text."""
    return re.findall(rf"\w{{{min_len},}}", normalize(text).lower())


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """Convert a Gregorian date to Jalali (year, month, day). Integer arithmetic only."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        (365 * gy)
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + g_d_m[gm - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def jalali(when: datetime | date | None = None) -> str:
    """Jalali calendar date with Persian digits, e.g. ۱۴۰۵-۰۵-۰۴."""
    d = when.date() if isinstance(when, datetime) else (when or date.today())
    jy, jm, jd = gregorian_to_jalali(d.year, d.month, d.day)
    ascii_s = f"{jy:04d}-{jm:02d}-{jd:02d}"
    return ascii_s.translate(_TO_PERSIAN_DIGITS)
