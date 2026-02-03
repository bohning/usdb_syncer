"""Tests for functions from the usdb_scraper module."""

from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

from usdb_syncer import SongId
from usdb_syncer.usdb_scraper import (
    _parse_song_page,
    _parse_song_txt_from_txt_page,
    _parse_songs_from_songlist,
)


def get_soup(resource_dir: Path, resource: str) -> BeautifulSoup:
    with resource_dir.joinpath("html", "usdb-animux-de", resource).open(
        encoding="utf8"
    ) as html:
        return BeautifulSoup(html, "lxml")


def test__parse_song_txt_from_txt_page(resource_dir: Path) -> None:
    soup = get_soup(resource_dir, "txt_page.htm")
    txt = _parse_song_txt_from_txt_page(soup)
    assert txt.startswith("#ARTIST:")
    assert txt.endswith("\nE")


def test__parse_song_page_with_commented_embedded_video(resource_dir: Path) -> None:
    song_id = SongId(26152)
    soup = get_soup(resource_dir, "song_page_with_embedded_video.htm")
    details = _parse_song_page(soup, song_id)
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
    details = _parse_song_page(soup, song_id)
    assert len(details.comments) == 1
    assert details.comments[0].contents.youtube_ids == ["WIAvMiUcCgw"]


def test__parse_song_page_without_comments_or_cover(resource_dir: Path) -> None:
    song_id = SongId(26244)
    soup = get_soup(resource_dir, "song_page_without_comments_or_cover.htm")
    details = _parse_song_page(soup, song_id)
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
    html = (resource_dir / "html" / "usdb-animux-de" / "song_list.htm").read_text(
        encoding="utf8"
    )
    songs = list(_parse_songs_from_songlist(html))
    assert len(songs) == 3

    assert songs[0].song_id == SongId(57)
    assert songs[0].usdb_mtime == 1204046489
    assert songs[0].artist == "Albert Hammond"
    assert songs[0].title == "It Never Rains In Southern California"
    assert songs[0].genre == "Soft Rock"
    assert songs[0].year == 1972
    assert songs[0].language == "English"
    assert songs[0].creator == "Canni"
    assert songs[0].edition == ""
    assert songs[0].golden_notes is False
    assert songs[0].rating == 0
    assert songs[0].views == 446
    assert (
        songs[0].sample_url
        == "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview115/v4/cb/4b/aa/cb4baa80-8845-098f-c52e-f1a4280dd5e5/mzaf_9190069867172822903.plus.aac.ep.m4a"
    )

    assert songs[1].song_id == SongId(59)
    assert songs[1].usdb_mtime == 1204046505
    assert songs[1].artist == "Alex Britti"
    assert songs[1].title == "Prendere o lasciare"
    assert songs[1].genre == ""
    assert songs[1].year == 2005
    assert songs[1].language == "Italian, English"
    assert songs[1].creator == "Canni"
    assert songs[1].edition == "SingStar top.it"
    assert songs[1].golden_notes is True
    assert songs[1].rating == 0
    assert songs[1].views == 339
    assert (
        songs[1].sample_url
        == "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview125/v4/e9/09/16/e909161b-7076-e86f-ee75-daf8d4b6546e/mzaf_2071895916635162352.plus.aac.ep.m4a"
    )

    assert songs[2].song_id == SongId(60)
    assert songs[2].usdb_mtime == 1708538299
    assert songs[2].artist == "Alexander Klaws"
    assert songs[2].title == "Take Me Tonight"
    assert songs[2].genre == "Pop"
    assert songs[2].year == 2003
    assert songs[2].language == "English"
    assert songs[2].creator == "Canni, b4St1@fuN"
    assert songs[2].edition == "[SC]-Songs"
    assert songs[2].golden_notes is True
    assert songs[2].rating == 5
    assert songs[2].views == 652
    assert (
        songs[2].sample_url
        == "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview115/v4/07/7e/37/077e37a6-58ae-91bd-0e30-7311b7b1807c/mzaf_17099415661794586176.plus.aac.ep.m4a"
    )
