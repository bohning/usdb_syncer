"""Tests for utils."""

import os
import sys
import unicodedata
from collections.abc import Callable
from pathlib import Path

import pytest

from usdb_syncer import utils
from usdb_syncer.utils import extract_youtube_id, resource_file_ending

FAKE_YOUTUBE_ID = "fake_YT-id0"
FAKE_LD_LIBRARY_PATH = "/tmp/_MEI12345:/usr/lib:/usr/local/lib"  # noqa: S108


def test_extract_youtube_id(resource_dir: Path) -> None:
    with resource_dir.joinpath("youtube_urls.txt").open(encoding="utf-8") as file:
        urls = file.read().splitlines()
    for url in urls:
        assert extract_youtube_id(url) == FAKE_YOUTUBE_ID


@pytest.mark.parametrize(
    "name,expected",
    [
        ("artist - title.mp3", ".mp3"),
        ("artist - title.mp3.m4a", ".m4a"),
        ("artist - title [BG].JPG", " [BG].JPG"),
    ],
)
def test_resource_file_ending(name: str, expected: str) -> None:
    assert resource_file_ending(name) == expected


def _nfc(name: str) -> str:
    return unicodedata.normalize("NFC", name)


def _nfd(name: str) -> str:
    return unicodedata.normalize("NFD", name)


def _simulate_macos_exfat(
    monkeypatch: pytest.MonkeyPatch, lookup: Callable[[str], str] = _nfc
) -> None:
    """Simulate macOS on exFAT with NFC names stored.

    unlink and rmdir only succeed for NFC paths and never relative to a dir_fd
    (shutil.rmtree passes the listed, i.e. NFD, name there). lstat resolves a path
    via `lookup`, which by default finds the stored file by any form.
    """
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(utils.settings, "get_trash_files", lambda: False)
    real_lstat = os.lstat
    monkeypatch.setattr(os, "lstat", lambda path: real_lstat(lookup(os.fsdecode(path))))
    for name in ("unlink", "rmdir"):
        real = getattr(os, name)

        def fake(path, *, dir_fd=None, _real=real):  # type: ignore[no-untyped-def]
            if dir_fd is not None or not unicodedata.is_normalized(
                "NFC", os.fsdecode(path)
            ):
                raise FileNotFoundError(path)
            _real(path)

        monkeypatch.setattr(os, name, fake)


def test_delete_file_by_other_normalization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _simulate_macos_exfat(monkeypatch)
    file = tmp_path / _nfc("Runął.txt")
    file.touch()
    utils.trash_or_delete_path(tmp_path / _nfd("Runął.txt"))
    assert not file.exists()


def test_delete_dir_with_entries_not_deletable_by_listed_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _simulate_macos_exfat(monkeypatch)
    folder = tmp_path / _nfc("Runął")
    (folder / "sub").mkdir(parents=True)
    (folder / _nfc("ä.txt")).touch()
    (folder / "sub" / _nfc("ö.txt")).touch()
    (folder / "link").symlink_to(folder / "sub")
    utils.trash_or_delete_path(folder)
    assert not folder.exists()


def _nfd_is_missing(path: str) -> str:
    return path if unicodedata.is_normalized("NFC", path) else f"{path}.missing"


def _nfd_is_other_file(path: str) -> str:
    return path if unicodedata.is_normalized("NFC", path) else f"{_nfc(path)}.other"


@pytest.mark.parametrize("lookup", [_nfd_is_missing, _nfd_is_other_file])
def test_delete_does_not_retry_if_other_form_is_another_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lookup: Callable[[str], str]
) -> None:
    file = tmp_path / _nfc("Runął.txt")
    file.touch()
    file.with_name(f"{file.name}.other").touch()
    _simulate_macos_exfat(monkeypatch, lookup)
    with pytest.raises(FileNotFoundError):
        utils.trash_or_delete_path(tmp_path / _nfd("Runął.txt"))
    assert file.exists()
