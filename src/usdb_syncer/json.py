"""Generates a JSON from the passed song list."""

from __future__ import annotations

import datetime
import json
from json import JSONEncoder
from pathlib import Path
from typing import Any, Iterable

import attrs

from usdb_syncer import SongId
from usdb_syncer.constants import VERSION
from usdb_syncer.logger import get_logger
from usdb_syncer.resource_dl import _url_from_resource
from usdb_syncer.song_txt.headers import Headers
from usdb_syncer.usdb_song import UsdbSong

_logger = get_logger(__file__)

JSON_EXPORT_VERSION = "0.1.0"


def get_headers(txt_path: str) -> Headers:
    with open(txt_path, "r", encoding="utf-8") as file:
        lines = [line for line in file.read().splitlines() if line]
        return Headers.parse(lines, _logger)


@attrs.define(kw_only=True)
class SongExportData:
    """Meta Data describing a song from USDB including specific meta tag data"""

    id: SongId
    artist: str
    title: str
    year: int | None = None
    edition: str | None = None
    genre: str | None = None
    language: str | None = None
    golden_notes: bool
    cover_url: str | None = None
    cover_meta: str | None = None
    audio_url: str | None = None
    video_url: str | None = None
    duet: bool

    @classmethod
    def from_usdb_song(cls, song: UsdbSong) -> SongExportData | None:
        if not (meta := song.sync_meta) or not (txt := meta.txt):
            return None
        headers = get_headers(str(meta.path.with_name(txt.fname)))
        return cls(
            id=song.song_id,
            artist=headers.artist,
            title=headers.title,
            year=int(headers.year) if headers.year else None,
            edition=(
                None
                if (not headers.edition or headers.edition == "None")
                else headers.edition
            ),
            genre=(
                None
                if (not headers.genre or headers.genre == "None")
                else headers.genre
            ),
            language=song.language,
            golden_notes=song.golden_notes,
            cover_url=(
                meta.meta_tags.cover.source_url(_logger)
                if meta.meta_tags.cover
                else None
            ),
            cover_meta=(
                meta.meta_tags.cover.to_str("co") if meta.meta_tags.cover else None
            ),
            audio_url=(
                _url_from_resource(meta.meta_tags.audio)
                if meta.meta_tags.audio
                else None
            ),
            video_url=(
                _url_from_resource(meta.meta_tags.video)
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
    syncer_version: str = attrs.field(default=VERSION, init=False)
    export_version: str = attrs.field(default=JSON_EXPORT_VERSION, init=False)

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


def generate_song_json(songs: Iterable[SongId], path: Path) -> int:
    content = JsonSongList.from_songs(songs=songs, date=datetime.datetime.now())
    with path.open("w", encoding="utf8") as file:
        json.dump(content, file, cls=JsonSongListEncoder, ensure_ascii=False)
    return len(content.songs)
