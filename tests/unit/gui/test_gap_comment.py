"""Tests for posting comments containing local #GAP values."""

from decimal import Decimal
from pathlib import Path

import attrs
import pytest

from usdb_syncer import SongId, utils
from usdb_syncer.db import JobStatus
from usdb_syncer.gui import mw
from usdb_syncer.sync_meta import Resource, ResourceFile
from usdb_syncer.usdb_song import UsdbSong


@pytest.mark.parametrize(
    ("contents", "expected"),
    [
        ("#TITLE:Title\n#GAP: 84\n", "84"),
        ("#TITLE:Title\n#GAP: 51.4\n", "51.4"),
        ("#TITLE:Title\n#GAP: 51,4\n", "51,4"),
        ("#TITLE:Title\n#GAP: invalid\n", None),
        ("#TITLE:Title\n: 0 1 0 lyric\n#GAP: 84\n", None),
    ],
)
def test_read_local_gap(tmp_path: Path, contents: str, expected: str | None) -> None:
    path = tmp_path / "song.txt"
    path.write_text(contents, encoding="utf-8")

    assert mw._read_local_gap(path) == expected


def test_read_local_gap_supports_cp1252(tmp_path: Path) -> None:
    path = tmp_path / "song.txt"
    path.write_bytes("#ARTIST:Café\n#GAP: 84\n".encode("cp1252"))

    assert mw._read_local_gap(path) == "84"


def test_post_gap_comments_only_posts_changed_text_files(
    song: UsdbSong, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    changed = _song_with_txt(song, tmp_path, 101, "#GAP: 84\n", changed=True)
    unchanged = _song_with_txt(song, tmp_path, 102, "#GAP: 12\n", changed=False)
    missing_gap = _song_with_txt(
        song, tmp_path, 103, "#TITLE:No GAP\n", changed=True
    )
    missing_file = _song_with_txt(song, tmp_path, 104, None, changed=True)
    posted: list[tuple[SongId, str, str]] = []

    def post_comment(song_id: SongId, text: str, rating: str) -> None:
        posted.append((song_id, text, rating))

    monkeypatch.setattr(mw, "post_song_comment", post_comment)
    posted_gap_comments: set[tuple[SongId, Decimal]] = set()

    result = mw._post_gap_comments(
        [changed, unchanged, missing_gap, missing_file],
        utils.ProgressProxy("test"),
        posted_gap_comments,
    )

    assert result == (1, 3, 0, False)
    assert posted == [(SongId(101), "#GAP: 84", "neutral")]


def test_post_gap_comments_retries_failed_post(
    song: UsdbSong, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _song_with_txt(song, tmp_path, 201, "#GAP: 20\n", changed=True)
    second = _song_with_txt(song, tmp_path, 202, "#GAP: 30\n", changed=True)
    calls: list[tuple[SongId, str, str]] = []
    failed_once = False

    def post_comment(song_id: SongId, text: str, rating: str) -> None:
        nonlocal failed_once
        calls.append((song_id, text, rating))
        if song_id == SongId(201) and not failed_once:
            failed_once = True
            raise RuntimeError("USDB unavailable")

    monkeypatch.setattr(mw, "post_song_comment", post_comment)
    posted_gap_comments: set[tuple[SongId, Decimal]] = set()

    result = mw._post_gap_comments(
        [first, second], utils.ProgressProxy("test"), posted_gap_comments
    )
    retry_result = mw._post_gap_comments(
        [first], utils.ProgressProxy("test"), posted_gap_comments
    )

    assert result == (1, 0, 1, False)
    assert retry_result == (1, 0, 0, False)
    assert calls == [
        (SongId(201), "#GAP: 20", "neutral"),
        (SongId(202), "#GAP: 30", "neutral"),
        (SongId(201), "#GAP: 20", "neutral"),
    ]


def test_post_gap_comments_suppresses_duplicate_numeric_gap(
    song: UsdbSong, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    changed = _song_with_txt(song, tmp_path, 301, "#GAP: 50.1\n", changed=True)
    posted: list[tuple[SongId, str, str]] = []

    def post_comment(song_id: SongId, text: str, rating: str) -> None:
        posted.append((song_id, text, rating))

    monkeypatch.setattr(mw, "post_song_comment", post_comment)
    posted_gap_comments: set[tuple[SongId, Decimal]] = set()

    first_result = mw._post_gap_comments(
        [changed], utils.ProgressProxy("test"), posted_gap_comments
    )
    assert changed.sync_meta
    txt_path = changed.sync_meta.txt_path()
    assert txt_path
    txt_path.write_text("#GAP: 50,1\n", encoding="utf-8")
    duplicate_result = mw._post_gap_comments(
        [changed], utils.ProgressProxy("test"), posted_gap_comments
    )
    txt_path.write_text("#GAP: 51,1\n", encoding="utf-8")
    changed_gap_result = mw._post_gap_comments(
        [changed], utils.ProgressProxy("test"), posted_gap_comments
    )

    assert first_result == (1, 0, 0, False)
    assert duplicate_result == (0, 1, 0, False)
    assert changed_gap_result == (1, 0, 0, False)
    assert posted == [
        (SongId(301), "#GAP: 50.1", "neutral"),
        (SongId(301), "#GAP: 51,1", "neutral"),
    ]


def _song_with_txt(
    song: UsdbSong,
    folder: Path,
    song_id: int,
    contents: str | None,
    *,
    changed: bool,
) -> UsdbSong:
    txt_path = folder / f"{song_id}.txt"
    if contents is not None:
        txt_path.write_text(contents, encoding="utf-8")

    file = (
        ResourceFile.new(txt_path, "local text")
        if contents is not None
        else ResourceFile(txt_path.name, 0, "local text")
    )
    if changed or contents is None:
        file.mtime = 0
    else:
        file.mtime = utils.get_mtime(txt_path)
    # Verify the action refreshes a potentially stale cached icon result.
    file._is_in_sync = True

    assert song.sync_meta
    sync_meta = attrs.evolve(
        song.sync_meta,
        song_id=SongId(song_id),
        path=folder / f"{song_id}.usdb",
        txt=Resource(JobStatus.SUCCESS, file),
    )
    return attrs.evolve(song, song_id=SongId(song_id), sync_meta=sync_meta)
