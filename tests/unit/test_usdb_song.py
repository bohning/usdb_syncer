"""Tests for UsdbSong."""

import json
from pathlib import Path

import attrs

from usdb_syncer.db import JobStatus
from usdb_syncer.logger import song_logger
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.sync_meta import Resource, ResourceFile
from usdb_syncer.usdb_song import UsdbSong, UsdbSongEncoder


def test_encoding_and_decoding_song_meta(song: UsdbSong) -> None:
    song.sync_meta = None
    song_json = json.dumps(song, cls=UsdbSongEncoder)
    new_song = json.loads(song_json, object_hook=UsdbSong.from_json)
    assert isinstance(new_song, UsdbSong)
    assert attrs.asdict(song) == attrs.asdict(new_song)


def test_get_changes_can_skip_upload_normalization(
    song: UsdbSong, tmp_path: Path
) -> None:
    assert song.sync_meta
    text = (
        "#TITLE:Velvet Comet\n"
        "#ARTIST:The Paper Satellites\n"
        "#BPM:268.16\n"
        "#GAP:10601\n"
        "F 0 6 5 Right \n"
        "F 32 17 0 now \n"
        "- 51\n"
        ": 160 8 0 I \n"
        ": 172 4 0 am \n"
        "E"
    )
    txt_path = tmp_path.joinpath("song.txt")
    txt_path.write_text(text, encoding="utf-8")
    song.sync_meta.path = tmp_path.joinpath("song.usdb")
    song.sync_meta.txt = Resource(JobStatus.SUCCESS, ResourceFile.new(txt_path, "USDB"))
    logger = song_logger(song.song_id)
    remote = SongTxt.parse(text, logger)

    comparison = song.get_changes(remote, normalize_for_upload=False)
    submission = song.get_changes(remote)

    assert comparison and not comparison.has_changes()
    assert submission and submission.has_changes()
