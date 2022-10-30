"""Tests for functions from the usdb_scraper module."""

import os

from bs4 import BeautifulSoup

from usdb_dl.usdb_scraper import _parse_song_page, _parse_song_txt_from_txt_page


def get_soup(resource_dir: str, resource: str) -> BeautifulSoup:
    with open(os.path.join(resource_dir, "html", resource), encoding="utf8") as html:
        return BeautifulSoup(html, "lxml")


def test__parse_song_txt_from_txt_page(resource_dir: str) -> None:
    soup = get_soup(resource_dir, "txt_page.htm")
    txt = _parse_song_txt_from_txt_page(soup)
    assert txt.startswith("#ARTIST:")
    assert txt.endswith("\nE")


def test__parse_song_page_with_commented_embedded_video(resource_dir: str) -> None:
    soup = get_soup(resource_dir, "song_page_with_embedded_video.htm")
    details = _parse_song_page(soup, 123)
    assert details.song_id == 123
    assert details.artist == "Revolverheld"
    assert details.title == "Ich lass für dich das Licht an"
    assert details.cover_url == "http://usdb.animux.de/images/coverflow/cover/26152.jpg"
    assert details.bpm == 276.17
    assert details.gap == 120000
    assert details.golden_notes
    assert not details.song_check
    assert details.date == "10.10.22"
    assert details.time == "19:47"
    assert details.uploader == "bohning"
    assert details.editors == []
    assert details.views == 27
    assert details.rating == 5
    assert details.votes == 1
    assert details.audio_sample is None
    assert details.team_comment is None
    assert len(details.comments) == 2
    assert details.comments[0].date == "2022-10-11"
    assert details.comments[0].time == "10:46"
    assert details.comments[0].author == "sportgonzo"
    assert details.comments[0].contents.text == "Perfekt"
    assert details.comments[0].contents.youtube_ids == []
    assert details.comments[0].contents.urls == []
    assert details.comments[1].date == "2022-10-10"
    assert details.comments[1].time == "19:48"
    assert details.comments[1].author == "bohning"
    assert details.comments[1].contents.text == ""
    assert details.comments[1].contents.youtube_ids == []
    assert details.comments[1].contents.urls == ["http://www.youtube.com/v/Vf0MC3CFihY"]
