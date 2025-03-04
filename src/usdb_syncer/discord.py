"""Functions for Disord integration."""

from functools import lru_cache

import requests

from usdb_syncer import SongId
from usdb_syncer.constants import GITHUB_RAW, Usdb
from usdb_syncer.logger import Log
from usdb_syncer.usdb_song import UsdbSong

BASE_URL = "https://discordapp.com/api/webhooks"
WH_CONFIG_URL = (
    f"{GITHUB_RAW}/refs/heads/enhance_resource_error_handling/src/usdb_syncer/wh.json"
)

sent_notifications: set[tuple[SongId, str]] = set()
cached_dwh_url: str | None = None


@lru_cache(maxsize=1)
def _get_dwh_url(logger: Log) -> str | None:
    try:
        response = requests.get(WH_CONFIG_URL, timeout=5)
        response.raise_for_status()
        data = response.json()

        if "channel" in data and "hash" in data:
            logger.debug("Retrieved Discord webhook configuration.")
            return f"{BASE_URL}/{data['channel']}/{data['hash']}"
    except requests.RequestException:
        logger.debug("Failed to retrieve Discord webhook configuration.")
    return None


def notify_discord(song_id: SongId, url: str, logger: Log) -> None:
    """Notify unavailable resources on Discord (without using the discord package)."""
    if not (song := UsdbSong.get(song_id)):
        logger.debug("Song id does not exist.")
        return

    if (song_id, url) in sent_notifications:
        logger.debug(
            "Failed resource was already reported. Skipping Discord notification."
        )
        return

    dwh_url = _get_dwh_url(logger)
    if not dwh_url:
        logger.debug("No discord webhook configured. Skipping Discord notification.")
        return

    embed = {
        "color": 0xED4245,  # equivalent to discord.Color.red()
        "author": {
            "name": f"{song_id}: {song.artist} - {song.title}",
            "url": f"{Usdb.DETAILS_URL}{song_id}",
            "icon_url": f"{Usdb.COVER_URL}{song_id}.jpg",
        },
        "fields": [{"name": "Failed resource:", "value": url, "inline": False}],
    }

    payload = {"embeds": [embed]}

    response = requests.post(dwh_url, json=payload, timeout=5)
    response.raise_for_status()  # Raise an error if request fails

    sent_notifications.add((song_id, url))
