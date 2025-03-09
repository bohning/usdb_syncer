"""Functions for Disord integration."""

import requests

from usdb_syncer import SongId, db, remote_config
from usdb_syncer.constants import Usdb
from usdb_syncer.logger import Log
from usdb_syncer.usdb_song import UsdbSong


def notify_discord(song_id: SongId, url: str, logger: Log) -> None:
    """Notify unavailable resources on Discord (without using the discord package)."""
    if not (song := UsdbSong.get(song_id)):
        logger.debug("Song id does not exist.")
        return

    if not (dwh_url := remote_config.discord_webhook_url()):
        logger.debug("No discord webhook configured. Skipping Discord notification.")
        return

    with db.transaction():
        if not db.maybe_insert_discord_notification(song_id, url):
            logger.debug(
                "Failed resource was already reported. Skipping Discord notification."
            )
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
        response.raise_for_status()
