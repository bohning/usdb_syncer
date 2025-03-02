"""Functions for Disord integration."""

import discord

from usdb_syncer import SongId
from usdb_syncer.constants import Usdb
from usdb_syncer.usdb_song import UsdbSong

BASE_URL = "https://discordapp.com/api/webhooks"
CHANNEL = "1231022685513973840"
HASH = "0MfBIqFH9JFl4zALvqdm-etzIuT6OefxH12YXjCTMw7xyyhUlSL1oJkxjnifQmrZ2tzD"
WEBHOOK_URL = f"{BASE_URL}/{CHANNEL}/{HASH}"

sent_notifications: set[tuple[SongId, str]] = set()


def notify_discord(song_id: SongId, url: str) -> None:
    """Notify unavailable resources on Discord"""

    if (song_id, url) in sent_notifications:
        return
    webhook = discord.SyncWebhook.from_url(WEBHOOK_URL)
    embed = discord.Embed(color=discord.Color.red())
    if not (song := UsdbSong.get(song_id)):
        return
    embed.set_author(
        name=f"{song_id:d}: {song.artist} - {song.title}",
        url=f"{Usdb.DETAILS_URL}{song_id:d}",
        icon_url=f"{Usdb.COVER_URL}{song_id:d}.jpg",
    )
    embed.add_field(name="Failed resource:", value=url, inline=False)
    webhook.send(embed=embed)
    sent_notifications.add((song_id, url))
