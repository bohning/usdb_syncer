"""Functions for Disord integration."""

import datetime

import discord

from usdb_syncer import SongId
from usdb_syncer.constants import Usdb

BASE_URL = "https://discordapp.com/api/webhooks"
CHANNEL = "1231022685513973840"
HASH = "0MfBIqFH9JFl4zALvqdm-etzIuT6OefxH12YXjCTMw7xyyhUlSL1oJkxjnifQmrZ2tzD"
WEBHOOK_URL = f"{BASE_URL}/{CHANNEL}/{HASH}"


def notify_discord(song_id: SongId, url: str) -> None:
    """Notify unavailable resources on Discord"""

    webhook = discord.SyncWebhook.from_url(WEBHOOK_URL)

    embed = discord.Embed(
        description=f"I tried, but failed: {url}", color=discord.Color.red()
    )

    embed.set_author(
        name=f"{song_id:d}: resource failure notification",
        url=f"{Usdb.DETAILS_URL}{song_id:d}",
        icon_url=f"{Usdb.COVER_URL}{song_id:d}.jpg",
    )
    embed.timestamp = datetime.datetime.utcnow()
    webhook.send(embed=embed)
