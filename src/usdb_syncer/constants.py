"""Constants"""

import re

MINIMUM_BPM = 200.0
USDB_DOMAIN = "usdb.animux.de"
USDB_BASE_URL = "https://" + USDB_DOMAIN + "/"
USDB_DATASET_NOT_FOUND_STRING = "Datensatz nicht gefunden"
USDB_SONG_EDITED_BY_STRING = "Song edited by:"
USDB_SONG_RATING_STRING = "Rating"
USDB_GOLDEN_NOTES_STRING = "Golden Notes"
USDB_SONGCHECK_STRING = "Songcheck"
USDB_DATE_STRING = "Date"
USDB_CREATED_BY_STRING = "Created by"
USDB_VIEWS_STRING = "Views"
USDB_DATETIME_STRF = "%d.%m.%y - %H:%M"
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
