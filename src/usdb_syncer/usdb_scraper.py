"""Functionality related to the usdb.animux.de web page."""

import re
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import attrs
from bs4 import BeautifulSoup, NavigableString, Tag

from usdb_syncer import SongId, errors
from usdb_syncer.constants import (
    SUPPORTED_VIDEO_SOURCES_REGEX,
    Usdb,
    UsdbStrings,
    UsdbStringsEnglish,
    UsdbStringsFrench,
    UsdbStringsGerman,
)
from usdb_syncer.logger import Logger, song_logger
from usdb_syncer.usdb_song import UsdbSong
from usdb_syncer.utils import extract_youtube_id

WELCOME_REGEX = re.compile(
    r"<td class='row3' colspan='2'>\s*<span class='gen'>([^<]+) <b>([^<]+)</b>"
)
SONG_LIST_ROW_REGEX = re.compile(
    r'<td(?:.*?<source src="(?P<sample_url>.*?)".*?)?></td>'
    r'<td onclick="show_detail\((?P<song_id>\d+)\)".*?>'
    r'<img src="(?P<cover_url>.*?)".*?></td>'
    r'<td onclick="show_detail\(\d+\)">(?P<artist>.*?)</td>\n'
    r'<td onclick="show_detail\(\d+\)"><a href=.*?>(?P<title>.*?)</td>\n'
    r'<td onclick="show_detail\(\d+\)">(?P<genre>.*?)</td>\n'
    r'<td onclick="show_detail\(\d+\)">(?P<year>.*?)</td>\n'
    r'<td onclick="show_detail\(\d+\)">(?P<edition>.*?)</td>\n'
    r'<td onclick="show_detail\(\d+\)">(?P<golden_notes>.*?)</td>\n'
    r'<td onclick="show_detail\(\d+\)">(?P<language>.*?)</td>\n'
    r'<td onclick="show_detail\(\d+\)">(?P<creator>.*?)</td>\n'
    r'<td onclick="show_detail\(\d+\)">(?P<rating>.*?)</td>\n'
    r'<td onclick="show_detail\(\d+\)">(?P<views>.*?)</td>'
)


@attrs.define(kw_only=True)
class CommentContents:
    """The parsed contents of a SongComment."""

    text: str
    youtube_ids: list[str]
    urls: list[str]


class SongComment:
    """A comment to a song on USDB."""

    date_time: datetime
    author: str
    contents: CommentContents

    def __init__(
        self, *, date_time: str, author: str, contents: CommentContents
    ) -> None:
        self.date_time = datetime.strptime(date_time, Usdb.DATETIME_STRF)
        self.author = author
        self.contents = contents


@attrs.define
class SongDetails:
    """Details about a song that USDB shows on a song's page, or are specified in the
    comment section."""

    song_id: SongId
    artist: str
    title: str
    cover_url: str | None
    language: str
    year: int | None
    genre: str
    edition: str
    bpm: float
    gap: float
    golden_notes: bool
    song_check: bool
    date_time: datetime
    uploader: str
    editors: list[str]
    views: int
    rating: int
    votes: int
    audio_sample: str | None
    comments: list[SongComment] = attrs.field(factory=list)

    def all_comment_videos(self) -> Iterator[str]:
        """Yields all parsed URLs and YouTube ids. Order is latest to earliest, then ids
        before URLs.
        """
        for comment in self.comments:
            yield from comment.contents.youtube_ids
            yield from comment.contents.urls


def username_from_html(html: str) -> str | None:
    if match := WELCOME_REGEX.search(html):
        return match.group(2)
    return None


def parse_song_page(soup: BeautifulSoup, song_id: SongId) -> SongDetails:
    logger = song_logger(song_id)
    usdb_strings = _usdb_strings_from_soup(soup)
    details_table, comments_table, *_ = soup.find_all("table", border="0", width="500")
    assert isinstance(details_table, Tag)
    assert isinstance(comments_table, Tag)
    details = _parse_details_table(details_table, song_id, usdb_strings, logger)
    details.comments = _parse_comments_table(comments_table, logger)
    return details


