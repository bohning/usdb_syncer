"""Constants"""

import re

MINIMUM_BPM = 200.0


class Usdb:
    """Constants related to USDB."""

    DOMAIN = "usdb.animux.de"
    BASE_URL = "https://" + DOMAIN + "/"
    MAX_SONG_ID = 30000
    MAX_SONGS_PER_PAGE = 100
    DATASET_NOT_FOUND_STRING = "Datensatz nicht gefunden"
    SONG_EDITED_BY_STRING = "Song edited by:"
    SONG_RATING_STRING = "Rating"
    GOLDEN_NOTES_STRING = "Golden Notes"
    SONGCHECK_STRING = "Songcheck"
    DATE_STRING = "Date"
    CREATED_BY_STRING = "Created by"
    VIEWS_STRING = "Views"
    DATETIME_STRF = "%d.%m.%y - %H:%M"


SUPPORTED_VIDEO_SOURCES_REGEX = re.compile(
    r"""\b
        (
            (?:https?://)?
            (?:www\.)?
            (?:
                youtube\.com
                | youtube-nocookie\.com
                | youtu\.be
                | vimeo\.com
                | archive\.org
                | fb\.watch
                | universal-music\.de
                | dailymotion\.com
            )
            /\S+
        )
    """,
    re.VERBOSE,
)
