"""Tests for comparing local text changes with USDB."""

from pathlib import Path
from unittest import mock

from tests.conftest import example_notes_str
from usdb_syncer.db import DownloadStatus, JobStatus
from usdb_syncer.gui.usdb_upload_dialog import (
    ValidationFailure,
    ValidationSuccess,
    _validate_song_for_comparison,
    _validate_song_for_submission,
    can_compare_text_with_usdb,
    has_local_text_file,
)
from usdb_syncer.sync_meta import Resource, ResourceFile
from usdb_syncer.usdb_song import UsdbSong


@mock.patch("usdb_syncer.gui.usdb_upload_dialog.get_notes")
def test_validate_song_for_comparison_builds_text_diff(
    get_notes: mock.Mock, song: UsdbSong, tmp_path: Path
) -> None:
    assert song.sync_meta
    remote = example_notes_str()
    local = remote.replace("first note", "changed note")
    txt_path = tmp_path.joinpath("song.txt")
    txt_path.write_text(local, encoding="utf-8")
    song.sync_meta.path = tmp_path.joinpath("song.usdb")
    song.sync_meta.txt = Resource(JobStatus.SUCCESS, ResourceFile.new(txt_path, "USDB"))
    song.status = DownloadStatus.OUTDATED
    get_notes.return_value = remote

    result = _validate_song_for_comparison(song)

    assert isinstance(result, ValidationSuccess)
    assert result.changes.has_changes()
    assert has_local_text_file(song)
    assert can_compare_text_with_usdb(song)
    get_notes.assert_called_once_with(song.song_id, mock.ANY)


@mock.patch("usdb_syncer.gui.usdb_upload_dialog.get_notes")
def test_validate_song_for_comparison_rejects_song_without_local_text_file(
    get_notes: mock.Mock, song: UsdbSong
) -> None:
    result = _validate_song_for_comparison(song)

    assert result == ValidationFailure("local text file is missing")
    assert not has_local_text_file(song)
    assert not can_compare_text_with_usdb(song)
    get_notes.assert_not_called()


def test_compare_action_requires_local_or_remote_change(
    song: UsdbSong, tmp_path: Path
) -> None:
    assert song.sync_meta
    txt_path = tmp_path.joinpath("song.txt")
    txt_path.touch()
    song.sync_meta.path = tmp_path.joinpath("song.usdb")
    song.sync_meta.txt = Resource(JobStatus.SUCCESS, ResourceFile.new(txt_path, "USDB"))
    song.status = DownloadStatus.SYNCHRONIZED

    assert not can_compare_text_with_usdb(song)

    assert song.sync_meta.txt.file
    song.sync_meta.txt.file.mtime = 0
    song.sync_meta.txt.file._is_in_sync = None

    assert can_compare_text_with_usdb(song)


@mock.patch("usdb_syncer.gui.usdb_upload_dialog.get_notes")
@mock.patch.object(UsdbSong, "get_changes")
def test_submission_keeps_upload_normalization_enabled(
    get_changes: mock.Mock, get_notes: mock.Mock, song: UsdbSong, tmp_path: Path
) -> None:
    assert song.sync_meta
    song.sync_meta.path = tmp_path.joinpath("song.usdb")
    song.sync_meta.path.touch()
    song.status = DownloadStatus.SYNCHRONIZED
    get_notes.return_value = example_notes_str()
    changes = mock.Mock()
    changes.has_changes.return_value = True
    get_changes.return_value = changes

    result = _validate_song_for_submission(song)

    assert isinstance(result, ValidationSuccess)
    assert get_changes.call_args.kwargs == {}


@mock.patch("usdb_syncer.gui.usdb_upload_dialog.get_notes")
@mock.patch.object(UsdbSong, "get_changes")
def test_read_only_comparison_disables_upload_normalization(
    get_changes: mock.Mock, get_notes: mock.Mock, song: UsdbSong, tmp_path: Path
) -> None:
    assert song.sync_meta
    txt_path = tmp_path.joinpath("song.txt")
    txt_path.touch()
    song.sync_meta.path = tmp_path.joinpath("song.usdb")
    song.sync_meta.txt = Resource(JobStatus.SUCCESS, ResourceFile.new(txt_path, "USDB"))
    get_notes.return_value = example_notes_str()
    get_changes.return_value = mock.Mock()

    result = _validate_song_for_comparison(song)

    assert isinstance(result, ValidationSuccess)
    assert get_changes.call_args.kwargs == {"normalize_for_upload": False}
