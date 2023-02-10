"""Constants"""

import re

MINIMUM_BPM = 200.0


class UsdbLanguage:
    """Possible UI languages of usdb"""

    ENGLISH = "English"
    GERMAN = "German"
    FRENCH = "French"


class Usdb:
    """Constants related to USDB."""

    DOMAIN = "usdb.animux.de"
    BASE_URL = "https://" + DOMAIN + "/"
    MAX_SONG_ID = 30000
    MAX_SONGS_PER_PAGE = 100
    DATASET_NOT_FOUND_STRING = "Datensatz nicht gefunden"
    WELCOME_STRING = {
        UsdbLanguage.ENGLISH: "Welcome",
        UsdbLanguage.GERMAN: "Willkommen",
        UsdbLanguage.FRENCH: "Bienvenue",
    }
    SONG_EDITED_BY_STRING = {
        UsdbLanguage.ENGLISH: "Song edited by:",
        UsdbLanguage.GERMAN: "Song editiert von:",
        UsdbLanguage.FRENCH: "Chanson modifiée par:",
    }
    SONG_RATING_STRING = {
        UsdbLanguage.ENGLISH: "Rating",
        UsdbLanguage.GERMAN: "Bewertung",
        UsdbLanguage.FRENCH: "Classement",
    }
    GOLDEN_NOTES_STRING = {
        UsdbLanguage.ENGLISH: "Golden Notes",
        UsdbLanguage.GERMAN: "Goldene Noten",
        UsdbLanguage.FRENCH: "Notes en or",
    }
    SONGCHECK_STRING = {
        UsdbLanguage.ENGLISH: "Songcheck",
        UsdbLanguage.GERMAN: "Songcheck",
        UsdbLanguage.FRENCH: "Songcheck",
    }
    DATE_STRING = {
        UsdbLanguage.ENGLISH: "Date",
        UsdbLanguage.GERMAN: "Datum",
        UsdbLanguage.FRENCH: "Date",
    }
    CREATED_BY_STRING = {
        UsdbLanguage.ENGLISH: "Created by",
        UsdbLanguage.GERMAN: "Erstellt von",
        UsdbLanguage.FRENCH: "créé par",
    }
    VIEWS_STRING = {
        UsdbLanguage.ENGLISH: "Views",
        UsdbLanguage.GERMAN: "Aufrufe",
        UsdbLanguage.FRENCH: "Affichages",
    }
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
