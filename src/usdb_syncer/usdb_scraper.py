"""Functionality related to the usdb.animux.de web page."""

import logging
import re
import time
from datetime import datetime
from enum import Enum
from typing import Iterator, Type, assert_never

import attrs
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from requests import Session

from usdb_syncer import SongId, errors, settings
from usdb_syncer.constants import (
    SUPPORTED_VIDEO_SOURCES_REGEX,
    Usdb,
    UsdbStrings,
    UsdbStringsEnglish,
    UsdbStringsFrench,
    UsdbStringsGerman,
)
from usdb_syncer.logger import Log, get_logger
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
    r"<td class='row3' colspan='2'>\s*<span class='gen'>([^<]+) <b>([^<]+)</b>"
)
TAGS_LINE_REGEX = re.compile("#TAGS:(.+)")


def establish_usdb_login(session: Session) -> bool:
    """Tries to log in to USDB if necessary. Returns final login status."""
    if user := get_logged_in_usdb_user(session):
        _logger.info(f"Using existing login of USDB user '{user}'.")
        return True
    if (auth := settings.get_usdb_auth())[0] and auth[1]:
        if login_to_usdb(session, *auth):
            _logger.info(f"Successfully logged in to USDB with user '{auth[0]}'.")
            return True
        _logger.error(f"Login to USDB with user '{auth[0]}' failed!")
    else:
        _logger.warning(
            "Not logged in to USDB. Please go to 'Synchronize > USDB Login', then "
            "select the browser you are logged in with and/or enter your credentials."
        )
    return False


def new_session_with_cookies(browser: settings.Browser) -> Session:
    session = Session()
    if cookies := browser.cookies():
        for cookie in cookies:
            session.cookies.set_cookie(cookie)
    return session


class SessionManager:
    """Singleton for managing the global session instance."""

    _session: Session | None = None
    _connecting: bool = False

    @classmethod
    def session(cls) -> Session:
        while cls._connecting:
            time.sleep(0.1)
        if cls._session is None:
            cls._connecting = True
            try:
                cls._session = new_session_with_cookies(settings.get_browser())
                establish_usdb_login(cls._session)
            finally:
                cls._connecting = False
        return cls._session

    @classmethod
    def reset_session(cls) -> None:
        if cls._session:
            cls._session.close()
            cls._session = None

    @classmethod
    def has_session(cls) -> bool:
        return cls._session is not None


def get_logged_in_usdb_user(session: Session) -> str | None:
    response = session.get(Usdb.BASE_URL, timeout=10, params={"link": "profil"})
    response.raise_for_status()
    if match := WELCOME_REGEX.search(response.text):
        return match.group(2)
    return None


def login_to_usdb(session: Session, user: str, password: str) -> bool:
    """True if success."""
    response = session.post(
        Usdb.BASE_URL,
        timeout=10,
        data={"user": user, "pass": password, "login": "Login"},
    )
    response.raise_for_status()
    return UsdbStrings.LOGIN_INVALID not in response.text


def log_out_of_usdb(session: Session) -> None:
    session.post(Usdb.BASE_URL, timeout=10, params={"link": "logout"})


class RequestMethod(Enum):
    """Supported HTTP requests."""

    GET = "GET"
    POST = "POST"


@attrs.define(kw_only=True)
class CommentContents:
    """The parsed contents of a SongComment."""

    text: str
    youtube_ids: list[str]
    urls: list[str]
    tags: list[str]


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

    def comment_tags(self) -> list[str]:
        """Return the first tags string sanitized, if any."""
        for comment in self.comments:
            if comment.contents.tags:
                return comment.contents.tags
        return []


def get_usdb_page(
    rel_url: str,
    method: RequestMethod = RequestMethod.GET,
    headers: dict[str, str] | None = None,
    payload: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
    session: Session | None = None,
) -> str:
    """Retrieve HTML subpage from USDB.

    Parameters:
        rel_url: relative url of page to retrieve
        method: GET or POST
        headers: dict of headers to send with request
        payload: dict of data to send with request
        params: dict of params to send with request
        session: Session to use instead of the global one
    """
    existing_session = SessionManager.has_session()

    def page() -> str:
        return _get_usdb_page_inner(
            session or SessionManager.session(),
            rel_url,
            method=method,
            headers=headers,
            payload=payload,
            params=params,
        )

    try:
        return page()
    except requests.ConnectionError:
        _logger.debug("Connection failed; session may have expired; retrying ...")
    except errors.UsdbLoginError:
        # skip login retry if custom or just created session
        if session or not existing_session:
            raise
        _logger.debug(f"Page '{rel_url}' is private; trying to log in ...")
    if not session:
        SessionManager.reset_session()
    return page()


