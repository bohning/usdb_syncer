"""This module contains pytest fixtures."""

import datetime
from pathlib import Path

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item

from usdb_syncer import SongId, SyncMetaId
from usdb_syncer.meta_tags import ImageMetaTags, MetaTags
from usdb_syncer.sync_meta import ResourceFile, SyncMeta
from usdb_syncer.usdb_scraper import SongDetails
from usdb_syncer.usdb_song import UsdbSong
from usdb_syncer.utils import JobResult


# taken from https://docs.pytest.org/en/latest/example/simple.html#control-skipping-of-tests-according-to-command-line-option
def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config: Config) -> None:
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config: Config, items: list[Item]) -> None:
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


#


@pytest.fixture(scope="session", name="resource_dir")
def resource_dir_fixture() -> Path:
    """Returns the path to the test resource directory.

    Returns:
        Path: The resource directory path.
    """
    return Path(__file__).parent.joinpath("resources")


@pytest.fixture(name="song")
def usdb_song_fixture() -> UsdbSong:
    return example_usdb_song()


def example_usdb_song() -> UsdbSong:
    song_id = SongId(123)
    sync_meta_id = SyncMetaId.new()
    return UsdbSong(
        sample_url="",
        song_id=song_id,
        usdb_mtime=0,
        artist="Foo",
        title="Bar",
        genre="Pop",
        year=1999,
        language="Esperanto",
        creator="unknown",
        edition="",
        golden_notes=True,
        rating=0,
        views=1,
        sync_meta=SyncMeta(
            sync_meta_id=sync_meta_id,
            song_id=song_id,
            usdb_mtime=0,
            path=Path(f"C:/{sync_meta_id.to_filename()}"),
            mtime=0,
            meta_tags=MetaTags(),
            audio=ResourceFile(
                "song.mp3", 1, "example.org/song.mp3", JobResult.SUCCESS
            ),
        ),
    )


def example_meta_tags() -> MetaTags:
    return MetaTags(
        video="https://example.com/video.mp4",
        cover=ImageMetaTags(source="https://example.com/cover.jpg"),
        background=ImageMetaTags(source="https://example.com/bg.jpg"),
    )


def example_notes_str(meta_tags: MetaTags | None = None) -> str:
    return f"""#TITLE:title
#ARTIST:artist
#BPM:250
#GAP:12345
#VIDEO:{meta_tags or MetaTags()!s}
: 0 1 0 first note 
* 2 1 0 golden 
F 4 1 0 freestyle 
R 6 1 0 rap 
G 8 1 0 golden freestyle
- 10 12
: 12 1 0 one 
: 14 1 0 more
- 16
: 18 1 0 and 
: 20 1 0 another
E
"""  # noqa: W291


def details_from_song(song: UsdbSong) -> SongDetails:
    return SongDetails(
        song_id=song.song_id,
        artist=song.artist,
        title=song.title,
        genre=song.genre,
        year=song.year,
        language=song.language,
        edition=song.edition,
        golden_notes=song.golden_notes,
        rating=song.rating,
        views=song.views,
        cover_url=None,
        bpm=250.0,
        gap=12345.0,
        song_check=False,
        date_time=datetime.datetime(2024, 7, 20),
        uploader="unknown",
        editors=[],
        votes=100,
        audio_sample=None,
    )
