"""Helpers for type checking."""

from typing import NoReturn


def assert_never(value: NoReturn) -> NoReturn:
    """Used to get a static type error if an enum isn't matched exhaustively.

    After we upgrade to Python 3.11, we can use typing.assert_never."""
    assert False, f"Unhandled type: {type(value).__name__}"
