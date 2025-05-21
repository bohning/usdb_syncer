"""Tests for functions from the usdb_scraper module."""

from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

from usdb_syncer import SongId
from usdb_syncer.usdb_scraper import (
    parse_song_page,
    parse_song_txt_from_txt_page,
    parse_songs_from_songlist,
)


def get_soup(resource_dir: Path, resource: str) -> BeautifulSoup:
    with resource_dir.joinpath("html", "usdb-animux-de", resource).open(
        encoding="utf8"
    ) as html:
        return BeautifulSoup(html, "lxml")


def test__parse_song_txt_from_txt_page(resource_dir: Path) -> None:
    soup = get_soup(resource_dir, "txt_page.htm")
    txt = parse_song_txt_from_txt_page(soup)
    assert txt is not None
    assert txt.startswith("#ARTIST:")
    assert txt.endswith("\nE")


def test__parse_song_page_with_commented_embedded_video(resource_dir: Path) -> None:
    song_id = SongId(26152)
    soup = get_soup(resource_dir, "song_page_with_embedded_video.htm")
    details = parse_song_page(soup, song_id)
    assert details.song_id == song_id
    assert details.artist == "Revolverheld"
    assert details.title == "Ich lass für dich das Licht an"
    assert details.cover_url == "https://usdb.animux.de/data/cover/26152.jpg"
    assert details.year == 2013
    assert details.genre == "Pop"
    assert details.bpm == 276.17
    assert details.gap == 120000
    assert details.golden_notes
    assert not details.song_check
    assert details.date_time == datetime(2022, 10, 10, 19, 47)
    assert details.uploader == "bohning"
    assert details.editors == []
    assert details.views == 27
    assert details.rating == 5
    assert details.votes == 1
    assert details.audio_sample is None
    assert len(details.comments) == 2
    assert details.comments[0].date_time == datetime(2022, 10, 11, 10, 46)
    assert details.comments[0].author == "sportgonzo"
    assert details.comments[0].contents.text == "Perfekt :-)"
    assert details.comments[0].contents.youtube_ids == []
    assert details.comments[0].contents.urls == []
    assert details.comments[1].date_time == datetime(2022, 10, 10, 19, 48)
    assert details.comments[1].author == "bohning"
    assert details.comments[1].contents.text == ""
    assert details.comments[1].contents.youtube_ids == ["Vf0MC3CFihY"]
    assert details.comments[1].contents.urls == []


def test__parse_song_page_with_commented_unembedded_video(resource_dir: Path) -> None:
    song_id = SongId(16575)
    soup = get_soup(resource_dir, "song_page_with_unembedded_video.htm")
    details = parse_song_page(soup, song_id)
    assert len(details.comments) == 1
    assert details.comments[0].contents.youtube_ids == ["WIAvMiUcCgw"]


def test__parse_song_page_without_comments_or_cover(resource_dir: Path) -> None:
    song_id = SongId(26244)
    soup = get_soup(resource_dir, "song_page_without_comments_or_cover.htm")
    details = parse_song_page(soup, song_id)
    assert details.song_id == song_id
    assert details.artist == "The Used"
    assert details.title == "River Stay"
    assert details.cover_url is None
    assert details.year == 2020
    assert details.genre == "Alternative"
    assert details.bpm == 305
    assert details.gap == 548
    assert details.golden_notes
    assert not details.song_check
    assert details.date_time == datetime(2022, 10, 30, 19, 4)
    assert details.uploader == "askusbloodfist"
    assert details.editors == []
    assert details.views == 0
    assert details.rating == 0
    assert details.votes == 0
    assert details.audio_sample is None
    assert len(details.comments) == 0


def test_parse_song_list(resource_dir: Path) -> None:
    html = (resource_dir / "html" / "song_list.htm").read_text(encoding="utf8")
    songs = list(parse_songs_from_songlist(html))
    assert len(songs) == 3
    # first song: no audio sample, but cover image
    assert songs[0].sample_url == ""
    assert songs[0].song_id == SongId(29199)
    assert songs[0].artist == "AUT of ORDA"
    assert songs[0].title == "hoch gwimmas (n)imma"
    assert songs[0].genre == "Austropop"
    assert songs[0].year == 2023
    assert songs[0].edition == ""
    assert songs[0].golden_notes is False
    assert songs[0].language == "German"
    assert songs[0].creator == "ultron"
    assert songs[0].rating == 0
    assert songs[0].views == 0
    # second song: no audio sample, default nocover.png
    assert songs[1].sample_url == ""
    assert songs[1].song_id == SongId(29198)
    assert songs[1].artist == "Les enfantastiques"
    assert songs[1].title == "Si j’allais en Chine"  # noqa: RUF001
    assert songs[1].genre == ""
    assert songs[1].year is None
    assert songs[1].edition == ""
    assert songs[1].golden_notes is True
    assert songs[1].language == "French"
    assert songs[1].creator == "ultrastarlover75"
    assert songs[1].rating == 0
    assert songs[1].views == 1
    # third song: audio sample and cover
    assert songs[2].sample_url == "song_list_files/2239202.mp3"
    assert songs[2].song_id == SongId(29197)
    assert songs[2].artist == "STEFAN"
    assert songs[2].title == "Hope (ESC 2022 Estonia)"
    assert songs[2].genre == "Western-Pop"
    assert songs[2].year == 2022
    assert songs[2].edition == "Eurovision Song Contest 2022"
    assert songs[2].golden_notes is True
    assert songs[2].language == "English"
    assert songs[2].creator == "Dragon33"
    assert songs[2].rating == 0
    assert songs[2].views == 2
