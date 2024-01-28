"""Generates a PDF from the passed song list."""

import datetime
from typing import Iterable, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate

from usdb_syncer import SongId
from usdb_syncer.usdb_song import UsdbSong


def generate_song_pdf(songs: Iterable[SongId], path: str) -> None:
    # Create a PDF document
    doc = SimpleDocTemplate(path, pagesize=A4)

    # Define custom styles
    styles = getSampleStyleSheet()
    custom_styles = {
        "Title": ParagraphStyle("Title", parent=styles["Title"], fontSize=20),
        "Heading1": ParagraphStyle("Heading1", parent=styles["Heading1"], fontSize=14),
        "Normal": ParagraphStyle("Normal", parent=styles["Normal"], fontSize=12),
    }

    # Build the content
    content = []
    date = datetime.datetime.now()
    content.append(Paragraph(f"Songlist ({date:%Y-%m-%d})", custom_styles["Title"]))

    # Add table header
    table_header = ["Song ID", "Artist", "Title", "Language"]
    content.append(build_table_row(table_header, custom_styles["Heading1"]))

    # Add songs to the table
    for song_id in songs:
        song = UsdbSong.get(song_id)
        if song:
            song_data = [str(song.song_id), song.artist, song.title, song.language]
            content.append(build_table_row(song_data, custom_styles["Normal"]))

    # Build the PDF document
    doc.build(content)


def build_table_row(data: List[str], style: ParagraphStyle) -> Paragraph:
    return Paragraph("\t\t".join(data), style)
