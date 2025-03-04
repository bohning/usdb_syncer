"""Functions for Disord integration."""

from functools import lru_cache

import requests

from usdb_syncer import SongId
from usdb_syncer.constants import Usdb
from usdb_syncer.usdb_song import UsdbSong

BASE_URL = "https://discordapp.com/api/webhooks"
WH_CONFIG_URL = "https://github.com/bohning/usdb_syncer/tree/enhance_resource_error_handling/src/usdb_syncer/wh.json"

sent_notifications: set[tuple[SongId, str]] = set()
cached_dwh_url: str | None = None


@lru_cache(maxsize=1)
def _get_dwh_url() -> str | None:
    try:
        response = requests.get(WH_CONFIG_URL, timeout=5)
        response.raise_for_status()
        data = response.json()

        if "channel" in data and "hash" in data:
            return f"{BASE_URL}/{data['channel']}/{data['hash']}"
    except requests.RequestException:
        pass
    return None


def notify_discord(song_id: SongId, url: str) -> None:
    """Notify unavailable resources on Discord (without using the discord package)."""
    if not (song := UsdbSong.get(song_id)):
        return

    if (song_id, url) in sent_notifications:
        return

    dwh_url = _get_dwh_url()
    if not dwh_url:
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
