"""Icon accessor with auto-theming."""

import enum
import functools
from typing import assert_never

from PySide6.QtGui import QIcon

from usdb_syncer import settings


class Icon(enum.Enum):
    """Available icons with auto-theming."""

    ABORT = "minus-circle.png", "minus-circle-white.svg"
    ARC = "arc.png", None
    ARTIST = "artist.png", "artist-white.svg"
    AUDIO = "audio.png", "music-white.svg"
    AUDIO_SAMPLE = "sample.png", "music-note-white.svg"
    BACKGROUND = "background.png", "image-area-white.svg"
    BRAVE = "brave.png", None
    BUG = "bug.png", "bug-white.svg"
    CALENDAR = "calendar.png", "calendar-white.svg"
    CHECK = "tick.png", "check-white.svg"
    CHECK_FOR_UPDATE = "check_for_update.png", "sync-white.svg"
    CHEVRON_DOWN = None, "chevron-down-white.svg"
    CHEVRON_LEFT = None, "chevron-left-white.svg"
    CHEVRON_RIGHT = None, "chevron-right-white.svg"
    CHEVRON_UP = None, "chevron-up-white.svg"
    CHROME = "chrome.png", None
    CHROMIUM = "chromium.png", None
    COMMENT = "balloon.png", "comment-white.svg"
    COVER = "cover.png", "image-white.svg"
    CREATOR = "quill.png", "feather-white.svg"
    CUSTOM_DATA = "drawer.png", "dresser-white.svg"
    DATABASE = "database.png", "database-white.svg"
    DELETE = "bin.png", "delete-white.svg"
    DOWNLOAD = "status.png", "download-white.svg"
    EDGE = "edge.png", None
    EDITION = "edition.png", "edition-white.svg"
    ERROR = "error.png", "close-octagon-white.svg"
    FILE_EXPORT = "document-export.png", "file-export-white.svg"
    FILE_IMPORT = "document-import.png", "file-import-white.svg"
    FIREFOX = "firefox.png", None
    GENRE = "spectrum-absorption.png", "cards-white.svg"
    GOLDEN_NOTES = "golden_notes.png", "gold-white.svg"
    ID = "id.png", "database-marker-white.svg"
    INFO = "info.png", "information-white.svg"
    KAREDI = "karedi.png", None
    LANGUAGE = "language.png", "translate-variant-white.svg"
    LIBREWOLF = "librewolf.png", None
    LOG = "log.png", "receipt-text-white.svg"
    MENU_DOWN = None, "menu-down-white.svg"
    MENU_LEFT = None, "menu-left-white.svg"
    MENU_RIGHT = None, "menu-right-white.svg"
    MENU_UP = None, "menu-up-white.svg"
    META_TAGS = "tag-hash.png", "pound-box-white.svg"
    OCTO_BROWSER = "octo_browser.png", None
    OPEN_SONG_WITH = "music--arrow.png", "folder-play-white.svg"
    OPERA = "opera.png", None
    OPERA_GX = "opera_gx.png", None
    PAUSE_LOCAL = "control-pause-local.png", "pause-white.svg"
    PAUSE_REMOTE = "control-pause.png", "pause-white.svg"
    PERFORMOUS = "performous.png", None
    PIN = "pin.png", "pin-white.svg"
    PLAY_LOCAL = "control-play-local.png", "play-white.svg"
    PLAY_REMOTE = "control-play.png", "play-network-white.svg"
    RADIOBOX_BLANK = None, "radiobox-blank-white.svg"
    RADIOBOX_MARKED = None, "radiobox-marked-white.svg"
    RATING = "rating.png", "podium-white.svg"
    REPORT = "report.png", "notebook-white.svg"
    SAFARI = "safari.png", None
    SAVED_SEARCH = "heart.png", "heart-white.svg"
    SETTINGS = "cog.png", "cog-white.svg"
    SONG_FOLDER = "folder_note.png", "folder-music-white.svg"
    TAGS = "price-tag.png", "tag-white.svg"
    TEXT = "text.png", "file-document-white.svg"
    TITLE = "title.png", "format-title-white.svg"
    ULTRASTAR_MANAGER = "ultrastar-manager.png", None
    USDB = "faviconUSDB.png", "usdb-white.svg"
    USDX = "usdx.png", None
    VIDEO = "video.png", "filmstrip-white.svg"
    VIEWS = "views.png", "views-white.svg"
    VIVALDI = "vivaldi.png", None
    VOCALUXE = "vocaluxe.png", None
    WARNING = "warning.png", "alert-white.svg"
    YASS = "yass.png", None
    YASS_RELOADED = "yass-reloaded.png", None

    def __init__(self, colored_name: str | None, white_name: str | None):
        colored = colored_name or white_name
        white = white_name or colored_name
        assert colored is not None and white is not None, (
            f"{self.__class__.__name__}.{self.name}: At least one value must be "
            "supplied"
        )
        self.colored_name = colored
        self.white_name = white

    def icon(self, theme: settings.Theme | None = None) -> QIcon:
        colored = (theme or settings.get_theme()) == settings.Theme.SYSTEM
        return _icon(self.colored_name if colored else self.white_name)


def browser_icon(browser: settings.Browser) -> QIcon | None:  # noqa: C901
    match browser:
        case settings.Browser.NONE:
            return None
        case settings.Browser.ARC:
            icon = Icon.ARC
        case settings.Browser.BRAVE:
            icon = Icon.BRAVE
        case settings.Browser.CHROME:
            icon = Icon.CHROME
        case settings.Browser.CHROMIUM:
            icon = Icon.CHROMIUM
        case settings.Browser.EDGE:
            icon = Icon.EDGE
        case settings.Browser.FIREFOX:
            icon = Icon.FIREFOX
        case settings.Browser.LIBREWOLF:
            icon = Icon.LIBREWOLF
        case settings.Browser.OCTO_BROWSER:
            icon = Icon.OCTO_BROWSER
        case settings.Browser.OPERA:
            icon = Icon.OPERA
        case settings.Browser.OPERA_GX:
            icon = Icon.OPERA_GX
        case settings.Browser.SAFARI:
            icon = Icon.SAFARI
        case settings.Browser.VIVALDI:
            icon = Icon.VIVALDI
        case _ as unreachable:
            assert_never(unreachable)
    return icon.icon()


@functools.cache
def _icon(name: str) -> QIcon:
    return QIcon(f":/icons/{name}")
