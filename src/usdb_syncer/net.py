"""Networking functionality for the syncer.

Every networking operation should go
through this module to ensure common headers, consistent error handling, and retry
logic.
"""

import abc
import time
import urllib.parse
from threading import Lock
from typing import TYPE_CHECKING, Generic, TypeVar, override

from requests import Response, Session
from requests.cookies import RequestsCookieJar
from requests.exceptions import RequestException

from usdb_syncer.logger import logger

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
    """Abstract base session class."""

    BASE_URL: str
    session: Session

    @abc.abstractmethod
    def __init__(self, base_url: str, **kwargs: dict) -> None:
        """Initialize the session."""
        self.BASE_URL = base_url
        self.session = Session(**kwargs)
        self._lock = Lock()
        self.session.verify = True
        self.set_headers(GLOBAL_HEADERS)

    @abc.abstractmethod
    def conn_failed(self, url: str, error: RequestException) -> T:
        """Handle connection failures."""
        raise NotImplementedError

    @abc.abstractmethod
    def handle_response(self, response: Response) -> T:
        """Handle the response."""
        raise NotImplementedError

    def clear_cookies(self) -> None:
        """Clear all cookies for the session."""
        with self._lock:
            self.session.cookies.clear()

    def set_cookies(self, cookiejar: "settings.Browser | RequestsCookieJar") -> None:
        """Add cookies to the session..

        Args:
            browser: The browser to get cookies from.

        """
        # The unintuitive `not isinstance` allows us to not import settings
        if not isinstance(cookiejar, RequestsCookieJar):
            cookies = cookiejar.cookies()
        else:
            cookies = cookiejar
        with self._lock:
            for cookie in cookies or []:
                self.session.cookies.set_cookie(cookie)

    def set_headers(self, headers: dict) -> None:
        """Add new headers to the existing ones for the session.

        Args:
            headers: The headers to add

        """
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
        """Make a request with retry capability.

        Calls handle_response to process the response.
        Calls conn_failed with the last exception if all retries are exhausted.

        Args:
            method: The HTTP method to use.
            rel_url: The relative URL to request. Merged with the base URL using
                `urllib.parse.urljoin`.
            data: The data to send with the request.
            json: The JSON data to send with the request.
            headers: The headers to send with the request.
            params: The parameters to send with the request.

        Returns:
            An object defined by subclasses in handle_response.

        """
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

                response.encoding = "utf-8"

                return self.handle_response(response)

            except RequestException as e:
                if retry_count < REQUEST_MAX_RETRIES:
                    retry_count += 1
                    logger.debug(
                        (
                            f"{e!s} while accessing {complete_url}. Retry "
                            f"({retry_count}/{REQUEST_MAX_RETRIES}) in "
                            f"{current_delay:.1f}s"
                        )
                    )
                    time.sleep(current_delay)
                    current_delay *= REQUEST_RETRY_BACKOFF
                    continue
                return self.conn_failed(complete_url, e)

    def get(
        self, rel_url: str, params: dict | None = None, headers: dict | None = None
    ) -> T:
        """Make a GET request.

        Args:
            rel_url: The relative URL to request. Merged with the base URL using
                `urllib.parse.urljoin`.
            params: The parameters to send with the request.
            headers: The headers to send with the request.

        Returns:
            An object defined by subclasses in handle_response.

        """
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
        """Make a POST request.

        Args:
            rel_url: The relative URL to request. Merged with the base URL using
                `urllib.parse.urljoin`.
            data: The data to send with the request.
            json: The JSON data to send with the request.
            params: The parameters to send with the request.
            headers: The headers to send with the request.

        Returns:
            An object defined by subclasses in handle_response.

        """
        return self._request(
            "POST", rel_url, data=data, json=json, headers=headers, params=params
        )

    def close(self) -> None:
        """Close the session."""
        self.session.close()


class _GenericSession(SyncerSession[Response | None]):
    """Generic session class for other sites.

    This class is used for sites that do not require any special handling of
    requests or responses.
    """

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url=base_url)

    @override
    def get(
        self, rel_url: str, params: dict | None = None, headers: dict | None = None
    ) -> Response | None:
        """Make a GET request.

        Args:
            rel_url: The relative URL to request. Merged with the base URL using
                `urllib.parse.urljoin`.
            params: The parameters to send with the request.
            headers: The headers to send with the request.

        Returns:
            Response: The response, guaranteed to be ok.

        """
        return super().get(rel_url, params=params, headers=headers)

    @override
    def post(
        self,
        rel_url: str,
        data: dict | None = None,
        json: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> Response | None:
        """Make a POST request.

        Args:
            rel_url: The relative URL to request. Merged with the base URL using
                `urllib.parse.urljoin`.
            data: The data to send with the request.
            json: The JSON data to send with the request.
            params: The parameters to send with the request.
            headers: The headers to send with the request.
        return super().post(rel_url, data, json, params, headers)

        Returns:
            Response: The response, guaranteed to be ok.

        """
        return super().post(
            rel_url, data=data, json=json, params=params, headers=headers
        )

    @override
    def handle_response(self, response: Response) -> Response | None:
        """Handle the response.

        Args:
            response: The response to handle.

        Returns:
            Response: The response, guaranteed to be ok.

        """
        if response.ok:
            return response
        logger.debug(
            f"Request failed with status code {response.status_code} for {response.url}"
        )
        return None

    @override
    def conn_failed(self, url: str, error: RequestException) -> None:
        """Handle connection failure.

        Returns:
            Response: An empty response.

        """
        logger.debug(f"Connection failed for {url}: {error!s}.")
        return None


def get_generic_session(base_url: str = "") -> _GenericSession:
    """Get a generic session for the given base URL.

    Args:
        base_url(optional): The base URL for the session. Defaults to an empty string.

    Returns:
        _GenericSession: The generic session.

    """
    return _GenericSession(base_url)
