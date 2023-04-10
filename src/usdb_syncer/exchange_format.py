"""Import and export lists of USDB IDs from file system."""

import configparser
import json
import os
from urllib.parse import parse_qs, urlparse

import attrs
from bs4 import BeautifulSoup

from usdb_syncer import SongId


@attrs.define
class UsdbIdFileParserError(Exception):
    """USDB File Parser root exception"""


@attrs.define
class UsdbIdFileParserUnsupportedExtensionError(UsdbIdFileParserError):
    """file extension is not supported for parsing"""

    def __str__(self) -> str:
        return "file extension is not supported"


@attrs.define
class UnexpectedUsdbIdFileParserError(UsdbIdFileParserError):
    """Unknown cause while reading file"""

    def __str__(self) -> str:
        return "Unexpected error reading file"


@attrs.define
class UsdbIdFileParserReadError(UsdbIdFileParserError):
    """Error reading file from file system"""

    def __str__(self) -> str:
        return "failed to read file"


@attrs.define
class UsdbIdFileParserInvalidFormatError(UsdbIdFileParserError):
    """Invalid file format"""

    def __str__(self) -> str:
        return "invalid file format"


@attrs.define
class UsdbIdFileParserMissingSectionHeaderFormatError(
    UsdbIdFileParserInvalidFormatError
):
    """Invalid file format with missing section header"""

    def __str__(self) -> str:
        return f"{super().__str__()}: missing a section header"


@attrs.define
class UsdbIdFileParserMissingOrDublicateOptionFormatError(
    UsdbIdFileParserInvalidFormatError
):
    """Invalid file format with missing or dublicate option"""

    def __str__(self) -> str:
        return f"{super().__str__()}: missing or dublicate option"


@attrs.define
class UsdbIdFileParserMultipleUrlsFormatError(UsdbIdFileParserInvalidFormatError):
    """Invalid file format with multiple URLs"""

    def __str__(self) -> str:
        return f"{super().__str__()}: file contains multiple URLs"


@attrs.define
class UsdbIdFileParserMissingKeyFormatError(UsdbIdFileParserInvalidFormatError):
    """Invalid file format with missing key in file"""

    missing_key: str

    def __str__(self) -> str:
        return f"{super().__str__()}: missing key '{self.missing_key}'"


@attrs.define
class UsdbIdFileParserMissingSectionFormatError(UsdbIdFileParserInvalidFormatError):
    """Invalid file format with missing section in file"""

    missing_section: str

    def __str__(self) -> str:
        return f"{super().__str__()}: missing section '{self.missing_section}'"


@attrs.define
class UsdbIdFileParserMissingTagFormatError(UsdbIdFileParserInvalidFormatError):
    """Invalid file format with missing tag in file"""

    missing_tag: str

    def __str__(self) -> str:
        return f"{super().__str__()}: missing tag '{self.missing_tag}'"


@attrs.define
class UsdbIdFileParserMultipleTagsFormatError(UsdbIdFileParserInvalidFormatError):
    """Invalid file format with a tag occurring multiple times instead of just once"""

    multiple_tag: str

    def __str__(self) -> str:
        return f"{super().__str__()}: multiple tags '{self.multiple_tag}'"


@attrs.define
class UsdbIdFileParserMissingUrlTagFormatError(UsdbIdFileParserInvalidFormatError):
    """Invalid file format with missing tag for URL in file"""

    missing_tag: str

    def __str__(self) -> str:
        return f"{super().__str__()}: missing URL tag '{self.missing_tag}'"


@attrs.define
class UsdbIdFileParserMalformedUrlFormatError(UsdbIdFileParserInvalidFormatError):
    """Invalid file format with URL in bad format"""

    bad_url: str

    def __str__(self) -> str:
        return f"{super().__str__()}: malformed URL '{self.bad_url}'"


@attrs.define
class UsdbIdFileParserInvalidDomainMalformedUrlFormatError(
    UsdbIdFileParserMalformedUrlFormatError
):
    """Invalid file format with URL containing bad domain"""

    bad_domain: str
    bad_url: str

    def __str__(self) -> str:
        return f"{super().__str__()}: has invalid domain '{self.bad_domain}'"


@attrs.define
class UsdbIdFileParserNoParametersMalformedUrlFormatError(
    UsdbIdFileParserMalformedUrlFormatError
):
    """Invalid file format with URL having no query parameters"""

    bad_url: str

    def __str__(self) -> str:
        return f"{super().__str__()}: has no query parameters"


@attrs.define
class UsdbIdFileParserMissingQueryParameterMalformedUrlFormatError(
    UsdbIdFileParserMalformedUrlFormatError
):
    """Invalid file format with URL missing a specific query parameter"""

    missing_parameter: str
    bad_url: str

    def __str__(self) -> str:
        return (
            f"{super().__str__()}: missing query parameter '{self.missing_parameter}'"
        )


