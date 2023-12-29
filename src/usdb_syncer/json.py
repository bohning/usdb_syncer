"""Generates a JSON from the passed song list."""

# maybe reportlab is better suited?
import base64
import datetime
import json
from typing import Any, Iterable

from PIL import Image

from usdb_syncer import SongId
from usdb_syncer.constants import VERSION
from usdb_syncer.logger import get_logger
from usdb_syncer.resource_dl import _url_from_resource
from usdb_syncer.song_txt.headers import Headers
from usdb_syncer.usdb_scraper import UsdbSong

_logger = get_logger(__file__)

MAX_SIZE = (100, 100)


def encode_image_to_json(
    image_path: str, max_size: tuple[int, int] | None = None
) -> str:
    """encode it to Base64, and store it in a JSON string with optional resize"""
    if max_size:
        # Open the image using Pillow
        with Image.open(image_path) as image:
            # Resize the image
            resized_image = image.resize(max_size)

            # Convert resized image to bytes
            with resized_image.convert("RGB") as resized_image_bytes:
                # Encode image data to Base64
                encoded_image = base64.b64encode(resized_image_bytes.tobytes()).decode(
                    "utf-8"
                )
    else:
        with open(image_path, "rb") as image_file:
            # Encode image data to Base64
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

    # Create a dictionary with the image data
    image_data = {"image": encoded_image}

    # Convert the dictionary to a JSON string
    json_string = json.dumps(image_data)

    return json_string


def get_headers(txt_path: str) -> Headers:
    with open(txt_path, "r", encoding="utf-8") as file:
        lines = [line for line in file.read().splitlines() if line]
        return Headers.parse(lines, _logger)


def generate_song_json(songs: Iterable[SongId], path: str) -> int:
    date = datetime.datetime.now()
    song_list: list[dict[str, Any]] = [
        {
            "id": song.song_id,
            "artist": headers.artist,
            "title": headers.title,
            "year": headers.year,
            "edition": song.edition,
            "genre": headers.genre,
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
            "cover_preview": (
                encode_image_to_json(
                    str(meta.path.with_name(meta.cover.fname)), MAX_SIZE
                )
                if meta.cover
                else None
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
        and (headers := get_headers(str(meta.path)))
    ]
    content = {"songs": song_list, "date": str(date), "syncer_version": VERSION}

    with open(path, "w", encoding="utf8") as file:
        json.dump(content, file, ensure_ascii=False)

    return len(song_list)
