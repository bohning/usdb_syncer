"""Functionality related to the usdb.animux.de web page."""

import json
import re
from collections.abc import Iterator
from datetime import datetime
from threading import Lock
from typing import Any, Tuple, cast, override

import attrs
from bs4 import BeautifulSoup, NavigableString, Tag
from requests import Response
from requests.exceptions import RequestException

from usdb_syncer import SongId, errors, settings
from usdb_syncer.constants import (
    SUPPORTED_VIDEO_SOURCES_REGEX,
    Usdb,
    UsdbStrings,
    UsdbStringsEnglish,
    UsdbStringsFrench,
    UsdbStringsGerman,
)
from usdb_syncer.logger import Logger, logger, song_logger
from usdb_syncer.net import SyncerSession
from usdb_syncer.usdb_song import UsdbSong
from usdb_syncer.utils import extract_youtube_id, normalize

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


class UsdbSession(SyncerSession[str]):
    """Session class for USDB."""

    def __init__(self, **kwargs: dict) -> None:
        super().__init__(base_url=Usdb.BASE_URL, **kwargs)
        self._username: str = ""

    @override
    def conn_failed(self, error: RequestException) -> str:
        """Handle connection failure."""
        # TODO handle connection failure (dns, timeout, etc.)
        return ""

    @override
    def conn_error(self, response: Response) -> None:
        """Handle connection error."""
        # TODO handle connection error (invalid response, etc.)
        pass

    @override
    def handle_response(self, response: Response) -> str:
        """Handle response."""
        self.set_cookies(response.cookies)
        page = normalize(response.text)
        # TODO handle errors
        return page

    @override
    def close(self) -> None:
        """Close the session."""
        self.username = ""
        super().close()

    @property
    def username(self) -> str:
        """Get the username of the logged-in user."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """Set the username of the logged-in user."""
        self._username = value
        logger.debug(f"Username set to {value or 'None'}.")

    def manual_login(self, username: str, password: str) -> bool:
        """Try to login with the provided credentials."""
        if not username or not password:
            return False
        text = self.post(
            "", data={"user": username, "pass": password, "login": "Login"}
        )
        if UsdbStrings.NOT_LOGGED_IN not in text:
            self.username = username
            return True

        self.username = ""
        return False

    def cookie_login_exists(self) -> bool:
        """Check if a login exists using session cookies.

        Uses the cookies stored in this session.

        Returns:
            True if login was successful, False otherwise.

        """
        username = cast(dict[str, str], json.loads(self.get("whoami.php"))).get(
            "username", ""
        )
        self.username = username
        return bool(username)

    def establish_login(self, auth: Tuple[str, str] | None = None) -> bool:
        """Establish a login. Uses cookies first, then provided credentials.

        Args:
            auth (optional): tuple of username and password.

        Returns:
            True if login was successful, False otherwise.

        """
        if self.cookie_login_exists():
            logger.info(
                f"Using existing browser session for USDB with user '{self.username}'."
            )
            return True
        if not auth:
            logger.debug("Login with browser session failed. Try setting credentials.")
            return False
        if self.manual_login(*auth):
            logger.info(f"Logged in to USDB with user '{self.username}'.")
            return True
        logger.error("Login failed. Please check your credentials.")
        return False

    def logout(self) -> None:
        """Log out from the session.

        Note that, obviously, if cookies are used, this logs out the user from their
        browser as well.
        """
        self.username = ""
        self.post("", params={"link": "logout"})

    def get_song_details(self, song_id: SongId) -> "SongDetails":
        """Get song details for a given song ID."""
        text = self.get("index.php", params={"id": str(int(song_id)), "link": "detail"})
        return parse_song_page(BeautifulSoup(normalize(text), "lxml"), song_id)

    def get_usdb_available_songs(
        self, max_skip_id: SongId, content_filter: dict[str, str] | None = None
    ) -> list[UsdbSong]:
        """Return a list of all available songs.

        Args:
            max_skip_id: only fetch ids larger than this
            content_filter: filters response (e.g. {'artist': 'The Beatles'})

        """
        available_songs: list[UsdbSong] = []
        payload = {
            "order": "id",
            "ud": "desc",
            "limit": str(Usdb.MAX_SONGS_PER_PAGE),
            "details": "1",
        }

        payload.update(content_filter or {})
        for start in range(0, Usdb.MAX_SONG_ID, Usdb.MAX_SONGS_PER_PAGE):
            payload["start"] = str(start)
            html = self.post("index.php", params={"link": "list"}, data=payload)
            songs = [
                song
                for song in parse_songs_from_songlist(html)
                if song.song_id > max_skip_id
            ]
            available_songs.extend(songs)

            if len(songs) < Usdb.MAX_SONGS_PER_PAGE:
                break
        return available_songs

    def get_notes(self, song_id: SongId) -> str:
        """Get notes for a song."""
        html = self.post(
            "index.php",
            params={"link": "gettxt", "id": str(int(song_id))},
            data={"wd": "1"},
        )
        return parse_song_txt_from_txt_page(BeautifulSoup(html, "lxml"))

    def post_song_comment(self, song_id: SongId, text: str, rating: str) -> None:
        """Post a comment to a song."""
        data = {"text": text, "stars": rating}
        self.post(
            "index.php",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            params={"link": "detail", "id": str(int(song_id)), "comment": str(1)},
            data=data,
        )

    def post_song_rating(self, song_id: SongId, stars: int) -> None:
        """Post a rating to a song."""
        data = {"stars": str(stars), "text": "onlyvoting"}
        self.post(
            "index.php",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            params={"link": "detail", "id": str(int(song_id)), "rating": str(1)},
            data=data,
        )


class UsdbSessionManager:
    """Manages the global USDB session."""

    _session: UsdbSession | None = None
    _lock: Lock = Lock()

    @classmethod
    def session(cls) -> UsdbSession:
        """Return a logged-in session.

        If no session exists, create a new one and login.
        If a session exists, return it.

        Returns:
            UsdbSession: The logged-in session.

        """
        with cls._lock:
            if cls._session is None:
                cls._session = UsdbSession()
                cls._session.set_cookies(settings.get_browser())
                cls._session.establish_login(settings.get_usdb_auth())
            return cls._session

    @classmethod
    def reset_session(cls) -> None:
        """Reset the session."""
        with cls._lock:
            if cls._session:
                cls._session.close()
                cls._session = None

    @classmethod
    def has_session(cls) -> bool:
        """Check if a session exists.

        Returns:
            bool: True if a session exists, False otherwise.

        """
        return cls._session is not None


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
    """Details about a song.

    This combines details that USDB shows on a song's page and those specified in the
    comment section.
    """

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
        """Get all parsed URLs and YouTube ids.

        Order is latest to earliest, then ids before URLs.

        Yields:
            str: URLs and YouTube ids from all comments.

        """
        for comment in self.comments:
            yield from comment.contents.youtube_ids
            yield from comment.contents.urls


def username_from_html(html: str) -> str | None:
    """Extract the username from the HTML page.

    Args:
        html: The HTML content of the main USDB page.

    Returns:
        The username if found, otherwise None.

    """
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

    Parameters
    ----------
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
        rating=sum("star.png" in s.get("src") for s in stars),  # type: ignore
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
