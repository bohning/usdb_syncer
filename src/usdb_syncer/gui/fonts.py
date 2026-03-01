"""Functions related to fonts used in the GUI."""

from functools import cache

from PySide6.QtGui import QFont, QFontDatabase

from usdb_syncer.gui.resources.fonts import GONOTO_CURRENT_REGULAR_TTF


@cache
def get_rating_font() -> QFont | None:
    """Load the GoNotoCurrent Regular font for rating display."""
    font_path = str(GONOTO_CURRENT_REGULAR_TTF)
    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id >= 0:
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            return QFont(families[0])
    return None
