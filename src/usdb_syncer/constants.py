"""Constants"""

import re

# set in the release workflow
VERSION = "dev"
COMMIT_HASH = "dev"

MINIMUM_BPM = 200.0


class UsdbStrings:
    """Relevant strings from USDB"""

    WELCOME: str
    SONG_EDITED_BY: str
    SONG_RATING: str
    GOLDEN_NOTES: str
    SONGCHECK: str
    DATE: str
    CREATED_BY: str
    VIEWS: str
    YES: str
    NO: str
    DATASET_NOT_FOUND = "Datensatz nicht gefunden"
    WELCOME_PLEASE_LOGIN = "Welcome, Please login"
    LOGIN_INVALID = "Login or Password invalid, please try again."
    NOT_LOGGED_IN = "You are not logged in. Login to use this function."


class UsdbStringsEnglish(UsdbStrings):
    """Relevant strings from USDB"""

    WELCOME = "Welcome"
    SONG_EDITED_BY = "Song edited by:"
    SONG_RATING = "Rating"
    GOLDEN_NOTES = "Golden Notes"
    SONGCHECK = "Songcheck"
    DATE = "Date"
    CREATED_BY = "Created by"
    VIEWS = "Views"
    YES = "Yes"
    NO = "No"


class UsdbStringsGerman(UsdbStrings):
    """Relevant strings from USDB"""

    WELCOME = "Willkommen"
    SONG_EDITED_BY = "Song editiert von:"
    SONG_RATING = "Bewertung"
    GOLDEN_NOTES = "Goldene Noten"
    SONGCHECK = "Songcheck"
    DATE = "Datum"
    CREATED_BY = "Erstellt von"
    VIEWS = "Aufrufe"
    YES = "Ja"
    NO = "Nein"


class UsdbStringsFrench(UsdbStrings):
    """Relevant strings from USDB"""

    WELCOME = "Bienvenue"
    SONG_EDITED_BY = "Chanson modifiée par:"
    SONG_RATING = "Classement"
    GOLDEN_NOTES = "Notes en or"
    SONGCHECK = "Songcheck"
    DATE = "Date"
    CREATED_BY = "créé par"
    VIEWS = "Affichages"
    YES = "Oui"
    NO = "Non"


class Usdb:
    """Constants related to USDB."""

    DOMAIN = "usdb.animux.de"
    BASE_URL = "https://" + DOMAIN + "/"
    REGISTER_URL = BASE_URL + "index.php?link=register"
    MAX_SONG_ID = 100_000
    MAX_SONGS_PER_PAGE = 100
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
