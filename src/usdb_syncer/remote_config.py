"""Remote configuration fetched from GitHub at runtime."""

import functools
import json

import requests

from usdb_syncer import constants
from usdb_syncer.logger import logger
from usdb_syncer.utils import AppPaths

_CONFIG_URL = f"{constants.GITHUB_SHARED_CONTENT}/config.json"
_CONFIG_PATH = AppPaths.shared.joinpath("config.json") if AppPaths.shared else None


@functools.lru_cache(maxsize=1)
def discord_webhook_url() -> str | None:
    if (
        isinstance(dct := _fetch_config().get("discord_webhook"), dict)
        and isinstance(channel := dct.get("channel"), str)
        and isinstance(hash_ := dct.get("hash"), str)
    ):
        return "/".join((constants.DISCORD_WEBHOOK_API, channel, hash_))
    logger.debug("Failed to retrieve Discord webhook URL.")
    return None


@functools.lru_cache(maxsize=1)
def _fetch_config() -> dict:
    if _CONFIG_PATH:
        with _CONFIG_PATH.open(encoding="utf-8") as file:
            return json.load(file)
    return _fetch_remote_config()


def _fetch_remote_config() -> dict:
    try:
        response = requests.get(_CONFIG_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        logger.debug(f"Failed to retrieve remote configuration from {_CONFIG_URL}")
        logger.error(str(error))
        data = {}
    else:
        logger.debug(f"Retrieved remote configuration from {_CONFIG_URL}")
    return data
