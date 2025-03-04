"""Functions for Disord integration."""

import requests

from usdb_syncer import SongId
from usdb_syncer.constants import Usdb
from usdb_syncer.usdb_song import UsdbSong

BASE_URL = "https://discordapp.com/api/webhooks"
CHANNEL = "1231022685513973840"
HASH = "0MfBIqFH9JFl4zALvqdm-etzIuT6OefxH12YXjCTMw7xyyhUlSL1oJkxjnifQmrZ2tzD"
WEBHOOK_URL = f"{BASE_URL}/{CHANNEL}/{HASH}"

sent_notifications: set[tuple[SongId, str]] = set()


def notify_discord(song_id: SongId, url: str) -> None:
    """Notify unavailable resources on Discord (without using the discord package)."""

    if (song_id, url) in sent_notifications:
        return

    if not (song := UsdbSong.get(song_id)):
        return

    embed = {
        "color": 15548997,  # 0xED4245, equivalent to discord.Color.red()
        "author": {
            "name": f"{song_id}: {song.artist} - {song.title}",
            "url": f"{Usdb.DETAILS_URL}{song_id}",
            "icon_url": f"{Usdb.COVER_URL}{song_id}.jpg",
        },
        "fields": [{"name": "Failed resource:", "value": url, "inline": False}],
    }

    payload = {"embeds": [embed]}

    response = requests.post(WEBHOOK_URL, json=payload, timeout=5)
    response.raise_for_status()  # Raise an error if request fails

    sent_notifications.add((song_id, url))