@attrs.define
class UsdbIdFileParserRepeatedQueryParameterMalformedUrlFormatError(
    UsdbIdFileParserMalformedUrlFormatError
):
    """Invalid file format with URL specific query parameter occurring multiple times"""

    repeated_parameter: str
    bad_url: str

    def __str__(self) -> str:
        return (
            f"{super().__str__()}: repeated query parameter '{self.repeated_parameter}'"
        )


@attrs.define
class UsdbIdFileParserInvalidQueryParameterMalformedUrlFormatError(
    UsdbIdFileParserMalformedUrlFormatError
):
    """Invalid file format with URL having an invalid query parameter"""

    invalid_parameter: str
    bad_url: str

    def __str__(self) -> str:
        return (
            f"{super().__str__()}: invalid query parameter '{self.invalid_parameter}'"
        )


@attrs.define
class UsdbIdFileParserUnparsableQueryParameterMalformedUrlFormatError(
    UsdbIdFileParserMalformedUrlFormatError
):
    """Invalid file format with URL having a query parameter that cannot be parsed"""

    unparsable_parameter: str
    bad_url: str

    def __str__(self) -> str:
        return (
            f"{super().__str__()}: could not parse query parameter "
            f"'{self.unparsable_parameter}'"
        )


@attrs.define
class UsdbIdFileParserEmptyFileError(UsdbIdFileParserError):
    """Files do not contain any USDB ID but were selected for import"""

    def __str__(self) -> str:
        return "empty file"


@attrs.define
class UsdbIdFileParserInvalidJsonError(UsdbIdFileParserError):
    """failed to interpret file content as JSON"""

    def __str__(self) -> str:
        return "invalid JSON format"


@attrs.define
class UsdbIdFileParserEmptyJsonArrayError(UsdbIdFileParserError):
    """file content is an emty JSON array"""

    def __str__(self) -> str:
        return "empty JSON array"


@attrs.define
class UsdbIdFileParserNoJsonArrayError(UsdbIdFileParserError):
    """file content is valid JSON, but not an array"""

    def __str__(self) -> str:
        return "file does not contain a JSON array"


@attrs.define
class UsdbIdFileParserInvalidUsdbIdError(UsdbIdFileParserError):
    """expected USDB ID string cannot be converted correctly"""

    def __str__(self) -> str:
        return "invalid USDB ID in file"


@attrs.define
class UnexpectedUsdbIdFileParserInvalidUsdbIdError(UsdbIdFileParserInvalidUsdbIdError):
    """some unknown error around parsing an USDB ID string"""

    def __str__(self) -> str:
        return "unexpected error when parsing USDB ID(s)"


@attrs.define
class UsdbIdFileParserNoUrlFoundError(UsdbIdFileParserError):
    """parser could not find an URL in file content"""

    def __str__(self) -> str:
        return "no URL found"


