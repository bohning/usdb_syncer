import abc
import time
import urllib.parse
from threading import Lock
from typing import TYPE_CHECKING, Generic, TypeVar, override

from requests import Response, Session
from requests.exceptions import RequestException

if TYPE_CHECKING:
    from usdb_syncer import settings

GLOBAL_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT = 10
REQUEST_MAX_RETRIES = 3
REQUEST_RETRY_DELAY = 1.0
REQUEST_RETRY_BACKOFF = 3.0

# Typevar to control return type of get and post methods
T = TypeVar("T")


class SyncerSession(Generic[T], abc.ABC):
    """Base session class."""

    BASE_URL: str
    session: Session

    @abc.abstractmethod
    def __init__(self, base_url: str, **kwargs: dict) -> None:
        self.BASE_URL = base_url
        self.session = Session(**kwargs)
        self._lock = Lock()
        self.session.verify = True
        self.set_headers(GLOBAL_HEADERS)

    @abc.abstractmethod
    def conn_failed(self, error: RequestException) -> T:
        """The connection failed with an exception. Handle it."""
        raise NotImplementedError

    @abc.abstractmethod
    def conn_error(self, response: Response) -> None:
        """The response has an invalid status code. Handle it."""
        raise NotImplementedError

    @abc.abstractmethod
    def handle_response(self, response: Response) -> T:
        """Handle the response."""
        raise NotImplementedError

    def set_cookies(self, browser: "settings.Browser") -> None:
        """Set cookies for the session. Clears existing cookies."""
        with self._lock:
            self.session.cookies.clear()
            if jar := browser.cookies():
                for cookie in jar:
                    self.session.cookies.set_cookie(cookie)

    def set_headers(self, headers: dict) -> None:
        """Set headers for the session. Does not clear existing headers."""
        with self._lock:
            self.session.headers.update(headers)

    def _request(
        self,
        method: str,
        rel_url: str,
        data: dict | None,
        json: dict | None,
        headers: dict | None,
        params: dict | None,
    ) -> T:
        """Make a request with retry capability. Calls conn_failed with the last
        exception when all retries are exhausted."""
        complete_url = urllib.parse.urljoin(self.BASE_URL, rel_url)

        retry_count = 0
        current_delay = REQUEST_RETRY_DELAY

        while True:
            try:
                response = self.session.request(
                    method=method,
                    url=complete_url,
                    data=data,
                    json=json,
                    headers=headers,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )

                if response.ok:
                    response.encoding = "utf-8"
                    return self.handle_response(response)

                # Response not ok
                self.conn_error(response)
                response.encoding = "utf-8"
                return self.handle_response(response)

            except RequestException as e:
                if retry_count < REQUEST_MAX_RETRIES:
                    time.sleep(current_delay)
                    current_delay *= REQUEST_RETRY_BACKOFF
                    retry_count += 1
                    continue
                return self.conn_failed(e)

    def get(
        self, rel_url: str, params: dict | None = None, headers: dict | None = None
    ) -> T:
        """Make a GET request."""
        return self._request(
            "GET", rel_url, headers=headers, params=params, data=None, json=None
        )

    def post(
        self,
        rel_url: str,
        data: dict | None = None,
        json: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> T:
        """Make a POST request."""
        return self._request(
            "POST", rel_url, data=data, json=json, headers=headers, params=params
        )

    def close(self) -> None:
        """Close the session."""
        self.session.close()


class _GenericSession(SyncerSession[Response]):
    """Generic session class for other sites."""

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url=base_url)

    @override
    def handle_response(self, response: Response) -> Response:
        return response

    @override
    def conn_failed(self, error: RequestException) -> Response:
        """Handle connection failure."""
        # TODO handle connection failure (dns, timeout, etc.)
        return Response()

    @override
    def conn_error(self, response: Response) -> None:
        """Handle connection failure."""
        # TODO handle connection error (invalid response, etc.)
        pass


def get_generic_session(base_url: str = "") -> _GenericSession:
    return _GenericSession(base_url)
