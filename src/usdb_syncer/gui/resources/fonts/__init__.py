"""File was generated using `write_resource_files.py`."""

from functools import cache
from importlib import resources

from PySide6.QtGui import QFont, QFontDatabase

NOTOSANS_BLACK_TTF = resources.files(__package__) / "NotoSans-Black.ttf"
NOTOSANS_BOLD_TTF = resources.files(__package__) / "NotoSans-Bold.ttf"
NOTOSANS_REGULAR_TTF = resources.files(__package__) / "NotoSans-Regular.ttf"
NOTOSANS_SYMBOLS2_TTF = resources.files(__package__) / "NotoSansSymbols2-Regular.ttf"


@cache
def get_rating_font() -> QFont | None:
    """Load the Noto Sans Symbols 2 font for rating display."""
    font_path = str(NOTOSANS_SYMBOLS2_TTF)
    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id >= 0:
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            return QFont(families[0])
    return None
