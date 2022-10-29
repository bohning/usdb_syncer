#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for functions from the note_utils module."""

from typing import Any

from usdb_dl.note_utils import get_params_from_video_tag, is_duet


def test_is_duet() -> None:
    """Tests for the `is_duet` helper function."""

    # # If the title tag contains `DUET`, the function must return True.
    dummy_headers: dict[str, str] = {"#TITLE": "Never gonna give you up [Duet]"}
    assert is_duet(header=dummy_headers, resource_params={})

    # If the resource params dict contains `p1` and `p2` information, the song is a duet as well.
    dummy_resource_params: dict[str, Any] = {"p1": True, "p2": True}
    assert is_duet(header=dummy_headers, resource_params=dummy_resource_params)


def test_get_params_from_video_tag() -> None:

    # Test multiple params
    assert {
        "a": "example",
        "co": "foobar.jpg",
        "bg": "background.jpg",
    } == get_params_from_video_tag(
        header={"#VIDEO": "a=example,co=foobar.jpg,bg=background.jpg"}
    )

    # Test invalid param (empty value)
    assert {"a": "example"} == get_params_from_video_tag(
        header={"#VIDEO": "a=example,co="}
    )

    # Test no params (legacy local video file definition)
    assert not get_params_from_video_tag(header={"#VIDEO": "video.mp4"})
