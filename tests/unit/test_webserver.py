"""Regression: /api/songs must serialize UsdbSong via UsdbSongEncoder."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch
from urllib.parse import urlencode

import flask
import pytest

from usdb_syncer import db
from usdb_syncer.webserver import webserver

if TYPE_CHECKING:
    from flask.testing import FlaskClient

    from usdb_syncer.usdb_song import UsdbSong


LOCAL = db.DownloadStatus.local()
NONLOCAL = [s for s in db.DownloadStatus if s not in LOCAL]


@pytest.fixture
def app() -> flask.Flask:
    return flask.Flask(__name__)


def _parse(
    app: flask.Flask, params: list[tuple[str, object]], show_nonlocal: bool
) -> db.SearchBuilder:
    query = urlencode(params, doseq=True)
    with app.test_request_context(f"/api/songs?{query}"):
        return webserver._parse_search(flask.request, show_nonlocal)


def test_parse_search_sets_all_parameters(app: flask.Flask) -> None:
    params = [
        ("search", "Rock"),
        ("sort_by", "year"),
        ("sort_order", "desc"),
        ("artist", "Queen"),
        ("artist", "Earth, Wind & Fire"),  # comma must survive
        ("title", "Bohemian Rhapsody"),
        ("title", "Dancing Queen"),
        ("edition", "Deluxe"),
        ("edition", "Remaster"),
        ("rating", "4.5"),
        ("rating", "3"),
        ("status", db.DownloadStatus.OUTDATED.value),
        ("status", db.DownloadStatus.SYNCHRONIZED.value),
        ("language", "en"),
        ("language", "de"),
        ("views", "1-5"),
        ("views", "10-"),
        ("year", "1975"),
        ("year", "1980"),
        ("genre", "Rock"),
        ("genre", "Pop"),
        ("creator", "alice"),
        ("creator", "bob"),
        ("golden_notes", "true"),
    ]

    builder = _parse(app, params, show_nonlocal=True)

    assert builder.text == "Rock"
    assert builder.order == db.SongOrder.YEAR
    assert builder.descending is True
    assert builder.artists == ["Queen", "Earth, Wind & Fire"]
    assert builder.titles == ["Bohemian Rhapsody", "Dancing Queen"]
    assert builder.editions == ["Deluxe", "Remaster"]
    assert builder.ratings == [4.5, 3.0]
    assert builder.statuses == [
        db.DownloadStatus.OUTDATED,
        db.DownloadStatus.SYNCHRONIZED,
    ]
    assert builder.languages == ["en", "de"]
    assert builder.views == [(1, 5), (10, None)]
    assert builder.years == [1975, 1980]
    assert builder.genres == ["Rock", "Pop"]
    assert builder.creators == ["alice", "bob"]
    assert builder.golden_notes is True


@pytest.mark.parametrize(
    ("sort_by", "expected"),
    [
        ("artist", db.SongOrder.ARTIST),
        ("title", db.SongOrder.TITLE),
        ("year", db.SongOrder.YEAR),
    ],
)
def test_parse_search_sort_by(
    app: flask.Flask, sort_by: str, expected: db.SongOrder
) -> None:
    builder = _parse(app, [("sort_by", sort_by)], show_nonlocal=True)
    assert builder.order == expected


def _status_params(statuses: list[db.DownloadStatus]) -> list[tuple[str, object]]:
    return [("status", s.value) for s in statuses]


def test_parse_search_hides_nonlocal_statuses(app: flask.Flask) -> None:
    requested = LOCAL + NONLOCAL

    builder = _parse(app, _status_params(requested), show_nonlocal=False)

    assert builder.statuses == LOCAL


def test_parse_search_keeps_requested_local_subset(app: flask.Flask) -> None:
    builder = _parse(
        app,
        _status_params([db.DownloadStatus.SYNCHRONIZED, *NONLOCAL]),
        show_nonlocal=False,
    )

    assert builder.statuses == [db.DownloadStatus.SYNCHRONIZED]


def test_parse_search_only_nonlocal_requested_falls_back_to_local(
    app: flask.Flask,
) -> None:
    builder = _parse(app, _status_params(NONLOCAL), show_nonlocal=False)

    assert builder.statuses == LOCAL


def test_parse_search_no_statuses_requested_defaults_to_local(app: flask.Flask) -> None:
    builder = _parse(app, [], show_nonlocal=False)

    assert builder.statuses == LOCAL


def test_parse_search_shows_nonlocal_statuses_when_enabled(app: flask.Flask) -> None:
    requested = NONLOCAL + LOCAL

    builder = _parse(app, _status_params(requested), show_nonlocal=True)

    assert builder.statuses == requested


def test_api_songs_returns_json_for_usdb_song(song: UsdbSong) -> None:
    song.sync_meta = None
    app = webserver._create_app(
        "test", show_nonlocal_songs=True, allow_downloading=False
    )
    app.config["TESTING"] = True

    # Skip the real DB handshake; this test only covers JSON encoding.
    with (
        patch.object(webserver.db, "connect"),
        patch.object(webserver.db, "close"),
        patch.object(webserver, "_get_songs", return_value=[song]),
    ):
        client: FlaskClient = app.test_client()
        response = client.get("/api/songs?search=ABBA&limit=100&offset=0")

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    payload = json.loads(response.get_data(as_text=True))
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["artist"] == song.artist
    assert payload[0]["title"] == song.title
    assert payload[0]["song_id"] == int(song.song_id)
