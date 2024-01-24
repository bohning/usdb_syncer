"""Errors thrown by the USDB Syncer."""

class UsdbSyncerError(Exception):
    """Common base class for our own errors."""


### database


class DatabaseError(UsdbSyncerError):
    """Base class for database errors."""


class UnknownSchemaError(DatabaseError):
    """Raised if schema version is not compatible."""


### meta files


class MetaFileTooNewError(UsdbSyncerError):
    """Raised when trying to decode meta info from an incompatible future release."""

    def __str__(self) -> str:
        return "Cannot read sync meta written by a future release!"


### USDB


class UsdbError(UsdbSyncerError):
    """Super class for errors relating to USDB."""


class UsdbParseError(UsdbError):
    """Raised when HTML from USDB has unexpected format."""


class UsdbLoginError(UsdbError):
    """Raised when login was required, but not possible."""


class UsdbNotFoundError(UsdbError):
    """Raised when a requested USDB record is missing."""


### txt parsing


class NotesParseError(UsdbSyncerError):
    """Raised when failing to parse notes."""


### user input


class AbortError(UsdbSyncerError):
    """Raised when the user requests to abort an operation."""
