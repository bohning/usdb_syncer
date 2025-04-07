"""Tests for utils."""

import os
from pathlib import Path

import pytest

from usdb_syncer.utils import LinuxEnvCleaner, extract_youtube_id, resource_file_ending

FAKE_YOUTUBE_ID = "fake_YT-id0"


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


def test_linux_env_cleaner(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the LinuxEnvCleaner context manager."""

    # Mock the platform to simulate Linux
    monkeypatch.setattr("sys.platform", "linux")

    # Mock environment variables
    mock_env = {
        "FIRST_ENV_VAR": "value1",
        "LD_LIBRARY_PATH": "/tmp/_MEI12345:/usr/lib:/usr/local/lib",
        "QT_PLUGIN_PATH": "/some/qt/path",
        "QT_QPA_PLATFORM_PLUGIN_PATH": "/another/qt/path",
        "QT_DEBUG_PLUGINS": "1",
        "OTHER_ENV_VAR": "value",
    }
    monkeypatch.setattr("os.environ", mock_env.copy())

    with LinuxEnvCleaner() as cleaned_env:
        # Check that /tmp/_MEI paths are removed from LD_LIBRARY_PATH
        assert cleaned_env["LD_LIBRARY_PATH"] == "/usr/lib:/usr/local/lib"

        # Check that Qt-related paths are removed
        assert "QT_PLUGIN_PATH" not in cleaned_env
        assert "QT_QPA_PLATFORM_PLUGIN_PATH" not in cleaned_env
        assert "QT_DEBUG_PLUGINS" not in cleaned_env

        # Check that other environment variables remain unchanged
        assert cleaned_env["FIRST_ENV_VAR"] == "value1"
        assert cleaned_env["OTHER_ENV_VAR"] == "value"

    # Ensure the environment is restored after exiting the context
    assert os.environ == mock_env


def test_linux_env_cleaner_with_add(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the LinuxEnvCleaner context manager with added environment variables."""

    # Mock the platform to simulate Linux
    monkeypatch.setattr("sys.platform", "linux")

    # Mock environment variables
    monkeypatch.setenv("FIRST_ENV_VAR", "value1")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/_MEI12345:/usr/lib:/usr/local/lib")
    monkeypatch.setenv("QT_PLUGIN_PATH", "/some/qt/path")
    monkeypatch.setenv("QT_QPA_PLATFORM_PLUGIN_PATH", "/another/qt/path")
    monkeypatch.setenv("QT_DEBUG_PLUGINS", "1")
    monkeypatch.setenv("OTHER_ENV_VAR", "value")

    with LinuxEnvCleaner():
        # Add a new environment variable
        os.environ["NEW_ENV_VAR"] = "new_value"

    # Ensure that the new environment variable is still set
    assert os.environ["NEW_ENV_VAR"] == "new_value"
