"""Functionality related to the usdb.animux.de web page."""

import logging
import re
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Iterator, Type

import attrs
import requests
from bs4 import BeautifulSoup, NavigableString, Tag

from usdb_syncer import SongId, settings
from usdb_syncer.constants import (
    SUPPORTED_VIDEO_SOURCES_REGEX,
    Usdb,
    UsdbStrings,
    UsdbStringsEnglish,
    UsdbStringsFrench,
    UsdbStringsGerman,
)
from usdb_syncer.logger import Log
from usdb_syncer.typing_helpers import assert_never
from usdb_syncer.usdb_song import UsdbSong
from usdb_syncer.utils import extract_youtube_id, normalize

_logger: logging.Logger = logging.getLogger(__file__)

SONG_LIST_ROW_REGEX = re.compile(
    r'<td onclick="show_detail\((\d+)\)">(.*)</td>\n'
    r'<td onclick="show_detail\(\d+\)"><a href=.*>(.*)</td>\n'
    r'<td onclick="show_detail\(\d+\)">(.*)</td>\n'
    r'<td onclick="show_detail\(\d+\)">(.*)</td>\n'
    r'<td onclick="show_detail\(\d+\)">(.*)</td>\n'
    r'<td onclick="show_detail\(\d+\)">(.*)</td>\n'
    r'<td onclick="show_detail\(\d+\)">(.*)</td>'
)
WELCOME_REGEX = re.compile(
    r"<td class='row3' colspan='2'>\s*<span class='gen'>([^<]+) <b>"
)


class RequestMethod(Enum):
    """Supported HTTP requests."""

    GET = "GET"
    POST = "POST"


class ParseException(Exception):
    """Raised when HTML from USDB has unexpected format."""


def raises_parse_exception(func: Callable) -> Callable:
    """Converts certain errors of annotated functions that indicate wrong assumptions
    about the parsed HTML into ParseErrors.
    This can be used with '# type: ignore' and an outer try-except clause to parse HTML
    concisely, but safely.
    """

    @wraps(func)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except (AttributeError, IndexError, ValueError) as exception:
            # AttributeError: not existing attribute (e.g. because the object is None)
            # IndexError: list index out of bounds
            # ValueError: too many values to unpack
            raise ParseException from exception

    return wrapped


class CommentContents:
    """The parsed contents of a SongComment."""

    text: str
    youtube_ids: list[str]
    urls: list[str]

    def __init__(self, *, text: str, youtube_ids: list[str], urls: list[str]) -> None:
        self.text = text
        self.youtube_ids = youtube_ids
        self.urls = urls


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
            for ytid in comment.contents.youtube_ids:
                yield ytid
            for url in comment.contents.urls:
                yield url


def get_usdb_page(
    rel_url: str,
    method: RequestMethod = RequestMethod.GET,
    headers: dict[str, str] | None = None,
    payload: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> str:
    """Retrieve html subpage from usdb.

    Parameters:
        rel_url: relative url of page to retrieve
        method: GET or POST
        headers: dict of headers to send with request
        payload: dict of data to send with request
        params: dict of params to send with request
    """
    url = Usdb.BASE_URL + rel_url

    match method:
        case RequestMethod.GET:
            _logger.debug("get request for %s", url)
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=60,
                cookies=settings.get_browser().cookies(),
            )
        case RequestMethod.POST:
            _logger.debug("post request for %s", url)
            response = requests.post(
                url,
                headers=headers,
                data=payload,
                params=params,
                timeout=60,
                cookies=settings.get_browser().cookies(),
            )
        case _ as unreachable:
            assert_never(unreachable)

    response.raise_for_status()
    response.encoding = "utf-8"
    return normalize(response.text)


def get_usdb_details(song_id: SongId) -> SongDetails | None:
    """Retrieve song details from usdb webpage, if song exists.

    Parameters:
        song_id: id of song to retrieve details for
    """
    html = get_usdb_page(
        "index.php", params={"id": str(int(song_id)), "link": "detail"}
    )
    soup = BeautifulSoup(html, "lxml")
    if UsdbStrings.DATASET_NOT_FOUND in soup.get_text():
        return None
    return _parse_song_page(soup, song_id)


