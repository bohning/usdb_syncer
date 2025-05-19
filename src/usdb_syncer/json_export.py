"""Generates a JSON from the passed song list."""

from __future__ import annotations

import datetime
import json
from collections.abc import Iterable
from json import JSONEncoder
from pathlib import Path
from typing import Any

import attrs

from usdb_syncer import SongId
from usdb_syncer.logger import logger
from usdb_syncer.usdb_song import UsdbSong
from usdb_syncer.utils import video_url_from_resource

JSON_EXPORT_VERSION = 1


@attrs.define(kw_only=True)
class SongExportData:
    """Meta Data describing a song from USDB including specific meta tag data"""

    id: SongId
    artist: str
    title: str
    year: int | None = None
    edition: str | None = None
    genre: str | None = None
    tags: str | None = None
    language: str | None = None
    golden_notes: bool
    cover_url: str | None = None
    cover_meta: str | None = None
    audio_url: str | None = None
    video_url: str | None = None
    duet: bool

    @classmethod
    def from_usdb_song(cls, song: UsdbSong) -> SongExportData | None:
        if not (meta := song.sync_meta):
            return None
        return cls(
            id=song.song_id,
            artist=song.artist,
            title=song.title,
            year=song.year,
            edition=(
                None if (not song.edition or song.edition == "None") else song.edition
            ),
            genre=song.genre,
            tags=song.tags,
            language=song.language,
            golden_notes=song.golden_notes,
            cover_url=(
                meta.meta_tags.cover.source_url(logger)
                if meta.meta_tags.cover
                else None
            ),
            cover_meta=(
                meta.meta_tags.cover.to_str("co") if meta.meta_tags.cover else None
            ),
            audio_url=(
                video_url_from_resource(meta.meta_tags.audio)
                if meta.meta_tags.audio
                else None
            ),
            video_url=(
                video_url_from_resource(meta.meta_tags.video)
                if meta.meta_tags.video
                else None
            ),
            duet=(
                meta.meta_tags.player1 is not None
                and meta.meta_tags.player2 is not None
            ),
        )


@attrs.define(kw_only=True)
class JsonSongList:
    """defines fields in JSON songlist export"""

    songs: list[SongExportData]
    date: str
    version: int = attrs.field(default=JSON_EXPORT_VERSION, init=False)

    @classmethod
    def from_songs(
        cls, songs: Iterable[SongId], date: datetime.datetime
    ) -> JsonSongList:
        song_list = [
            song_data
            for song_id in songs
            if (song := UsdbSong.get(song_id))
            and (song_data := SongExportData.from_usdb_song(song))
        ]
        return cls(songs=song_list, date=str(date))


class JsonSongListEncoder(JSONEncoder):
    """Custom JSON encoder for SongExportData"""

    def default(self, o: Any) -> Any:
        if isinstance(o, JsonSongList):
            dct = attrs.asdict(o, recurse=True)
            return dct
        return super().default(o)


def generate_report_json(
    songs: Iterable[SongId], path: Path, indent: int = 4
) -> tuple[Path, int]:
    content = JsonSongList.from_songs(songs=songs, date=datetime.datetime.now())
    with path.open("w", encoding="utf8") as file:
        json.dump(
            content, file, cls=JsonSongListEncoder, indent=indent, ensure_ascii=False
        )
    return path, len(content.songs)
