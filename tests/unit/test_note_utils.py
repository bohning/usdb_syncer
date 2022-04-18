#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any

from usdb_dl.note_utils import is_duet


def test_is_duet() -> None:
    """Tests for the `is_duet` helper function."""

    # # If the title tag contains `DUET`, the function must return True.
    dummy_headers: dict[str, str] = {"#TITLE": "Never gonna give you up [Duet]"}
    assert True == is_duet(header=dummy_headers, resource_params={})

    # If the resource params dict contains `p1` and `p2` information, the song is a duet as well.
    dummy_resource_params: dict[str, Any] = {"p1": True, "p2": True}
    assert True == is_duet(header={}, resource_params=dummy_resource_params)
