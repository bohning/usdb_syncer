"""Generates a PDF from the passed song list."""

# maybe reportlab is better suited?
import datetime
from typing import Any, Iterator

from pdfme import build_pdf  # type: ignore

from usdb_syncer.usdb_scraper import UsdbSong


def generate_song_pdf(songs: Iterator[UsdbSong], path: str) -> None:
    document: dict[str, Any] = {}
    document["style"] = {"margin_bottom": 15, "text_align": "j"}
    document["formats"] = {"url": {"c": "blue", "u": 1}, "title": {"b": 1, "s": 13}}
    document["sections"] = []
    section1: dict[str, list[Any]] = {}
    document["sections"].append(section1)
    content1: list[Any] = []
    section1["content"] = content1
    date = datetime.datetime.now()
    content1.append(
        {
            ".": f"Songlist ({date:%Y-%m-%d})",
            "style": "title",
            "label": "title1",
            "outline": {"level": 1, "text": "A different title 1"},
        }
    )

    for song in songs:
        data = f"{song.song_id}\t\t{song.artist}\t\t{song.title}\t\t{song.language}"
        content1.append([data.replace("’", "'")])

    with open(path, "wb") as file:
        build_pdf(document, file)
