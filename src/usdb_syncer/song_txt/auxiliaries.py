"""Helper classes and functions related to the song text file"""

import math
import re

import attrs

from usdb_syncer.constants import (
    MINIMUM_BPM,
    QUOTATION_MARKS,
    QUOTATION_MARKS_TO_REPLACE,
)


@attrs.define
class BeatsPerMinute:
    """New type for beats per minute float."""

    value: float = NotImplemented

    def __str__(self) -> str:
        return f"{round(self.value, 2):g}"

    @classmethod
    def parse(cls, value: str) -> "BeatsPerMinute":
        return cls(float(value.replace(",", ".")))

    def beats_to_secs(self, beats: int) -> float:
        return beats / (self.value * 4) * 60

    def secs_to_beats(self, secs: float) -> int:
        return int(secs * 4 * self.value / 60)

    def beats_to_ms(self, beats: int) -> float:
        return self.beats_to_secs(beats) * 1000

    def is_too_low(self) -> bool:
        return self.value < MINIMUM_BPM

    def make_large_enough(self) -> int:
        """Double BPM (if necessary, multiple times) until it is above MINIMUM_BPM
        and returns the required multiplication factor."""
        # how often to double bpm until it is larger or equal to the threshold
        exp = math.ceil(math.log2(MINIMUM_BPM / self.value))
        factor = 2**exp
        self.value = self.value * factor
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
    value: str, language: str | None, marks_total: int
) -> tuple[str, int, int]:
    # replaces quotation marks with the language-specific counterparts
    if language:
        quotation_marks = QUOTATION_MARKS.get(language, ("“", "”"))
    else:
        quotation_marks = ("“", "”")

    quotation_mark_indices: list[int] = []
    for mark in QUOTATION_MARKS_TO_REPLACE:
        quotation_mark_indices.extend(
            match.start() for match in re.finditer(mark, value)
        )
    quotation_mark_indices.sort()

    marks_fixed = 0
    for str_index in quotation_mark_indices:
        marks_index = marks_total % 2
        if value[str_index] != quotation_marks[marks_index]:
            value = (
                value[:str_index]
                + quotation_marks[marks_index]
                + value[str_index + 1 :]
            )
            marks_fixed = marks_fixed + 1

        marks_total = marks_total + 1

    return value, marks_total, marks_fixed
