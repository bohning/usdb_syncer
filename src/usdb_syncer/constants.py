"""Constants"""

import re

MINIMUM_BPM = 200.0
GITHUB_API_LATEST = "https://api.github.com/repos/bohning/usdb_syncer/releases/latest"
GITHUB_DL_LATEST = "https://github.com/bohning/usdb_syncer/releases/latest"
GITHUB_SHARED_CONTENT = (
    "https://raw.githubusercontent.com/bohning/usdb_syncer/refs/heads/main/shared"
)
DISCORD_WEBHOOK_API = "https://discordapp.com/api/webhooks"


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
    GETTXT_URL = BASE_URL + "?link=gettxt&id="
    DETAIL_URL = BASE_URL + "?link=detail&id="
    COVER_URL = BASE_URL + "data/cover/"
    MAX_SONG_ID = 100_000
    MAX_SONGS_PER_PAGE = 100
    DATETIME_STRF = "%d.%m.%y - %H:%M"


class YtErrorMsg:
    """Strings returned by yt-dlp when download fails"""

    YT_AGE_RESTRICTED = (
        "Sign in to confirm your age. This video may be inappropriate for some users."
    )
    YT_GEO_RESTRICTED = (
        "Video unavailable. The uploader has not made this video available in your "
        "country"
    )
    YT_UNAVAILABLE = "Video unavailable"
    YT_PARSE_ERROR = "Failed to parse XML"
    YT_FORBIDDEN = "HTTP Error 403: Forbidden"


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
                | web\.archive\.org
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

QUOTATION_MARKS = {
    "Bosnian": ("”", "”"),
    "Breton": ("«", "»"),
    "Catalan": ("«", "»"),
    "Chinese (romanized)": ("“", "”"),
    "Croatian": ("„", "”"),
    "Czech": ("„", "“"),
    "Danish": ("»", "«"),
    "Dutch": ("„", "”"),
    "English": ("“", "”"),
    "Estonian": ("„", "“"),
    "Finnish": ("”", "”"),
    "French": ("«", "»"),
    "Galician": ("«", "»"),
    "German": ("»", "«"),
    "Greek": ("«", "»"),
    "Greek (romanized)": ("«", "»"),
    "Hebrew": ("„", "”"),
    "Hindi": ("“", "”"),
    "Hindi (romanized)": ("“", "”"),
    "Hungarian": ("„", "”"),
    "Icelandic": ("„", "“"),
    "Indonesian": ("“", "”"),
    "Irish": ("“", "”"),
    "Italian": ("«", "»"),
    "Japanese": ("「", "」"),
    "Japanese (romanized)": ("「", "」"),
    "Korean": ("“", "”"),
    "Korean (romanized)": ("“", "”"),
    "Norwegian": ("«", "»"),
    "Polish": ("„", "”"),
    "Portuguese": ("«", "»"),
    "Portuguese (Brazil)": ("“", "”"),
    "Romanian": ("„", "”"),
    "Russian": ("«", "»"),
    "Russian (romanized)": ("«", "»"),
    "Scots": ("“", "”"),
    "Serbian": ("„", "“"),
    "Slovak": ("„", "“"),
    "Slovenian": ("„", "“"),
    "Spanish": ("«", "»"),
    "Swedish": ("”", "”"),
    "Turkish": ("“", "”"),
    "Ukrainian": ("«", "»"),
    "Vietnamese": ("“", "”"),
    "Welsh": ("‘", "’"),  # noqa: RUF001
}

QUOTATION_MARKS_TO_REPLACE = {'"', "„", "”", "«", "»", "“", "「", "」"}

LANGUAGES_WITH_SPACED_QUOTES = {"French", "Breton"}
