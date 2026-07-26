"""Unit cases for the §7 text contract — normalize, tokens, Jalali."""

from __future__ import annotations

from datetime import date

import pytest

from yar.text import STOPWORDS, jalali, normalize, tokens


def test_persian_does_not_tokenize_to_empty():
    assert tokens("سلام دنیا") == ["سلام", "دنیا"]
    assert tokens("جلسه فردا") != []


def test_arabic_yeh_and_kaf_fold_to_persian():
    # علي (Arabic yeh) and علی (Persian yeh) must become the same searchable form.
    assert normalize("علي") == normalize("علی")
    assert "ی" in normalize("علي")
    assert normalize("كتاب") == normalize("کتاب")


def test_persian_and_arabic_indic_digits_fold_to_ascii():
    assert normalize("ساعت ۹") == normalize("ساعت 9")
    assert "9" in normalize("ساعت ۹")
    assert "9" in normalize("ساعت ٩")  # Arabic-Indic


def test_zwnj_is_preserved():
    raw = "جلسه‌های"  # جلسه + ZWNJ + های
    assert "\u200c" in raw
    assert "\u200c" in normalize(raw)


def test_bidi_controls_stripped_presentation_forms_collapsed():
    assert "\u200e" not in normalize("hello\u200eworld")
    assert normalize("\ufefb") == "لا"  # ﻻ ligature


def test_mixed_script_tokens():
    toks = tokens("book جلسه at 3pm")
    assert "book" in toks
    assert "جلسه" in toks


def test_jalali_matches_architecture_example():
    # ARCHITECTURE §7: 2026-07-26 → ۱۴۰۵-۰۵-۰۴
    assert jalali(date(2026, 7, 26)) == "۱۴۰۵-۰۵-۰۴"


def test_stopwords_include_short_persian_and_english():
    assert "با" in STOPWORDS
    assert "the" in STOPWORDS


@pytest.mark.parametrize(
    "text",
    [
        "علی",
        "schedule meeting",
        "۹ مرداد",
    ],
)
def test_tokens_never_use_empty_for_real_user_text(text: str):
    assert tokens(text)
