"""Functionality related to the usdb.animux.de web page."""

from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from http.cookiejar import CookieJar
from typing import TYPE_CHECKING, Any, assert_never

import attrs
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from requests import Session

from usdb_syncer import SongId, db, errors, events, hooks, settings
from usdb_syncer.constants import (
    SUPPORTED_VIDEO_SOURCES_REGEX,
    Usdb,
    UsdbStrings,
    UsdbStringsEnglish,
    UsdbStringsFrench,
    UsdbStringsGerman,
)
from usdb_syncer.logger import Logger, logger, song_logger
from usdb_syncer.usdb_song import UsdbSong
from usdb_syncer.utils import extract_youtube_id, normalize

if TYPE_CHECKING:
    from collections.abc import Iterator


class UserRole(Enum):
    """A USDB user role."""

    ADMIN = "admin"
    MODERATOR = "mod"
    USER = "user"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class UsdbUser:
    """A USDB user with a name and role."""

    name: str
    role: UserRole

    @classmethod
    def from_rank(cls, name: str, rank: int | None) -> UsdbUser:
        """Create a UsdbUser from a numeric USDB rank code (0-4)."""
        match rank:
            case 4:
                role = UserRole.ADMIN
            case 3:
                role = UserRole.MODERATOR
            case _:
                role = UserRole.USER
        return cls(name=name, role=role)


SONG_LIST_ROW_REGEX = re.compile(
    r'<tr class="list_tr\d"\s+data-songid="(?P<song_id>\d+)"\s+'
    r'data-lastchange="(?P<lastchange>\d+)"[^>]*?>\s*'
    r'<td(?:.*?<source src="(?P<sample_url>.*?)".*?)?></td>'
    r'<td[^>]*?><img src="(?P<cover_url>.*?)".*?></td>'
    r"<td[^>]*?>(?P<artist>.*?)</td>\n"
    r"<td[^>]*?><a href=.*?>(?P<title>.*?)</td>\n"
    r"<td[^>]*?>(?P<genre>.*?)</td>\n"
    r"<td[^>]*?>(?P<year>.*?)</td>\n"
    r"<td[^>]*?>(?P<edition>.*?)</td>\n"
    r"<td[^>]*?>(?P<golden_notes>.*?)</td>\n"
    r"<td[^>]*?>(?P<language>.*?)</td>\n"
    r"<td[^>]*?>(?P<creator>.*?)</td>\n"
    r"<td[^>]*?>(?P<rating>.*?)</td>\n"
    r"<td[^>]*?>(?P<views>.*?)</td>"
)
WELCOME_REGEX = re.compile(
    r"<td class='row3' colspan='2'>\s*<span class='gen'>([^<]+) <b>([^<]+)</b>"
)
RANK_REGEX = re.compile(r"images/rank_(\d)\.gif")


def establish_usdb_login(session: Session) -> UsdbUser | None:
    """Try to log in to USDB if necessary. Returns user info or None."""
    user = get_logged_in_usdb_user(session)

    if user:
        logger.info(f"Using existing USDB login of {user.role} '{user.name}'.")
    else:
        auth_user, auth_pass = settings.get_usdb_auth()
        if auth_user and auth_pass:
            if login_to_usdb(session, auth_user, auth_pass):
                user = get_logged_in_usdb_user(session)
                if user:
                    logger.info(
                        "Successfully logged in to USDB with "
                        f"{user.role} '{user.name}'."
                    )
                else:
                    logger.error(
                        "Login appeared successful, but user info could not be "
                        "retrieved."
                    )
            else:
                logger.error(f"Login to USDB with user '{auth_user}' failed!")
        else:
            logger.warning(
                "Not logged in to USDB. Please go to 'Synchronize > USDB Login', then "
                "select the browser you are logged in with and/or enter your "
                "credentials."
            )

    if user:
        events.LoggedInToUSDB(user=user.name).post()

    return user


def new_session_with_cookies(browser: settings.Browser) -> Session:
    session = Session()
    if cookies := browser.cookies():
        for cookie in cookies:
            session.cookies.set_cookie(cookie)
    addon_jar = CookieJar()
    hooks.GetUsdbCookies.call(addon_jar)
    for cookie in addon_jar:
        session.cookies.set_cookie(cookie)
    return session


class SessionManager:
    """Singleton for managing the global session instance."""

    _session: Session | None = None
    _connecting: bool = False
    _user: UsdbUser | None = None

    @classmethod
    def session(cls) -> Session:
        while cls._connecting:
            time.sleep(0.1)
        if cls._session is None:
            cls._connecting = True
            try:
                cls._session = new_session_with_cookies(settings.get_browser())
                cls._user = establish_usdb_login(cls._session)
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

    @classmethod
    def get_user(cls) -> UsdbUser | None:
        return cls._user


def get_logged_in_usdb_user(session: Session) -> UsdbUser | None:
    """Return the logged-in USDB user's name and role, or None if not logged in."""
    response = session.get(Usdb.BASE_URL, timeout=10, params={"link": "profil"})
    response.raise_for_status()

    html = response.text

    if not (welcome_match := WELCOME_REGEX.search(html)):
        return None
    username = welcome_match.group(2)

    rank_match = RANK_REGEX.search(html)
    rank = int(rank_match.group(1)) if rank_match else None

    return UsdbUser.from_rank(username, rank)


def login_to_usdb(session: Session, user: str, password: str) -> bool:
    """Return True if login was successful."""
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

    Includes details that USDB shows on a song's page or are specified in the
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
        """Yield all parsed URLs and YouTube ids.

        Order is latest to earliest, then ids before URLs.
        """
        for comment in self.comments:
            yield from comment.contents.youtube_ids
            yield from comment.contents.urls


