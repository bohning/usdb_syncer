"""Generates a JSON from the passed song list."""

import datetime
import json
from pathlib import Path
from typing import Any, Iterable

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


def generate_song_json(songs: Iterable[SongId], path: Path) -> int:
    date = datetime.datetime.now()
    song_list: list[dict[str, Any]] = [
        {
            "id": song.song_id,
            "artist": headers.artist,
            "title": headers.title,
            "year": int(headers.year) if headers.year else None,
            "edition": (
                None
                if (not headers.edition or headers.edition == "None")
                else headers.edition
            ),
            "genre": (
                None
                if (not headers.genre or headers.genre == "None")
                else headers.genre
            ),
            "language": song.language,
            "golden_notes": song.golden_notes,
            "cover_url": (
                meta.meta_tags.cover.source_url(_logger)
                if meta.meta_tags.cover
                else None
            ),
            "cover_meta": (
                meta.meta_tags.cover.to_str("co") if meta.meta_tags.cover else None
            ),
            "audio_url": (
                _url_from_resource(meta.meta_tags.audio)
                if meta.meta_tags.audio
                else None
            ),
            "video_url": (
                _url_from_resource(meta.meta_tags.video)
                if meta.meta_tags.video
                else None
            ),
            "duet": (
                meta.meta_tags.player1 is not None
                and meta.meta_tags.player2 is not None
            ),
        }
        for song_id in songs
        if (song := UsdbSong.get(song_id))
        and (meta := song.sync_meta)
        and (txt := meta.txt)
        and (headers := get_headers(str(meta.path.with_name(txt.fname))))
    ]
    content = {
        "songs": song_list,
        "date": str(date),
        "syncer_version": VERSION,
        "export_version": JSON_EXPORT_VERSION,
    }

    with open(path, "w", encoding="utf8") as file:
        json.dump(content, file, ensure_ascii=False)

    return len(song_list)
