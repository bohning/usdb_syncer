"""Constants"""

import re

# set in the release workflow
VERSION = "dev"
COMMIT_HASH = "dev"
SHORT_COMMIT_HASH = COMMIT_HASH[:7]

MINIMUM_BPM = 200.0


class UsdbStrings:
    """Relevant strings from USDB"""

    WELCOME: str
    SONG_LANGUAGE: str
    SONG_YEAR: str
    SONG_EDITED_BY: str
    SONG_RATING: str
    GOLDEN_NOTES: str
    SONGCHECK: str
    DATE: str
    UPLOADED_BY: str
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
    SONG_LANGUAGE = "Language"
    SONG_YEAR = "Year"
    SONG_EDITED_BY = "Song edited by:"
    SONG_RATING = "Rating"
    GOLDEN_NOTES = "Golden Notes"
    SONGCHECK = "Songcheck"
    DATE = "Date"
    UPLOADED_BY = "Uploaded by"
    VIEWS = "Views"
    YES = "Yes"
    NO = "No"


class UsdbStringsGerman(UsdbStrings):
    """Relevant strings from USDB"""

    WELCOME = "Willkommen"
    SONG_LANGUAGE = "Sprache"
    SONG_YEAR = "Jahr"
    SONG_EDITED_BY = "Song editiert von:"
    SONG_RATING = "Bewertung"
    GOLDEN_NOTES = "Goldene Noten"
    SONGCHECK = "Songcheck"
    DATE = "Datum"
    UPLOADED_BY = "Hochgeladen von"
    VIEWS = "Aufrufe"
    YES = "Ja"
    NO = "Nein"


class UsdbStringsFrench(UsdbStrings):
    """Relevant strings from USDB"""

    WELCOME = "Bienvenue"
    SONG_LANGUAGE = "Langue"
    SONG_YEAR = "An"
    SONG_EDITED_BY = "Chanson modifiée par:"
    SONG_RATING = "Classement"
    GOLDEN_NOTES = "Notes en or"
    SONGCHECK = "Songcheck"
    DATE = "Date"
    UPLOADED_BY = "Téléchargé par"
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
            (?:www|web)\.?
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

ISO_639_2B_LANGUAGE_CODES = {
    "Bosnian": "bos",
    "Breton": "bre",
    "Catalan": "cat",
    "Chinese": "chi",
    "Croatian": "hrv",
    "Czech": "cze",
    "Danish": "dan",
    "Duala": "dua",
    "Dutch": "dut",
    "English": "eng",
    "Estonian": "est",
    "Finnish": "fin",
    "French": "fre",
    "Galician": "glg",
    "German": "ger",
    "Haitian": "hat",
    "Hebrew": "heb",
    "Hindi": "hin",
    "Hungarian": "hun",
    "Icelandic": "ice",
    "Indonesian": "ind",
    "Irish": "gle",
    "Italian": "ita",
    "Japanese": "jpn",
    "Korean": "kor",
    "Latin": "lat",
    "Malagasy": "mlg",
    "Maori": "mao",
    "Norwegian": "nor",
    "Polish": "pol",
    "Portuguese": "por",
    "Quechua": "que",
    "Romanian": "rum",
    "Russian": "rus",
    "Samoan": "smo",
    "Scots": "sco",
    "Serbian": "srp",
    "Slovak": "slo",
    "Slovenian": "slv",
    "Spanish": "spa",
    "Swedish": "swe",
    "Tagalog": "tgl",
    "Turkish": "tur",
    "Ukrainian": "ukr",
    "Vietnamese": "vie",
    "Welsh": "wel",
    "Yoruba": "yor",
    "Zulu": "zul",
}
