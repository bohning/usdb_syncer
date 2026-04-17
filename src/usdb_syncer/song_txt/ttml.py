"""TTML serialisation for UltraStar SongTxt."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

from usdb_syncer.constants import ISO_639_1_LANGUAGE_CODES

if TYPE_CHECKING:
    from usdb_syncer.meta_tags import MetaTags
    from usdb_syncer.song_txt.headers import Headers
    from usdb_syncer.song_txt.tracks import Note, Tracks

TTML = "http://www.w3.org/ns/ttml"
TTM = "http://www.w3.org/ns/ttml#metadata"
ITUNES = "http://music.apple.com/lyric-ttml-internal"
US = "http://www.example.com/ns/us"

# Register once at import time so ET never emits ns0:/ns1: prefixes.
ET.register_namespace("", TTML)
ET.register_namespace("ttm", TTM)
ET.register_namespace("itunes", ITUNES)
ET.register_namespace("us", US)

_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


def _timestamp_ttml(ms: int) -> str:
    """Format milliseconds as MM:SS.mmm."""
    minutes, ms_rem = divmod(ms, 60_000)
    seconds, ms_rem = divmod(ms_rem, 1_000)
    return f"{minutes:02}:{seconds:02}.{ms_rem:03}"


def _beats_to_ms(note_time: int, headers: Headers) -> int:
    return round(headers.bpm.beats_to_ms(note_time) + headers.gap)


def _build_metadata(
    metadata: ET.Element, headers: Headers, notes: Tracks, meta_tags: MetaTags
) -> None:
    """Populate the <metadata> element."""
    _build_agents(metadata, headers, notes, meta_tags)

    ET.SubElement(metadata, f"{{{TTM}}}title").text = headers.title

    def add_us_meta(key: str, value: str | None, *, multi: bool = False) -> None:
        if not value:
            return
        items = (
            (v.strip() for v in value.split(",") if v.strip()) if multi else (value,)
        )
        for item in items:
            ET.SubElement(metadata, f"{{{US}}}meta", {"key": key, "value": item})

    add_us_meta("artist", headers.artist)
    add_us_meta("title", headers.title)
    add_us_meta("language", headers.language, multi=True)
    add_us_meta("edition", headers.edition, multi=True)
    add_us_meta("genre", headers.genre, multi=True)
    add_us_meta("year", headers.year)
    add_us_meta("creator", headers.creator, multi=True)
    add_us_meta("bpm", str(headers.bpm.value))
    add_us_meta("gap", str(headers.gap))
    add_us_meta("metatags", str(meta_tags))


def _build_agents(
    metadata: ET.Element, headers: Headers, notes: Tracks, meta_tags: MetaTags
) -> None:
    """Add one or two <ttm:agent> elements depending on whether it's a duet."""
    if notes.track_2:
        for agent_id, player_meta, player_header in (
            ("v1", meta_tags.player1, headers.p1),
            ("v2", meta_tags.player2, headers.p2),
        ):
            agent = ET.SubElement(
                metadata, f"{{{TTM}}}agent", {"type": "person", _XML_ID: agent_id}
            )
            ET.SubElement(agent, f"{{{TTM}}}name", {"type": "full"}).text = (
                player_meta or player_header or agent_id.upper()
            )
    else:
        agent = ET.SubElement(
            metadata, f"{{{TTM}}}agent", {"type": "person", _XML_ID: "v1"}
        )
        ET.SubElement(agent, f"{{{TTM}}}name", {"type": "full"}).text = headers.artist


def _build_body(tt: ET.Element, headers: Headers, notes: Tracks) -> None:
    """Populate the <body> element with sorted, interleaved lines."""
    body = ET.SubElement(tt, f"{{{TTML}}}body")
    div = ET.SubElement(
        body, f"{{{TTML}}}div", {"begin": _timestamp_ttml(round(headers.gap))}
    )

    line_entries = _collect_lines(headers, notes)
    last_end = _append_paragraphs(div, headers, line_entries)

    div.set("end", _timestamp_ttml(last_end))
    div.set(f"{{{ITUNES}}}songPart", "Song")


def _collect_lines(
    headers: Headers, notes: Tracks
) -> list[tuple[int, int, str, list[Note]]]:
    """Return all lines from all tracks, sorted by start time."""
    entries: list[tuple[int, int, str, list[Note]]] = []
    for track_index, track in enumerate(notes.all_tracks(), start=1):
        agent_id = f"v{track_index}"
        for line in track:
            line_notes = list(line.notes)
            if not line_notes:
                continue
            line_start = _beats_to_ms(line_notes[0].start, headers)
            line_end = _beats_to_ms(
                line_notes[-1].start + line_notes[-1].duration, headers
            )
            entries.append((line_start, line_end, agent_id, line_notes))

    entries.sort(key=lambda e: e[0])
    return entries


def _append_paragraphs(
    div: ET.Element,
    headers: Headers,
    line_entries: list[tuple[int, int, str, list[Note]]],
) -> int:
    """Append <p> elements to div and return the last end timestamp in ms."""
    last_end = 0
    for line_number, (line_start, line_end, agent_id, line_notes) in enumerate(
        line_entries, start=1
    ):
        p = ET.SubElement(
            div,
            f"{{{TTML}}}p",
            {
                "begin": _timestamp_ttml(line_start),
                "end": _timestamp_ttml(line_end),
                f"{{{ITUNES}}}key": f"L{line_number}",
                f"{{{TTM}}}agent": agent_id,
            },
        )
        _append_spans(p, headers, line_notes)
        last_end = max(last_end, line_end)

    return last_end


def _append_spans(p: ET.Element, headers: Headers, line_notes: list[Note]) -> None:
    """Append one <span> per note to a <p> element."""
    for note in line_notes:
        start = _beats_to_ms(note.start, headers)
        end = _beats_to_ms(note.start + note.duration, headers)
        span = ET.SubElement(
            p,
            f"{{{TTML}}}span",
            {
                "begin": _timestamp_ttml(start),
                "end": _timestamp_ttml(end),
                f"{{{US}}}kind": note.kind.name.lower(),
                f"{{{US}}}pitch": str(note.pitch),
            },
        )
        span.text = note.text


def to_ttml(headers: Headers, notes: Tracks, meta_tags: MetaTags) -> str:
    """Serialise a SongTxt to an indented TTML string."""
    lang = ISO_639_1_LANGUAGE_CODES.get(headers.main_language(), "und")

    tt = ET.Element(f"{{{TTML}}}tt", {_XML_LANG: lang, f"{{{ITUNES}}}timing": "Word"})

    head = ET.SubElement(tt, f"{{{TTML}}}head")
    metadata = ET.SubElement(head, f"{{{TTML}}}metadata")
    _build_metadata(metadata, headers, notes, meta_tags)
    _build_body(tt, headers, notes)

    ET.indent(tt, space="    ")
    return ET.tostring(tt, encoding="unicode")