def _get_usdb_page_inner(
    session: Session,
    rel_url: str,
    method: RequestMethod = RequestMethod.GET,
    headers: dict[str, str] | None = None,
    payload: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> str:
    session = session or SessionManager.session()
    url = Usdb.BASE_URL + rel_url
    match method:
        case RequestMethod.GET:
            _logger.debug(f"Get request for {url}")
            response = session.get(url, headers=headers, params=params, timeout=10)
        case RequestMethod.POST:
            _logger.debug(f"Post request for {url}")
            response = session.post(
                url, headers=headers, data=payload, params=params, timeout=10
            )
        case _ as unreachable:
            assert_never(unreachable)
    response.raise_for_status()
    response.encoding = "utf-8"
    if UsdbStrings.NOT_LOGGED_IN in (page := normalize(response.text)):
        raise errors.UsdbLoginError
    if UsdbStrings.DATASET_NOT_FOUND in page:
        raise errors.UsdbNotFoundError
    return page


def get_usdb_details(song_id: SongId) -> SongDetails:
    """Retrieve song details from usdb webpage, if song exists.

    Parameters:
        song_id: id of song to retrieve details for
    """
    html = get_usdb_page(
        "index.php", params={"id": str(int(song_id)), "link": "detail"}
    )
    return _parse_song_page(BeautifulSoup(html, "lxml"), song_id)


def _parse_song_page(soup: BeautifulSoup, song_id: SongId) -> SongDetails:
    logger = get_logger(__file__, song_id)
    usdb_strings = _usdb_strings_from_soup(soup)
    details_table, comments_table, *_ = soup.find_all("table", border="0", width="500")
    details = _parse_details_table(details_table, song_id, usdb_strings, logger)
    details.comments = _parse_comments_table(comments_table, logger)
    return details


def _usdb_strings_from_soup(soup: BeautifulSoup) -> Type[UsdbStrings]:
    return _usdb_strings_from_welcome(
        soup.find("span", class_="gen").text.split(" ", 1)[0].removesuffix(",")
    )


def _usdb_strings_from_html(html: str) -> Type[UsdbStrings]:
    if match := WELCOME_REGEX.search(html):
        return _usdb_strings_from_welcome(match.group(1))
    raise errors.UsdbParseError("welcome string not found")


def _usdb_strings_from_welcome(welcome_string: str) -> Type[UsdbStrings]:
    match welcome_string:
        case UsdbStringsEnglish.WELCOME:
            return UsdbStringsEnglish
        case UsdbStringsGerman.WELCOME:
            return UsdbStringsGerman
        case UsdbStringsFrench.WELCOME:
            return UsdbStringsFrench
    raise errors.UsdbParseError("Unknown USDB language.")


def get_usdb_available_songs(
    max_skip_id: SongId,
    content_filter: dict[str, str] | None = None,
    session: Session | None = None,
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
            "index.php",
            RequestMethod.POST,
            params={"link": "list"},
            payload=payload,
            session=session,
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
    details_table: BeautifulSoup,
    song_id: SongId,
    usdb_strings: Type[UsdbStrings],
    logger: Log,
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
        logger.debug("No audio sample found. Consider adding one!")

    cover_url = details_table.img["src"]  # type: ignore
    if "nocover" in cover_url:
        logger.debug("No USDB cover. Consider adding one!")

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
        uploader=_find_text_after(details_table, usdb_strings.UPLOADED_BY),
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
    raise errors.UsdbParseError(f"Text after {label} not found.")


def _parse_comments_table(
    comments_table: BeautifulSoup, logger: Log
) -> list[SongComment]:
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
        contents = _parse_comment_contents(header.next_sibling, logger)
        comments.append(
            SongComment(date_time=date_time, author=author, contents=contents)
        )

    return comments


def _parse_comment_contents(contents: BeautifulSoup, logger: Log) -> CommentContents:
    td_element = contents.find("td")
    for emoji in td_element.find_all("img"):
        emoji.replaceWith(emoji.get("title"))

    text = td_element.text.strip()  # type: ignore
    urls: list[str] = []
    youtube_ids: list[str] = []

    for url in _all_urls_in_comment(contents, text, logger):
        if yt_id := extract_youtube_id(url):
            youtube_ids.append(yt_id)
        else:
            urls.append(url)

    if match := TAGS_LINE_REGEX.search(text):
        tags = [t for tag in match.group(1).split(",") if (t := tag.strip())]
    else:
        tags = []

    return CommentContents(text=text, urls=urls, youtube_ids=youtube_ids, tags=tags)


def _all_urls_in_comment(
    contents: BeautifulSoup, text: str, logger: Log
) -> Iterator[str]:
    for embed in contents.find_all("embed"):
        if (src := embed.get("src")) and SUPPORTED_VIDEO_SOURCES_REGEX.fullmatch(src):
            logger.debug("video embed found. Consider embedding as iframe")
            yield src
    for iframe in contents.find_all("iframe"):
        if (src := iframe.get("src")) and SUPPORTED_VIDEO_SOURCES_REGEX.fullmatch(src):
            yield src
    for anchor in contents.find_all("a"):
        if (url := anchor.get("href")) and SUPPORTED_VIDEO_SOURCES_REGEX.fullmatch(url):
            logger.debug("video href found. Consider embedding as iframe")
            yield url
    for match in SUPPORTED_VIDEO_SOURCES_REGEX.finditer(text):
        logger.debug("video plain url found. Consider embedding as iframe.")
        yield match.group(1)


def get_notes(song_id: SongId, logger: Log) -> str:
    """Retrieve notes for a song."""
    logger.debug("fetching notes")
    html = get_usdb_page(
        "index.php",
        RequestMethod.POST,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        params={"link": "gettxt", "id": str(int(song_id))},
        payload={"wd": "1"},
    )
    return _parse_song_txt_from_txt_page(BeautifulSoup(html, "lxml"))


def _parse_song_txt_from_txt_page(soup: BeautifulSoup) -> str:
    if isinstance(textarea := soup.find("textarea"), Tag):
        return textarea.string or ""
    raise errors.UsdbParseError("textarea for notes not found")
