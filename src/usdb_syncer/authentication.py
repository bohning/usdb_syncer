"""This module provides functions to store and retrieve credentials and cookies."""

import pickle
from enum import Enum
from http.cookiejar import CookieJar
from typing import Tuple, cast

import keyring
from cryptography.fernet import Fernet

from usdb_syncer import settings, utils
from usdb_syncer.logger import logger

SYSTEM_USDB = "USDB Syncer/USDB"
SYSTEM_COOKIE_KEY = "USDB Syncer/Cookies"
NO_KEYRING_BACKEND_WARNING = (
    "Your USDB password cannot be stored or retrieved because no keyring backend is "
    "available. You might need to activate it. See https://pypi.org/project/keyring "
    "for details."
)


class CookieSource(Enum):
    """Where to get the cookies from."""

    MANUAL = "manual"
    BROWSER = "browser"


def _set_auth(service_name: str, username: str, password: str) -> bool:
    try:
        keyring.set_password(service_name, username, password)
        return True
    except keyring.core.backend.errors.NoKeyringError as error:
        logger.debug(error)
        logger.warning(NO_KEYRING_BACKEND_WARNING)
    return False


def _get_auth(service_name: str, username: str) -> str:
    try:
        password = keyring.get_password(service_name, username) or ""
    except keyring.core.backend.errors.NoKeyringError as error:
        logger.debug(error)
        logger.warning(NO_KEYRING_BACKEND_WARNING)
        password = ""
    return password


def get_usdb_auth() -> Tuple[str, str]:
    username = settings.get_setting(settings.SettingKey.USDB_USER_NAME, "")
    return (username, _get_auth(SYSTEM_USDB, username))


def set_usdb_auth(username: str, password: str) -> None:
    settings.set_setting(settings.SettingKey.USDB_USER_NAME, username)
    _set_auth(SYSTEM_USDB, username, password)


def _get_manual_cookies() -> CookieJar:
    """Return the cookies from the saved cookie file. If unavailable, return an empty cookiejar."""
    username = settings.get_setting(settings.SettingKey.USDB_USER_NAME, "")
    key = _get_auth(SYSTEM_COOKIE_KEY, username)
    cookies = CookieJar()
    if not key:
        return cookies
    try:
        fernet = Fernet(key.encode("utf-8"))
        with open(utils.AppPaths.cookie_file, "rb") as file:
            encrypted_cookies = file.read()
        pickled_cookies = fernet.decrypt(encrypted_cookies)
    except FileNotFoundError:
        logger.warning("Saved cookies not found. Try to set new ones.")
        return cookies

    for cookie in pickle.loads(pickled_cookies):
        cookies.set_cookie(cookie)
    return cookies


def store_manual_cookies(cookies: CookieJar) -> bool:
    """Store the cookiejar in the system keyring."""

    # Because of keyring length limitations on some platforms (Windows), we can't
    # store the cookiejar directly. Instead, we encrypt it with a symmetric key and store the
    # symmetric key in the keyring.
    # The encrypted file is stored in the user data directory.
    key = Fernet.generate_key()
    fernet = Fernet(key)
    username = settings.get_setting(settings.SettingKey.USDB_USER_NAME, "")

    cookie_list = list(cookie for cookie in cookies)

    try:
        pickled_cookies = pickle.dumps(cookie_list)
        encrypted_cookies = fernet.encrypt(pickled_cookies)

        with open(utils.AppPaths.cookie_file, "wb") as file:
            file.write(encrypted_cookies)

        success = _set_auth(SYSTEM_COOKIE_KEY, username, key.decode("utf-8"))
        return success
    except PermissionError:
        logger.error("Failed to save cookies. Permission denied.")
    except FileNotFoundError:
        logger.error("Failed to save cookies. File not found.")
    return False


def manual_cookies_stored() -> bool:
    """Check if manual cookies are stored."""
    username = settings.get_setting(settings.SettingKey.USDB_USER_NAME, "")
    key = _get_auth(SYSTEM_COOKIE_KEY, username)
    if not key:
        return False

    # Check if the cookie file exists
    if not utils.AppPaths.cookie_file.exists():
        return False

    # Check if the cookie file is empty
    cookies = _get_manual_cookies()
    if len(cookies) == 0:
        return False
    return True


def get_cookies(
    source: CookieSource, browser: settings.Browser | None = None
) -> CookieJar:
    """
    Return a CookieJar containing the cookies to be used for the requests according to the settings.
    If the source is CookieSource.BROWSER, the browser parameter is required.
    Note that the cookiejar might be empty if the cookies are not available.
    """
    match source:
        case CookieSource.MANUAL:
            return _get_manual_cookies()
        case CookieSource.BROWSER:
            if browser is None:
                raise ValueError("Browser parameter required for CookieSource.BROWSER")
            cookiejar = browser.cookies(settings.CookieFormat.COOKIEJAR)
            if not cookiejar:
                return CookieJar()
            # cast is safe because we know the type of the return value
            return cast(CookieJar, cookiejar)
        case _:
            assert False, "Invalid cookie source"
