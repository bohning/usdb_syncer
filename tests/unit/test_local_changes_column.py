"""Tests for the aggregate local-changes song table column."""

from pathlib import Path

from usdb_syncer.db import JobStatus
from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.gui.song_table.table_model import _tooltip_data
from usdb_syncer.sync_meta import Resource, ResourceFile
from usdb_syncer.usdb_song import UsdbSong


def test_local_changes_column_lists_modified_and_missing_resources(
    song: UsdbSong, tmp_path: Path
) -> None:
    assert song.sync_meta
    song.sync_meta.path = tmp_path.joinpath("song.usdb")
    audio_path = tmp_path.joinpath("song.mp3")
    audio_path.touch()
    song.sync_meta.audio = Resource(
        JobStatus.SUCCESS, ResourceFile("song.mp3", 0, "https://example.com/song.mp3")
    )
    song.sync_meta.txt = Resource(
        JobStatus.SUCCESS, ResourceFile("song.txt", 0, "https://example.com/song.txt")
    )

    display = Column.LOCAL_CHANGES.cell_display_data(song)
    tooltip = _tooltip_data(song, Column.LOCAL_CHANGES.index())

    assert display == "Text, Audio"
    assert tooltip == "Text: song.txt (missing)\nAudio: song.mp3 (modified)"
