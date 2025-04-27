"""Errors thrown by the USDB Syncer."""


class UsdbSyncerError(Exception):
    """Common base class for our own errors."""


# common


class SongIdError(UsdbSyncerError):
    """Raised when a song id is invalid."""

    def __init__(self, value: int) -> None:
        super().__init__(f"Song id out of range: {value}")
        self.value = value


# database


class DatabaseError(UsdbSyncerError):
    """Base class for database errors."""


class AlreadyConnectedError(DatabaseError):
    """Raised when trying to connect to a database that is already connected."""


class NotConnectedError(DatabaseError):
    """Raised when trying to access a database that is not connected."""


class UnknownSchemaError(DatabaseError):
    """Raised if schema version is not compatible."""


# meta files


class MetaFileTooNewError(UsdbSyncerError):
    """Raised when trying to decode meta info from an incompatible future release."""

    def __str__(self) -> str:
        return "Cannot read sync meta written by a future release!"


# USDB


class UsdbError(UsdbSyncerError):
    """Super class for errors relating to USDB."""


class UsdbParseError(UsdbError):
    """Raised when HTML from USDB has unexpected format."""


class UsdbLoginError(UsdbError):
    """Raised when login was required, but not possible."""


class UsdbNotFoundError(UsdbError):
    """Raised when a requested USDB record is missing."""


class UsdbUnknownLanguageError(UsdbError):
    """Raised when the language of the USDB website cannot be determined."""


# txt parsing


class TxtParseError(UsdbSyncerError):
    """Raised when parsing a txt file fails."""


class HeadersParseError(TxtParseError):
    """Raised when failing to parse headers."""


class HeadersRequiredMissingError(HeadersParseError):
    """Raised when specific headers are required, but missing."""


class TrackParseError(TxtParseError):
    """Raised when failing to parse track."""


class InvalidCharError(TrackParseError):
    """Raised when a track contains invalid characters."""

    def __init__(self, type_: str, value: str) -> None:
        super().__init__(f"Invalid {type_}: {value}")
        self.type_ = type_
        self.value = value


class InvalidNoteError(InvalidCharError):
    """Raised when a note is invalid."""

    def __init__(self, note: str) -> None:
        super().__init__("note", note)
        self.note = note


class InvalidLineBreakError(InvalidCharError):
    """Raised when a line break is invalid."""

    def __init__(self, line_break: str) -> None:
        super().__init__("line break", line_break)
        self.line_break = line_break


class InvalidTrackError(TrackParseError):
    """Raised when a track is invalid."""

    def __init__(self) -> None:
        super().__init__("Invalid track.")


# user input


class AbortError(UsdbSyncerError):
    """Raised when the user requests to abort an operation."""
