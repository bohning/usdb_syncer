"""Filters to filter songs by."""

from enum import Enum


class RatingFilter(Enum):
    """Selectable filters for song ratings."""

    ANY = (0, False)
    EXACT_1 = (1, True)
    EXACT_2 = (2, True)
    EXACT_3 = (3, True)
    EXACT_4 = (4, True)
    EXACT_5 = (5, True)
    MIN_2 = (2, False)
    MIN_3 = (3, False)
    MIN_4 = (4, False)

    def __str__(self) -> str:
        if self == RatingFilter.ANY:
            return "Any"
        if self.value[1]:
            return self.value[0] * "★"
        return self.value[0] * "★" + " or more"


class GoldenNotesFilter(Enum):
    """Selectable filters for songs with or without golden notes."""

    ANY = None
    YES = True
    NO = False

    def __str__(self) -> str:
        if self == GoldenNotesFilter.ANY:
            return "Any"
        if self == GoldenNotesFilter.YES:
            return "Yes"
        return "No"


class ViewsFilter(Enum):
    """Selectable filters for songs with a specific view count."""

    ANY = 0
    MIN_100 = 100
    MIN_200 = 200
    MIN_300 = 300
    MIN_400 = 400
    MIN_500 = 500

    def __str__(self) -> str:
        if self == ViewsFilter.ANY:
            return "Any"
        return f"{self.value}+"
