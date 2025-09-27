"""Errors thrown by the USDB Syncer."""

from pathlib import Path


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


# files


class TrashError(UsdbSyncerError):
    """Raised when a file cannot be trashed."""

    def __init__(self, path: Path) -> None:
        super().__init__(
            f"Cannot trash file: '{path}'. If this issue persists, trashing may not be "
            "supported for your system. Go to the settings to disable trashing and have"
            " files be deleted permanently instead."
        )
        self.path = path


# webserver


class WebserverError(UsdbSyncerError):
    """Base class for webserver errors."""


class InvalidPortError(WebserverError):
    """Raised when the port number is outside the valid range (1-65535)."""

    def __init__(self, port: int) -> None:
        super().__init__(f"Port {port} is invalid (valid range is 1-65535).")
        self.port = port


class PrivilegedPortError(WebserverError):
    """Raised when trying to bind to a privileged port (<1024) without admin rights."""

    def __init__(self, port: int) -> None:
        super().__init__(
            f"Port {port} is privileged on this system. "
            "Please choose a port in the range 1024-65535."
        )
        self.port = port


class PortInUseError(WebserverError):
    """Raised when the chosen port is already in use by another process."""

    def __init__(self, port: int, host: str) -> None:
        super().__init__(
            f"Port {port} on host {host} is already in use. "
            "Please choose a different port."
        )
        self.port = port
        self.host = host
