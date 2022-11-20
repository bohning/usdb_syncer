#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for functions from the note_utils module."""

from usdb_dl import SongId
from usdb_dl.logger import get_logger
from usdb_dl.meta_tags.deserializer import MetaTags
from usdb_dl.note_utils import is_duet

_logger = get_logger(__file__, SongId(1))


def test_is_duet() -> None:
    """Tests for the `is_duet` helper function."""

    # # If the title tag contains `DUET`, the function must return True.
    dummy_headers: dict[str, str] = {"#TITLE": "Never gonna give you up [Duet]"}
    assert is_duet(header=dummy_headers, meta_tags=MetaTags("", _logger))

    # If meta tags contain `p1` and `p2` information, the song is a duet as well.
    assert is_duet(header=dummy_headers, meta_tags=MetaTags("p1=P1,p2=P2", _logger))
