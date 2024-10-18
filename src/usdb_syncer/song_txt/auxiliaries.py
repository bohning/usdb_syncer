"""Helper classes and functions related to the song text file"""

import math

import attrs

from usdb_syncer.constants import MINIMUM_BPM


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


def replace_false_apostrophes_and_quotation_marks(value: str) -> str:
    # two single upright quotation marks ('') by double upright quotation marks (")
    # grave accent (`), acute accent (´), prime symbol (′) and upright apostrophe (')
    # by typographer’s apostrophe (’)
    return (
        value.replace("''", '"')
        .replace("`", "’")
        .replace("´", "’")
        .replace("′", "’")
        .replace("'", "’")
    )
