"""Integration tests for the song_loader module."""

import copy
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from tests.conftest import (
    details_from_song,
    example_meta_tags,
    example_notes_str,
    example_usdb_song,
)
from usdb_syncer import download_options, utils
from usdb_syncer.db import DownloadStatus
from usdb_syncer.meta_tags import MetaTags
from usdb_syncer.path_template import PathTemplate
from usdb_syncer.resource_dl import ImageKind, ResourceDLResult
from usdb_syncer.song_loader import _SongLoader
from usdb_syncer.sync_meta import MTIME_TOLERANCE_SECS, ResourceFile


def _download_and_process_image(
    url: Any,
    *,
    target_stem: Path,
    meta_tags: Any,
    details: Any,
    kind: ImageKind,
    max_width: Any,
    process: bool = True,
) -> Path | None:
    path = target_stem.with_name(f"{target_stem.name} [{kind.value}].jpg")
    path.touch()
    return path


def _download_audio(
    resource: Any, options: Any, browser: Any, path_stem: Path, logger: Any
) -> ResourceDLResult:
    path_stem.with_suffix(".mp3").touch()
    return ResourceDLResult(extension="mp3")


def _download_video(
    resource: Any, options: Any, browser: Any, path_stem: Path, logger: Any
) -> ResourceDLResult:
    path_stem.with_suffix(".mp4").touch()
    return ResourceDLResult(extension="mp4")


def _options(
    song_dir: Path,
    path_template: str,
    *,
    audio: bool = False,
    video: bool = False,
    cover: bool = False,
    background: bool = False,
) -> download_options.Options:
    options_dict = download_options.download_options().__dict__
    options_dict["song_dir"] = song_dir
    options_dict["path_template"] = PathTemplate.parse(path_template)
    if not audio:
        options_dict["audio_options"] = None
    if not video:
        options_dict["video_options"] = None
    if not cover:
        options_dict["cover"] = None
    if not background:
        options_dict["background_options"] = None
    return download_options.Options(**options_dict)


_db = mock.MagicMock()


