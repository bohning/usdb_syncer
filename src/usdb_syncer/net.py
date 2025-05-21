import abc
import time
import urllib
import urllib.parse
from typing import Tuple, override

from bs4 import BeautifulSoup
from requests import Response, Session

from usdb_syncer import SongId, constants, settings, usdb_scraper, usdb_song, utils

GLOBAL_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
}


class SyncerSession(abc.ABC):
    """Base session class."""

    BASE_URL: str
    session: Session
    timeout: int

    @abc.abstractmethod
    def __init__(self, base_url: str, **kwargs: dict) -> None:
        self.BASE_URL = base_url
        self.session = Session(**kwargs)
        self.session.verify = True
        self.set_headers(GLOBAL_HEADERS)
        self.timeout = 10

    @abc.abstractmethod
    def conn_failed(self, response: Response) -> None:
        raise NotImplementedError

    def handle_response(self, response: Response) -> str:
        return response.text

    def set_cookies(self, browser: settings.Browser) -> None:
        """Set cookies for the session. Clears existing cookies."""
        self.session.cookies.clear()
        if jar := browser.cookies():
            for cookie in jar:
                self.session.cookies.set_cookie(cookie)

    def set_headers(self, headers: dict) -> None:
        """Set headers for the session. Does not clear existing headers."""
        self.session.headers.update(headers)

    def _request(
        self,
        method: str,
        rel_url: str,
        data: dict,
        headers: dict,
        params: dict,
    ) -> str:
        """Make a request. Calls conn_failed on error."""
        complete_url = urllib.parse.urljoin(self.BASE_URL, rel_url)
        response = self.session.request(
            method=method,
            url=complete_url,
            data=data,
            headers=headers,
            params=params,
            timeout=self.timeout,
        )
        if not response.ok:
            self.conn_failed(response)
        response.encoding = "utf-8"
        return self.handle_response(response)

    def get(self, rel_url: str, params: dict, headers: dict) -> str:
        """Make a GET request."""
        return self._request("GET", rel_url, headers=headers, params=params, data={})

    def post(self, rel_url: str, data: dict, params: dict, headers: dict) -> str:
        """Make a POST request."""
        return self._request("POST", rel_url, data=data, headers=headers, params=params)

    def close(self) -> None:
        """Close the session."""
        self.session.close()


class UsdbSession(SyncerSession):
    """Session class for USDB."""

    logged_in: bool = False
    username: str | None = None

    @override
    def __init__(self, **kwargs: dict) -> None:
        super().__init__(base_url=constants.Usdb.BASE_URL, **kwargs)

    @override
    def conn_failed(self, response: Response) -> None:
        """Handle connection failure."""
        self.logged_in = False

    @override
    def handle_response(self, response: Response) -> str:
        """Handle response."""
        page = utils.normalize(response.text)
        # TODO handle errors
        return page

    @override
    def close(self) -> None:
        super().close()
        self.logged_in = False
        self.username = None

    def establish_login(self, *auth: Tuple[str, str]) -> bool:
        text = self.get("", params={"link": "profil"}, headers={})
        if username := usdb_scraper.username_from_html(text):
            self.username = username
            self.logged_in = True
            return True

        if not auth:
            username, password = settings.get_usdb_auth()
        else:
            username, password = auth[0]
        if not username or not password:
            return False
        text = self.post(
            "",
            data={"user": username, "pass": password, "login": "Login"},
            params={},
            headers={},
        )
        if constants.UsdbStrings.LOGIN_INVALID not in text:
            self.username = username
            self.logged_in = True
            return True
        self.username = None
        self.logged_in = False
        return False

    def logout(self) -> None:
        self.post("", params={"link": "logout"}, data={}, headers={})
        self.logged_in = False
        self.username = None

    def get_song_details(self, song_id: SongId) -> usdb_scraper.SongDetails:
        text = self.get(
            "index.php", params={"id": str(int(song_id)), "link": "detail"}, headers={}
        )
        return usdb_scraper.parse_song_page(
            BeautifulSoup(utils.normalize(text), "lxml"), song_id
        )

    def get_usdb_available_songs(
        self, max_skip_id: SongId, content_filter: dict[str, str] | None = None
    ) -> list[usdb_song.UsdbSong]:
        """Return a list of all available songs.

        Parameters:
            max_skip_id: only fetch ids larger than this
            content_filter: filters response (e.g. {'artist': 'The Beatles'})
        """
        available_songs: list[usdb_song.UsdbSong] = []
        payload = {
            "order": "id",
            "ud": "desc",
            "limit": str(constants.Usdb.MAX_SONGS_PER_PAGE),
            "details": "1",
        }

        payload.update(content_filter or {})
        for start in range(
            0, constants.Usdb.MAX_SONG_ID, constants.Usdb.MAX_SONGS_PER_PAGE
        ):
            payload["start"] = str(start)
            html = self.post(
                "index.php", params={"link": "list"}, data=payload, headers={}
            )
            songs = [
                song
                for song in usdb_scraper.parse_songs_from_songlist(html)
                if song.song_id > max_skip_id
            ]
            available_songs.extend(songs)

            if len(songs) < constants.Usdb.MAX_SONGS_PER_PAGE:
                break
        return available_songs

    def get_notes(self, song_id: SongId) -> str:
        """Get notes for a song."""
        html = self.post(
            "index.php",
            params={"link": "gettxt", "id": str(int(song_id))},
            data={"wd": "1"},
            headers={},
        )
        return usdb_scraper.parse_song_txt_from_txt_page(BeautifulSoup(html, "lxml"))

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
    _session: UsdbSession | None = None
    _connecting: bool = False

    @classmethod
    def session(cls) -> UsdbSession:
        while cls._connecting:
            time.sleep(0.1)
        if cls._session is None:
            cls._connecting = True
            try:
                cls._session = UsdbSession()
                cls._session.set_cookies(settings.get_browser())
                cls._session.establish_login()
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


class GenericSession(SyncerSession):
    """Generic session class for other sites."""

    @override
    def __init__(self, base_url: str) -> None:
        super().__init__(base_url=base_url)

    @override
    def conn_failed(self, response: Response) -> None:
        """Handle connection failure."""
        return None


def get_generic_session(base_url: str) -> SyncerSession:
    return GenericSession(base_url)