def _usdb_strings_from_soup(soup: BeautifulSoup) -> type[UsdbStrings]:
    span = soup.find("span", class_="gen")
    assert span
    return _usdb_strings_from_welcome(span.text.split(" ", 1)[0].removesuffix(","))


def _usdb_strings_from_html(html: str) -> type[UsdbStrings]:
    if match := WELCOME_REGEX.search(html):
        return _usdb_strings_from_welcome(match.group(1))
    raise errors.UsdbUnknownLanguageError


def _usdb_strings_from_welcome(welcome_string: str) -> type[UsdbStrings]:
    match welcome_string:
        case UsdbStringsEnglish.WELCOME:
            return UsdbStringsEnglish
        case UsdbStringsGerman.WELCOME:
            return UsdbStringsGerman
        case UsdbStringsFrench.WELCOME:
            return UsdbStringsFrench
    raise errors.UsdbUnknownLanguageError


def parse_songs_from_songlist(html: str) -> Iterator[UsdbSong]:
    return (
        UsdbSong.from_html(
            _usdb_strings_from_html(html),
            sample_url=match["sample_url"] or "",
            song_id=match["song_id"],
            artist=match["artist"],
            title=match["title"],
            genre=match["genre"],
            year=match["year"],
            edition=match["edition"],
            golden_notes=match["golden_notes"],
            language=match["language"],
            creator=match["creator"],
            rating=match["rating"],
            views=match["views"],
        )
        for match in SONG_LIST_ROW_REGEX.finditer(html)
    )


def _parse_details_table(
    details_table: Tag, song_id: SongId, usdb_strings: type[UsdbStrings], logger: Logger
) -> SongDetails:
    """Parse song attributes from usdb page.

    Parameters:
        details: dict of song attributes
        details_table: BeautifulSoup object of song details table
    """
    editors = []
    pointer = details_table.find(string=usdb_strings.SONG_EDITED_BY)
    while pointer is not None:
        pointer = pointer.find_next("td")
        if pointer.a is None:  # type: ignore
            break
        editors.append(pointer.text.strip())  # type: ignore
        pointer = pointer.find_next("tr")  # type: ignore

    stars = details_table.find(string=usdb_strings.SONG_RATING).next.find_all("img")  # type: ignore
    votes_str = details_table.find(string=usdb_strings.SONG_RATING).next_element.text  # type: ignore

    audio_sample = ""
    if param := details_table.find("source"):
        assert isinstance(param, Tag)
        src = param.get("src")
        assert isinstance(src, str)
        audio_sample = src
    else:
        logger.debug("No audio sample found. Consider adding one!")

    cover_url = details_table.img["src"]  # type: ignore
    assert isinstance(cover_url, str)
    if "nocover" in cover_url:
        logger.debug("No USDB cover. Consider adding one!")

    year_str = _find_text_after(details_table, usdb_strings.SONG_YEAR)
    year = int(year_str) if len(year_str) == 4 and year_str.isdigit() else None

    return SongDetails(
        song_id=song_id,
        artist=details_table.find_next("td").text,  # type: ignore
        title=details_table.find_next("td").find_next("td").text,  # type: ignore
        cover_url=None if "nocover" in cover_url else Usdb.BASE_URL + cover_url,
        language=_find_text_after(details_table, usdb_strings.SONG_LANGUAGE),
        year=year,
        genre=_find_text_after(details_table, "Genre"),
        edition=_find_text_after(details_table, "Edition"),
        bpm=float(_find_text_after(details_table, "BPM").replace(",", ".")),
        gap=float(_find_text_after(details_table, "GAP").replace(",", ".") or 0),
        golden_notes=_find_text_after(details_table, usdb_strings.GOLDEN_NOTES)
        == usdb_strings.YES,
        song_check=_find_text_after(details_table, usdb_strings.SONGCHECK)
        == usdb_strings.YES,
        date_time=datetime.strptime(
            _find_text_after(details_table, usdb_strings.DATE), Usdb.DATETIME_STRF
        ),
        uploader=_find_text_after(details_table, usdb_strings.UPLOADED_BY),
        editors=editors,
        views=int(_find_text_after(details_table, usdb_strings.VIEWS)),
        rating=sum("star.png" in s.get("src") for s in stars),
        votes=int(votes_str.split("(")[1].split(")")[0]),
        audio_sample=audio_sample or None,
    )