@mock.patch("usdb_syncer.song_loader.db", _db)
@mock.patch("usdb_syncer.usdb_song.db", _db)
@mock.patch("usdb_syncer.sync_meta.db", _db)
@mock.patch("usdb_syncer.resource_dl.download_audio", side_effect=_download_audio)
@mock.patch("usdb_syncer.resource_dl.download_video", _download_video)
@mock.patch(
    "usdb_syncer.resource_dl.download_and_process_image", _download_and_process_image
)
@mock.patch("usdb_syncer.song_loader.events", mock.Mock())
class SongLoaderTestCase(unittest.TestCase):
    """Tests for the song loader."""

    @mock.patch("usdb_syncer.usdb_scraper.UsdbSession.get_song_details")
    @mock.patch("usdb_syncer.usdb_scraper.UsdbSession.get_notes")
    def test_download_new_song(
        self, notes_mock: mock.Mock, details_mock: mock.Mock, _audio_mock: mock.Mock
    ) -> None:
        song = example_usdb_song()
        song.sync_meta = None
        notes_mock.return_value = example_notes_str(example_meta_tags())
        details_mock.return_value = details_from_song(song)

        with tempfile.TemporaryDirectory() as song_dir_str:
            song_dir = Path(song_dir_str)
            options = _options(
                song_dir,
                ":artist:/:title:/:id:",
                audio=True,
                video=True,
                cover=True,
                background=True,
            )

            loader = _SongLoader(song, options)
            loader.run()

            out = loader.song
            assert out.status == DownloadStatus.NONE
            path_stem = song_dir / out.artist / out.title / str(out.song_id)
            assert out.sync_meta
            assert path_stem.parent.exists()
            sync_meta_path = path_stem.parent / out.sync_meta.sync_meta_id.to_filename()
            assert out.sync_meta.mtime == utils.get_mtime(sync_meta_path)
            for meta, ext in (
                (out.sync_meta.txt, ".txt"),
                (out.sync_meta.audio, ".mp3"),
                (out.sync_meta.video, ".mp4"),
                (out.sync_meta.cover, " [CO].jpg"),
                (out.sync_meta.background, " [BG].jpg"),
            ):
                with self.subTest(ext=ext):
                    assert meta
                    assert meta.fname == path_stem.name + ext
                    assert meta.mtime == utils.get_mtime(
                        path_stem.with_name(meta.fname)
                    )

    @mock.patch("usdb_syncer.usdb_scraper.UsdbSession.get_song_details")
    @mock.patch("usdb_syncer.usdb_scraper.UsdbSession.get_notes")
    def test_download_unchanged_resource(
        self, notes_mock: mock.Mock, details_mock: mock.Mock, audio_mock: mock.Mock
    ) -> None:
        song = example_usdb_song()
        assert song.sync_meta
        notes_mock.return_value = example_notes_str(MetaTags(audio="audio.com"))
        details_mock.return_value = details_from_song(song)

        with tempfile.TemporaryDirectory() as song_dir_str:
            song_dir = Path(song_dir_str)
            options = _options(song_dir, ":title: / song", audio=True)
            song.sync_meta.path = (
                song_dir / song.title / song.sync_meta.sync_meta_id.to_filename()
            )
            mp3_path = song.sync_meta.path.parent / "song.mp3"
            song.sync_meta.audio = _mock_resource_file(mp3_path, "audio.com")

            loader = _SongLoader(copy.deepcopy(song), options)
            loader.run()

            audio_mock.assert_not_called()
            assert loader.song.status == DownloadStatus.NONE
            assert loader.song.sync_meta
            assert mp3_path.exists()

    @mock.patch("usdb_syncer.usdb_scraper.UsdbSession.get_song_details")
    @mock.patch("usdb_syncer.usdb_scraper.UsdbSession.get_notes")
    def test_download_misnamed_resource(
        self, notes_mock: mock.Mock, details_mock: mock.Mock, audio_mock: mock.Mock
    ) -> None:
        song = example_usdb_song()
        assert song.sync_meta
        notes_mock.return_value = example_notes_str(MetaTags(audio="audio.com"))
        details_mock.return_value = details_from_song(song)

        with tempfile.TemporaryDirectory() as song_dir_str:
            song_dir = Path(song_dir_str)
            options = _options(song_dir, ":title: / song", audio=True)
            song.sync_meta.path = (
                song_dir / song.artist / song.sync_meta.sync_meta_id.to_filename()
            )
            mp3_path = song.sync_meta.path.parent / "_.mp3"
            song.sync_meta.audio = _mock_resource_file(mp3_path, "audio.com")

            loader = _SongLoader(copy.deepcopy(song), options)
            loader.run()

            assert loader.song.status == DownloadStatus.NONE
            audio_mock.assert_not_called()
            assert loader.song.sync_meta
            assert not mp3_path.exists()
            assert (song_dir / song.title / "song.mp3").exists()

    @mock.patch("usdb_syncer.usdb_scraper.UsdbSession.get_song_details")
    @mock.patch("usdb_syncer.usdb_scraper.UsdbSession.get_notes")
    def test_download_outdated_resource(
        self, notes_mock: mock.Mock, details_mock: mock.Mock, audio_mock: mock.Mock
    ) -> None:
        song = example_usdb_song()
        assert song.sync_meta
        notes_mock.return_value = example_notes_str(MetaTags(audio="audio.com"))
        details_mock.return_value = details_from_song(song)

        with tempfile.TemporaryDirectory() as song_dir_str:
            song_dir = Path(song_dir_str)
            options = _options(song_dir, ":title: / song", audio=True)
            song.sync_meta.path = (
                song_dir / song.title / song.sync_meta.sync_meta_id.to_filename()
            )
            mp3_path = song.sync_meta.path.parent / "song.mp3"
            song.sync_meta.audio = _mock_resource_file(mp3_path, "audio.com")
            # simulate changed file
            song.sync_meta.audio.mtime -= MTIME_TOLERANCE_SECS * 1_000_000 + 1

            loader = _SongLoader(copy.deepcopy(song), options)
            loader.run()

            audio_mock.assert_called_once()
            assert loader.song.status == DownloadStatus.NONE
            assert utils.get_mtime(mp3_path) > song.sync_meta.audio.mtime


def _mock_resource_file(path: Path, resource: str | None = None) -> ResourceFile:
    path.parent.mkdir(exist_ok=True, parents=True)
    path.touch()
    return ResourceFile.new(path, resource or f"https://example.com/{path.name}")
