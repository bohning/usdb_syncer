"""Tests for UsdbSong."""

import json

import attrs

from usdb_syncer.usdb_song import UsdbSong, UsdbSongEncoder


def test_encoding_and_decoding_song_meta(song: UsdbSong) -> None:
    song.sync_meta = None
    song_json = json.dumps(song, cls=UsdbSongEncoder)
    new_song = json.loads(song_json, object_hook=UsdbSong.from_json)
    assert isinstance(new_song, UsdbSong)
    assert attrs.asdict(song) == attrs.asdict(new_song)
