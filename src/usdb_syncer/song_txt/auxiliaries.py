"""Helper classes and functions related to the song text file."""

# Since this file deals with a bunch of ambiguous unicode characters,
# we disable the rule file-wide.
# ruff: noqa: RUF001, RUF003

from __future__ import annotations

from typing import NamedTuple

import attrs

from usdb_syncer.constants import (
    BPM_THRESHOLD,
    LANGUAGES_WITH_SPACED_QUOTES,
    QUOTATION_MARKS,
    QUOTATION_MARKS_TO_REPLACE,
)

NARROW_NO_BREAK_SPACE = "\u202f"


class QuotationMarkReplacementResult(NamedTuple):
    """Named tuple for the result of replace_false_quotation_marks."""

    text: str
    marks_fixed: int
    opening: bool


@attrs.define
class BeatsPerMinute:
    """New type for beats per minute float."""

    value: float = NotImplemented

    def __str__(self) -> str:
        return f"{round(self.value, 2):g}"

    @classmethod
    def parse(cls, value: str) -> BeatsPerMinute:
        return cls(float(value.replace(",", ".")))

    def beats_to_secs(self, beats: int) -> float:
        return beats / (self.value * 4) * 60

    def secs_to_beats(self, secs: float) -> int:
        return int(secs * 4 * self.value / 60)

    def beats_to_ms(self, beats: int) -> float:
        return self.beats_to_secs(beats) * 1000

    def is_too_low(self) -> bool:
        return self.value <= BPM_THRESHOLD

    def make_large_enough(self) -> int:
        """Raise the BPM to a sensible value.

        Double BPM (if necessary, multiple times) until it is above MINIMUM_BPM
        and returns the required multiplication factor.
        """
        factor = 1
        while self.value * factor <= BPM_THRESHOLD:
            factor *= 2
        self.value *= factor
        return factor


def replace_false_apostrophes(value: str) -> str:
    # two single upright quotation marks ('') by double upright quotation marks (")
    # grave (`) and acute accent (´), prime symbol (′), left single quotation mark (‘)
    # and upright apostrophe (') by typographer’s apostrophe (’)
    return (
        value.replace("''", '"')
        .replace("`", "’")
        .replace("´", "’")
        .replace("′", "’")
        .replace("‘", "’")
        .replace("'", "’")
    )


def replace_false_quotation_marks(
    text: str, language: str | None, opening: bool
) -> QuotationMarkReplacementResult:
    # replaces quotation marks with the correct, language-specific ones
    # Note: nested quotation marks as in "Hello “world”" are not supported
    if language:
        opening_quote, closing_quote = QUOTATION_MARKS.get(language, ("“", "”"))
    else:
        opening_quote, closing_quote = ("“", "”")

    spaced_quotes = language in LANGUAGES_WITH_SPACED_QUOTES
    new_text = []
    marks_fixed = 0

    i = 0
    while i < len(text):
        char = text[i]
        if char in QUOTATION_MARKS_TO_REPLACE:
            replacement = opening_quote if opening else closing_quote
            if char != replacement:
                marks_fixed += 1
            if opening:
                new_text.append(opening_quote)
                if spaced_quotes:
                    new_text.append(NARROW_NO_BREAK_SPACE)
                    if i < len(text) - 1 and text[i + 1].isspace():
                        i += 1  # skip space
            else:
                if spaced_quotes:
                    if i > 0 and text[i - 1].isspace():
                        new_text.pop()  # remove trailing space
                    new_text.append(NARROW_NO_BREAK_SPACE)
                new_text.append(closing_quote)
            opening = not opening
        else:
            new_text.append(char)
        i += 1

    fixed_text = "".join(new_text)

    return QuotationMarkReplacementResult(fixed_text, marks_fixed, opening)