def _find_text_after(details_table: Tag, label: str) -> str:
    if isinstance((tag := details_table.find(string=label)), NavigableString):
        if isinstance(tag.next, Tag):
            return tag.next.text.strip()
    raise errors.UsdbParseError(f"Text after {label} not found.")  # noqa: TRY003


def _parse_comments_table(comments_table: Tag, logger: Logger) -> list[SongComment]:
    """Parse the table into individual comments, extracting potential video links,
    GAP and BPM values.
    """
    comments = []
    # last entry is the field to enter a new comment, so this one is ignored
    for header in comments_table.find_all("tr", class_="list_tr2")[:-1]:
        assert isinstance(header, Tag)
        td = header.find("td")
        assert isinstance(td, Tag)
        meta = td.text.strip()
        if " | " not in meta:
            # header is just the placeholder element
            break
        date_time, author = meta.removeprefix("[del] [edit] ").split(" | ")
        assert isinstance(header.next_sibling, Tag)
        contents = _parse_comment_contents(header.next_sibling, logger)
        comments.append(
            SongComment(date_time=date_time, author=author, contents=contents)
        )

    return comments


def _parse_comment_contents(contents: Tag, logger: Logger) -> CommentContents:
    td_element = contents.find("td")
    assert isinstance(td_element, Tag)
    for emoji in td_element.find_all("img"):
        assert isinstance(emoji, Tag)
        title = emoji.get("title")
        assert isinstance(title, str)
        emoji.replace_with(NavigableString(title))

    text = td_element.text.strip()  # type: ignore
    urls: list[str] = []
    youtube_ids: list[str] = []

    for url in _all_urls_in_comment(contents, text, logger):
        if yt_id := extract_youtube_id(url):
            youtube_ids.append(yt_id)
        else:
            urls.append(url)

    return CommentContents(text=text, urls=urls, youtube_ids=youtube_ids)


def _all_urls_in_comment(contents: Tag, text: str, logger: Logger) -> Iterator[str]:
    for embed in contents.find_all("embed"):
        if src := _extract_supported_video_source(embed, "src"):
            logger.debug("Video embed found. Consider embedding as iframe.")
            yield src
    for iframe in contents.find_all("iframe"):
        if src := _extract_supported_video_source(iframe, "src"):
            yield src
    for anchor in contents.find_all("a"):
        if url := _extract_supported_video_source(anchor, "href"):
            logger.debug("Video href found. Consider embedding as iframe.")
            yield url
    for match in SUPPORTED_VIDEO_SOURCES_REGEX.finditer(text):
        logger.debug("Video plain url found. Consider embedding as iframe.")
        yield match.group(1)


def _extract_supported_video_source(tag: Any, attr_key: str) -> str | None:
    if (
        isinstance(tag, Tag)
        and isinstance(src := tag.get(attr_key), str)
        and SUPPORTED_VIDEO_SOURCES_REGEX.fullmatch(src)
    ):
        return src
    return None


def parse_song_txt_from_txt_page(soup: BeautifulSoup) -> str:
    if isinstance(textarea := soup.find("textarea"), Tag):
        return textarea.string or ""
    raise errors.UsdbParseError("textarea for notes not found")  # noqa: TRY003