def get_usdb_login_status() -> bool:
    html = get_usdb_page("index.php", params={"link": "home"})
    soup = BeautifulSoup(html, "lxml")
    if UsdbStrings.WELCOME_PLEASE_LOGIN in soup.get_text():
        return False
    return True


def _parse_song_page(soup: BeautifulSoup, song_id: SongId) -> SongDetails:
    usdb_strings = _usdb_strings_from_soup(soup)
    details_table, comments_table, *_ = soup.find_all("table", border="0", width="500")
    details = _parse_details_table(details_table, song_id, usdb_strings)
    details.comments = _parse_comments_table(comments_table)
    return details


def _usdb_strings_from_soup(soup: BeautifulSoup) -> Type[UsdbStrings]:
    return _usdb_strings_from_welcome(
        soup.find("span", class_="gen").text.split(" ", 1)[0].removesuffix(",")
    )


def _usdb_strings_from_html(html: str) -> Type[UsdbStrings]:
    if match := WELCOME_REGEX.search(html):
        return _usdb_strings_from_welcome(match.group(1))
    raise ParseException("welcome string not found")


def _usdb_strings_from_welcome(welcome_string: str) -> Type[UsdbStrings]:
    match welcome_string:
        case UsdbStringsEnglish.WELCOME:
            return UsdbStringsEnglish
        case UsdbStringsGerman.WELCOME:
            return UsdbStringsGerman
        case UsdbStringsFrench.WELCOME:
            return UsdbStringsFrench
    raise ParseException("Unknown USDB language.")


def get_usdb_available_songs(
    max_skip_id: SongId, content_filter: dict[str, str] | None = None
) -> list[UsdbSong]:
    """Return a list of all available songs.

    Parameters:
        max_skip_id: only fetch ids larger than this
        content_filter: filters response (e.g. {'artist': 'The Beatles'})
    """
    available_songs: list[UsdbSong] = []
    payload = {"order": "id", "ud": "desc", "limit": str(Usdb.MAX_SONGS_PER_PAGE)}
    payload.update(content_filter or {})
    for start in range(0, Usdb.MAX_SONG_ID, Usdb.MAX_SONGS_PER_PAGE):
        payload["start"] = str(start)
        html = get_usdb_page(
            "index.php", RequestMethod.POST, params={"link": "list"}, payload=payload
        )
        songs = list(
            UsdbSong.from_html(
                _usdb_strings_from_html(html),
                song_id=match[1],
                artist=match[2],
                title=match[3],
                edition=match[4],
                golden_notes=match[5],
                language=match[6],
                rating=match[7],
                views=match[8],
            )
            for match in SONG_LIST_ROW_REGEX.finditer(html)
            if SongId.parse(match[1]) > max_skip_id
        )
        available_songs.extend(songs)

        if len(songs) < Usdb.MAX_SONGS_PER_PAGE:
            break

    _logger.info(f"Fetched {len(available_songs)} new song(s) from USDB.")
    return available_songs