class UsdbIdFileParser:
    """file parser for USDB IDs"""

    ids: list[SongId] = []
    error: UsdbIdFileParserError | None = None

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.ids = []
        self.error = None
        try:
            self.parse()
        except UsdbIdFileParserError as exception:
            self.error = exception

    def parse(self) -> None:
        file_extension = os.path.splitext(self.filepath)[1]
        if file_extension == ".json":
            self.parse_json_file()
        elif file_extension == ".url":
            self.parse_url_file()
        elif file_extension == ".desktop":
            self.parse_desktop_file()
        elif file_extension == ".webloc":
            self.parse_webloc_file()
        elif file_extension == ".usdb_ids":
            self.parse_usdb_ids_file()
        else:
            raise UsdbIdFileParserUnsupportedExtensionError()

    def get_json_file_content(self) -> str:
        filecontent: str
        try:
            with open(self.filepath, "r", encoding="utf-8") as file:
                filecontent = file.read()
        except OSError as exception:
            raise UsdbIdFileParserReadError() from exception
        except Exception as exception:
            raise UnexpectedUsdbIdFileParserError() from exception
        if not filecontent:
            raise UsdbIdFileParserEmptyFileError()
        return filecontent

    def parse_json_file(self) -> None:
        filecontent = self.get_json_file_content()

        parsed_json = None
        try:
            parsed_json = json.loads(filecontent)
        except json.decoder.JSONDecodeError as exception:
            raise UsdbIdFileParserInvalidJsonError() from exception
        except Exception as exception:
            raise UnexpectedUsdbIdFileParserError() from exception

        if not isinstance(parsed_json, list):
            raise UsdbIdFileParserNoJsonArrayError()

        if not parsed_json:
            raise UsdbIdFileParserEmptyJsonArrayError()

        key = "id"
        try:
            self.ids = [SongId.parse(element[key]) for element in parsed_json]
        except ValueError as exception:
            raise UsdbIdFileParserInvalidUsdbIdError() from exception
        except (KeyError, IndexError) as exception:
            raise UsdbIdFileParserMissingKeyFormatError(
                exception.args[0]
            ) from exception
        except Exception as exception:
            raise UnexpectedUsdbIdFileParserInvalidUsdbIdError() from exception

    def parse_ini_file(self, section: str, key: str) -> None:
        config = configparser.ConfigParser()
        try:
            config.read(self.filepath)
        except configparser.MissingSectionHeaderError as exception:
            raise UsdbIdFileParserMissingSectionHeaderFormatError() from exception
        except Exception as exception:
            raise UsdbIdFileParserMissingOrDublicateOptionFormatError() from exception
        if not config.sections():
            raise UsdbIdFileParserEmptyFileError()
        if section not in config:
            raise UsdbIdFileParserMissingSectionFormatError(section)
        if key not in config[section]:
            raise UsdbIdFileParserMissingKeyFormatError(key)
        url = config[section][key]
        self.parse_url(url)

    def parse_url_file(self) -> None:
        self.parse_ini_file(section="InternetShortcut", key="URL")

    def parse_desktop_file(self) -> None:
        self.parse_ini_file(section="Desktop Entry", key="URL")

    def parse_webloc_file(self) -> None:
        try:
            with open(self.filepath, "r", encoding="utf-8") as file:
                soup = BeautifulSoup(file, features="lxml-xml")
        except OSError as exception:
            raise UsdbIdFileParserReadError() from exception
        except Exception as exception:
            raise UnexpectedUsdbIdFileParserError() from exception

        if soup.is_empty_element:
            raise UsdbIdFileParserEmptyFileError()
        tag = "plist"
        xml_plist = soup.find_all(tag)
        if not xml_plist:
            raise UsdbIdFileParserMissingTagFormatError(tag)
        if len(xml_plist) > 1:
            raise UsdbIdFileParserMultipleTagsFormatError(tag)
        tag = "dict"
        xml_dict = xml_plist[0].find_all(tag)
        if not xml_dict:
            raise UsdbIdFileParserMissingTagFormatError(tag)
        if len(xml_dict) > 1:
            raise UsdbIdFileParserMultipleTagsFormatError(tag)
        tag = "string"
        xml_string = xml_dict[0].find_all(tag)
        if not xml_string:
            raise UsdbIdFileParserMissingUrlTagFormatError(tag)
        if len(xml_string) > 1:
            raise UsdbIdFileParserMultipleUrlsFormatError()

        url = xml_string[0].get_text()
        self.parse_url(url)

    def parse_usdb_ids_file(self) -> None:
        lines: list[str] = []
        try:
            with open(self.filepath, "r", encoding="utf-8") as file:
                lines = file.readlines()
        except OSError as exception:
            raise UsdbIdFileParserReadError() from exception
        except Exception as exception:
            raise UnexpectedUsdbIdFileParserError() from exception

        if not lines:
            raise UsdbIdFileParserEmptyFileError()

        try:
            self.ids = [SongId.parse(line) for line in lines]
        except ValueError as exception:
            raise UsdbIdFileParserInvalidUsdbIdError() from exception
        except Exception as exception:
            raise UnexpectedUsdbIdFileParserInvalidUsdbIdError() from exception

    def parse_url(self, url: str | None) -> None:
        if not url:
            raise UsdbIdFileParserNoUrlFoundError()
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            raise UsdbIdFileParserMalformedUrlFormatError(url)
        if parsed_url.netloc != "usdb.animux.de":
            raise UsdbIdFileParserInvalidDomainMalformedUrlFormatError(
                url, parsed_url.netloc
            )
        if not parsed_url.query:
            raise UsdbIdFileParserNoParametersMalformedUrlFormatError(url)
        query_params = parse_qs(parsed_url.query)
        id_param = "id"
        if id_param not in query_params:
            raise UsdbIdFileParserMissingQueryParameterMalformedUrlFormatError(
                url, id_param
            )
        if len(query_params[id_param]) > 1:
            raise UsdbIdFileParserRepeatedQueryParameterMalformedUrlFormatError(
                url, id_param
            )
        try:
            self.ids = [SongId.parse(query_params[id_param][0])]
        except ValueError as exception:
            raise UsdbIdFileParserInvalidQueryParameterMalformedUrlFormatError(
                url, id_param
            ) from exception
        except Exception as exception:
            # handle any other exception
            raise UsdbIdFileParserUnparsableQueryParameterMalformedUrlFormatError(
                url, id_param
            ) from exception


def write_song_ids_to_file(path: str, song_ids: list[SongId]) -> None:
    with open(path, encoding="utf-8", mode="w") as file:
        file.write("\n".join(str(id) for id in song_ids))