def get_usdb_page(
    rel_url: str,
    method: RequestMethod = RequestMethod.GET,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
    session: Session | None = None,
) -> str:
    """Retrieve HTML subpage from USDB."""
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
        logger.debug("Connection failed; session may have expired; retrying ...")
    except errors.UsdbLoginError:
        # skip login retry if custom or just created session
        if session or not existing_session:
            raise
        logger.debug(f"Page '{rel_url}' is private; trying to log in ...")
    if not session:
        SessionManager.reset_session()
    return page()


def _get_usdb_page_inner(
    session: Session,
    rel_url: str,
    method: RequestMethod = RequestMethod.GET,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> str:
    session = session or SessionManager.session()
    url = Usdb.BASE_URL + rel_url
    match method:
        case RequestMethod.GET:
            logger.debug(f"Get request for {url}")
            response = session.get(url, headers=headers, params=params, timeout=10)
        case RequestMethod.POST:
            logger.debug(f"Post request for {url}")
            response = session.post(
                url, headers=headers, data=payload, params=params, timeout=10
            )
        case _ as unreachable:
            assert_never(unreachable)
    response.raise_for_status()
    response.encoding = "utf-8"
    if UsdbStrings.NOT_LOGGED_IN in (page := normalize(html.unescape(response.text))):
        raise errors.UsdbLoginError
    if UsdbStrings.DATASET_NOT_FOUND in page:
        raise errors.UsdbNotFoundError
    return page


def get_usdb_details(song_id: SongId) -> SongDetails:
    """Retrieve song details from usdb webpage, if song exists."""
    html = get_usdb_page(
        "index.php", params={"id": str(int(song_id)), "link": "detail"}
    )
    return _parse_song_page(BeautifulSoup(html, "lxml"), song_id)


def _parse_song_page(soup: BeautifulSoup, song_id: SongId) -> SongDetails:
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


def get_updated_songs_from_usdb(
    last_update: db.LastUsdbUpdate,
    content_filter: dict[str, str] | None = None,
    session: Session | None = None,
) -> list[UsdbSong]:
    """Return a list of all songs that were updated (or added) since `last_update`."""
    available_songs: dict[SongId, UsdbSong] = {}
    payload = {
        "order": "lastchange",
        "ud": "desc",
        "limit": str(Usdb.MAX_SONGS_PER_PAGE),
        "details": "1",
    }
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
        songs = {
            song.song_id: song
            for song in _parse_songs_from_songlist(html)
            if song.is_new_since_last_update(last_update)
        }
        available_songs.update(songs)

        if len(songs) < Usdb.MAX_SONGS_PER_PAGE:
            break

    logger.info(f"Fetched {len(available_songs)} updated song(s) from USDB.")
    return list(available_songs.values())


def _parse_songs_from_songlist(html: str) -> Iterator[UsdbSong]:
    return (
        UsdbSong.from_html(
            _usdb_strings_from_html(html),
            song_id=match["song_id"],
            usdb_mtime=match["lastchange"],
            sample_url=match["sample_url"] or "",
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
    """Parse song attributes from usdb page."""
    editors = []
    pointer = details_table.find(string=usdb_strings.SONG_EDITED_BY)
    while pointer is not None:
        pointer = pointer.find_next("td")  # type: ignore
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
        rating=sum("star.png" in (s.get("src") or "") for s in stars),
        votes=int(votes_str.split("(")[1].split(")")[0]),
        audio_sample=audio_sample or None,
    )


def _find_text_after(details_table: Tag, label: str) -> str:
    if isinstance(
        (tag := details_table.find(string=label)), NavigableString
    ) and isinstance(tag.next, Tag):
        return tag.next.text.strip()
    raise errors.UsdbParseError(f"Text after {label} not found.")  # noqa: TRY003


def _parse_comments_table(comments_table: Tag, logger: Logger) -> list[SongComment]:
    """Parse the table into individual comments.

    Extracts potential video links, GAP and BPM values.
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
    for script in contents.find_all("script"):
        if (
            isinstance(script, Tag)
            and isinstance(script_src := script.get("src"), str)
            and ("dailymotion" in script_src)
            and isinstance(dailymotion_id := script.get("data-video"), str)
        ):
            yield f"https://www.dailymotion.com/video/{dailymotion_id}"
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


def get_notes(song_id: SongId, logger: Logger) -> str:
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
    raise errors.UsdbParseError("textarea for notes not found")  # noqa: TRY003


def post_song_comment(song_id: SongId, text: str, rating: str) -> None:
    """Post a song comment to USDB."""
    payload = {"text": text, "stars": rating}

    get_usdb_page(
        "index.php",
        RequestMethod.POST,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        params={"link": "detail", "id": str(int(song_id)), "comment": str(1)},
        payload=payload,
    )
    logger = song_logger(song_id)
    logger.debug("Comment posted on USDB.")


def post_song_rating(song_id: SongId, stars: int) -> None:
    """Post a song rating to USDB."""
    payload = {"stars": str(stars), "text": "onlyvoting"}

    get_usdb_page(
        "index.php",
        RequestMethod.POST,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        params={"link": "detail", "id": str(int(song_id)), "comment": str(1)},
        payload=payload,
    )
    logger = song_logger(song_id)
    logger.debug(f"{stars}-star rating posted on USDB.")


def submit_local_changes(
    song_id: SongId, sample_url: str, txt: str, filename: str, logger: Logger
) -> None:
    """Submit local changes of a song to USDB."""
    payload = {
        "coverinput": "",
        "sampleinput": sample_url,
        "txt": txt,
        "filename": filename,
    }

    get_usdb_page(
        "index.php",
        RequestMethod.POST,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        params={"link": "editsongsupdate", "id": str(song_id)},
        payload=payload,
    )

    logger.info("Local changes successfully submitted to USDB.")