def _parse_details_table(
    details_table: BeautifulSoup, song_id: SongId, usdb_strings: Type[UsdbStrings]
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
        audio_sample = param.get("src")
    else:
        _logger.debug("No audio sample found. Consider adding one!")

    cover_url = details_table.img["src"]  # type: ignore
    if "nocover" in cover_url:
        _logger.debug("No USDB cover. Consider adding one!")

    return SongDetails(
        song_id=song_id,
        artist=details_table.find_next("td").text,  # type: ignore
        title=details_table.find_next("td").find_next("td").text,  # type: ignore
        cover_url=None if "nocover" in cover_url else Usdb.BASE_URL + cover_url,
        bpm=float(_find_text_after(details_table, "BPM").replace(",", ".")),
        gap=float(_find_text_after(details_table, "GAP").replace(",", ".") or 0),
        golden_notes=_find_text_after(details_table, usdb_strings.GOLDEN_NOTES)
        == usdb_strings.YES,
        song_check=_find_text_after(details_table, usdb_strings.SONGCHECK)
        == usdb_strings.YES,
        date_time=datetime.strptime(
            _find_text_after(details_table, usdb_strings.DATE), Usdb.DATETIME_STRF
        ),
        uploader=_find_text_after(details_table, usdb_strings.CREATED_BY),
        editors=editors,
        views=int(_find_text_after(details_table, usdb_strings.VIEWS)),
        rating=sum("star.png" in s.get("src") for s in stars),
        votes=int(votes_str.split("(")[1].split(")")[0]),
        audio_sample=audio_sample or None,
    )


def _find_text_after(details_table: BeautifulSoup, label: str) -> str:
    if isinstance((tag := details_table.find(string=label)), NavigableString):
        if isinstance(tag.next, Tag):
            return tag.next.text.strip()
    raise ParseException(f"Text after {label} not found.")


def _parse_comments_table(comments_table: BeautifulSoup) -> list[SongComment]:
    """Parse the table into individual comments, extracting potential video links,
    GAP and BPM values.

    Parameters:
        details: dict of song attributes
        comments_table: BeautifulSoup object of song details table
    """
    comments = []
    # last entry is the field to enter a new comment, so this one is ignored
    for header in comments_table.find_all("tr", class_="list_tr2")[:-1]:
        meta = header.find("td").text.strip()
        if " | " not in meta:
            # header is just the placeholder element
            break
        date_time, author = meta.removeprefix("[del] [edit] ").split(" | ")
        contents = _parse_comment_contents(header.next_sibling)
        comments.append(
            SongComment(date_time=date_time, author=author, contents=contents)
        )

    return comments


def _parse_comment_contents(contents: BeautifulSoup) -> CommentContents:
    td_element = contents.find("td")
    for emoji in td_element.find_all("img"):
        emoji.replaceWith(emoji.get("title"))

    # text = contents.find("td").text.strip()  # type: ignore
    text = td_element.text.strip()  # type: ignore
    urls: list[str] = []
    youtube_ids: list[str] = []

    for url in _all_urls_in_comment(contents, text):
        if yt_id := extract_youtube_id(url):
            youtube_ids.append(yt_id)
        else:
            urls.append(url)

    return CommentContents(text=text, urls=urls, youtube_ids=youtube_ids)


def _all_urls_in_comment(contents: BeautifulSoup, text: str) -> Iterator[str]:
    for embed in contents.find_all("embed"):
        if (src := embed.get("src")) and SUPPORTED_VIDEO_SOURCES_REGEX.fullmatch(src):
            _logger.debug("video embed found. Consider embedding as iframe")
            yield src
    for iframe in contents.find_all("iframe"):
        if (src := iframe.get("src")) and SUPPORTED_VIDEO_SOURCES_REGEX.fullmatch(src):
            yield src
    for anchor in contents.find_all("a"):
        if (url := anchor.get("href")) and SUPPORTED_VIDEO_SOURCES_REGEX.fullmatch(url):
            _logger.debug("video href found. Consider embedding as iframe")
            yield url
    for match in SUPPORTED_VIDEO_SOURCES_REGEX.finditer(text):
        _logger.debug("video plain url found. Consider embedding as iframe.")
        yield match.group(1)


def get_notes(song_id: SongId, logger: Log) -> str | None:
    """Retrieve notes for a song."""
    logger.debug(f"fetch notes for song {song_id}")
    html = get_usdb_page(
        "index.php",
        RequestMethod.POST,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        params={"link": "gettxt", "id": str(int(song_id))},
        payload={"wd": "1"},
    )
    soup = BeautifulSoup(html, "lxml")
    text = _parse_song_txt_from_txt_page(soup)
    return text


def _parse_song_txt_from_txt_page(soup: BeautifulSoup) -> str | None:
    if textarea := soup.find("textarea"):
        return textarea.string  # type: ignore
    return None
