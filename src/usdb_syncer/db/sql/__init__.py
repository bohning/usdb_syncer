"""Data directory for SQL scripts."""

from enum import StrEnum, auto


class JobStatus(StrEnum):
    """Status of a job."""

    SKIPPED_UNCHANGED = auto()
    SKIPPED_DISABLED = auto()
    SKIPPED_UNAVAILABLE = auto()
    FAILURE = auto()
    FAILURE_EXISTING = auto()
    FALLBACK = auto()
    SUCCESS = auto()
