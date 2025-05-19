"""Functions for Disord integration."""

import requests

from usdb_syncer import SongId, db, remote_config
from usdb_syncer.constants import Usdb
from usdb_syncer.logger import Logger
from usdb_syncer.usdb_song import UsdbSong

DISCORD_COLOR_RED = 0xED4245  # equivalent to discord.Color.red()


def notify_discord(
    song_id: SongId, url: str, kind: str, error_str: str, logger: Logger
) -> None:
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
            "color": DISCORD_COLOR_RED,
            "author": {
                "name": f"{song_id}: {song.artist} - {song.title}",
                "url": song_id.usdb_detail_url(),
                "icon_url": f"{Usdb.COVER_URL}{song_id:d}.jpg",
            },
            "fields": [{"name": f"{kind} {error_str}:", "value": url, "inline": False}],
        }

        payload = {"embeds": [embed]}

        response = requests.post(dwh_url, json=payload, timeout=5)
        response.raise_for_status()
