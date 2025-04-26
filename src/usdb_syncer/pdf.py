"""Generates a PDF from the passed song list."""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from importlib import resources
from typing import assert_never

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, A4, A5, LEGAL, LETTER, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import BaseDocTemplate, Flowable, Frame, PageTemplate, Paragraph

from usdb_syncer import SongId, utils
from usdb_syncer.gui.resources import fonts
from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.settings import ReportPDFOrientation, ReportPDFPagesize
from usdb_syncer.usdb_song import UsdbSong

NOTOSANS_BLACK = "NotoSans-Black"
NOTOSANS_BOLD = "NotoSans-Bold"
NOTOSANS_REGULAR = "NotoSans-Regular"


_font_files = resources.files(fonts)
for name in (NOTOSANS_BLACK, NOTOSANS_BOLD, NOTOSANS_REGULAR):
    pdfmetrics.registerFont(TTFont(name, _font_files.joinpath(f"{name}.ttf")))


class Bookmark(Flowable):
    """Bookmark flowable."""

    def __init__(self, key: str, title: str, level: int = 0):
        super().__init__()
        self.key = key
        self.title = title
        self.level = level

    def draw(self) -> None:
        self.canv.bookmarkPage(self.key)
        self.canv.addOutlineEntry(self.title, self.key, level=self.level, closed=False)


def generate_report_pdf(
    *,
    songs: Iterable[SongId],
    path: str,
    size: ReportPDFPagesize = ReportPDFPagesize.A4,
    orientation: ReportPDFOrientation = ReportPDFOrientation.PORTRAIT,
    margin: int = 20,
    column_count: int = 1,
    base_font_size: int = 10,
    optional_info: list[Column] | None = None,
) -> str:
    optional_info = optional_info or []
    pagesize = _get_pagesize(size, orientation)

    doc: BaseDocTemplate = BaseDocTemplate(
        path,
        pagesize=pagesize,
        leftMargin=margin * mm,
        rightMargin=margin * mm,
        topMargin=margin * mm,
        bottomMargin=margin * mm,
    )

    custom_styles = _create_paragraph_styles(base_font_size)
    content = _build_pdf_content(songs, base_font_size, custom_styles, optional_info)

    gutter = margin * mm * 0.5
    frames = _create_column_frames(
        pagesize, margin=margin * mm, gutter=gutter, column_count=column_count
    )
    template = PageTemplate(
        id="with_page_number", frames=frames, onPage=_add_page_number
    )
    doc.addPageTemplates([template])
    doc.build(content)

    return path


def _get_pagesize(
    size: ReportPDFPagesize, orientation: ReportPDFOrientation
) -> tuple[float, float]:
    match size:
        case ReportPDFPagesize.A3:
            pagesize = A3
        case ReportPDFPagesize.A4:
            pagesize = A4
        case ReportPDFPagesize.A5:
            pagesize = A5
        case ReportPDFPagesize.LEGAL:
            pagesize = LEGAL
        case ReportPDFPagesize.LETTER:
            pagesize = LETTER
        case _ as unreachable:
            assert_never(unreachable)
    return (
        landscape(pagesize)
        if orientation == ReportPDFOrientation.LANDSCAPE
        else pagesize
    )


@dataclass(frozen=True)
class ParagraphStyles:
    """Paragraph styles for the report."""

    initial: ParagraphStyle
    artist: ParagraphStyle
    entry: ParagraphStyle


def _create_paragraph_styles(base_font_size: int) -> ParagraphStyles:
    return ParagraphStyles(
        initial=ParagraphStyle(
            "Initial",
            fontName=NOTOSANS_BLACK,
            fontSize=base_font_size * 3,
            textColor=colors.green,
            spaceBefore=base_font_size * 2.4,
            spaceAfter=base_font_size * 2.4,
        ),
        artist=ParagraphStyle(
            "Artist",
            fontName=NOTOSANS_BOLD,
            fontSize=base_font_size * 1.2,
            spaceBefore=base_font_size * 1.2,
            leading=base_font_size * 1.6,
            textColor=colors.black,
            leftIndent=0,
        ),
        entry=ParagraphStyle(
            "Entry",
            fontName=NOTOSANS_REGULAR,
            fontSize=base_font_size,
            leftIndent=base_font_size,
            leading=base_font_size * 1.4,
        ),
    )


def _build_pdf_content(
    songs: Iterable[SongId],
    base_font_size: int,
    styles: ParagraphStyles,
    optional_info: list[Column],
) -> list:
    content: list = []
    artist_map: dict[str, list[UsdbSong]] = defaultdict(list)
    for song_id in songs:
        song = UsdbSong.get(song_id)
        if song:
            artist_map[song.artist].append(song)

    initial_map: dict[str, dict[str, list[UsdbSong]]] = defaultdict(dict)
    for artist, artist_songs in artist_map.items():
        initial = utils.get_first_alphanum_upper(artist) or artist[0].upper()
        initial_map[initial][artist] = sorted(
            artist_songs, key=lambda s: s.title.lower()
        )

    for initial in sorted(initial_map.keys()):
        bookmark_key = f"initial_{initial}"
        content.append(Bookmark(bookmark_key, initial))
        content.append(Paragraph(initial, styles.initial))
        for artist in sorted(initial_map[initial].keys(), key=str.lower):
            content.append(Paragraph(f"<b>{artist}</b>", styles.artist))
            for song in initial_map[initial][artist]:
                entry = _format_song_entry(song, base_font_size, optional_info)
                content.append(Paragraph(entry, style=styles.entry))

    return content


def _format_song_entry(  # noqa: C901
    song: UsdbSong, base_font_size: int, optional_info: list[Column]
) -> str:
    entry = f"{song.title} "
    entry += f'<font size="{base_font_size * 0.8}" color="{colors.grey.hexval()}">'
    for column in optional_info:
        match column:
            case Column.LANGUAGE:
                if song.language:
                    entry += f"&nbsp;&nbsp;{song.language}"
            case Column.EDITION:
                if song.edition:
                    entry += f"&nbsp;&nbsp;{song.edition}"
            case Column.GENRE:
                if song.genre:
                    entry += f"&nbsp;&nbsp;{song.genre}"
            case Column.YEAR:
                if song.year:
                    entry += f"&nbsp;&nbsp;{song.year}"
            case Column.CREATOR:
                if song.creator:
                    entry += f"&nbsp;&nbsp;{song.creator}"
            case Column.SONG_ID:
                entry += f"&nbsp;&nbsp;({song.song_id})"
            case _:
                pass
    entry += "</font>"
    return entry


def _add_page_number(canvas: Canvas, doc: BaseDocTemplate) -> None:
    canvas.saveState()
    page_num: str = str(doc.page)
    canvas.setFont(NOTOSANS_REGULAR, 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(doc.pagesize[0] / 2, doc.bottomMargin * 0.5, page_num)
    canvas.restoreState()


def _create_column_frames(
    pagesize: tuple[float, float], margin: float, gutter: float, column_count: int
) -> list[Frame]:
    usable_width = pagesize[0] - 2 * margin - (column_count - 1) * gutter
    column_width = usable_width / column_count
    frames: list[Frame] = []

    for i in range(column_count):
        x = margin + i * (column_width + gutter)
        frame = Frame(
            x, margin, column_width, pagesize[1] - 2 * margin, id=f"col{i + 1}"
        )
        frames.append(frame)

    return frames
