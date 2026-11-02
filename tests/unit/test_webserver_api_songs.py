"""Regression: /api/songs must serialize UsdbSong via UsdbSongEncoder."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

from usdb_syncer.usdb_song import UsdbSong
from usdb_syncer.webserver import webserver

if TYPE_CHECKING:
    from flask.testing import FlaskClient


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
