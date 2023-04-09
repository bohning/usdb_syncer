"""Import and export lists of USDB IDs from file system."""

import configparser
import json
import os
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from usdb_syncer import SongId


class USDBIDFileParserError(Exception):
    """Differentiate known from unknown exceptions"""

    def __init__(self, message: str, detail: str | None = None):
        self.message = message
        self.detail = detail


class USDBIDFileParserUnsupportedExtensionError(USDBIDFileParserError):
    """file extension is not supported for parsing"""

    def __init__(self, detail: str | None = None):
        super().__init__("file extension is not supported", detail)


class UnexpectedUSDBIDFileParserError(USDBIDFileParserError):
    """Unknown cause while reading file"""

    def __init__(self, detail: str | None = None):
        super().__init__("Unexpected error reading file", detail)


class USDBIDFileParserReadError(USDBIDFileParserError):
    """Error reading file from file system"""

    def __init__(self, detail: str | None = None):
        super().__init__("failed to read file", detail)


class USDBIDFileParserInvalidFormatError(USDBIDFileParserError):
    """Invalid file format"""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(f"invalid file format: {message}", detail)


class USDBIDFileParserMissingSectionHeaderFormatError(
    USDBIDFileParserInvalidFormatError
):
    """Invalid file format with missing section header"""

    def __init__(self, detail: str | None = None):
        super().__init__("missing a section header", detail)


class USDBIDFileParserMissingOrDublicateOptionFormatError(
    USDBIDFileParserInvalidFormatError
):
    """Invalid file format with missing or dublicate option"""

    def __init__(self, detail: str | None = None):
        super().__init__("missing or dublicate option", detail)


class USDBIDFileParserMultipleURLsFormatError(USDBIDFileParserInvalidFormatError):
    """Invalid file format with multiple URLs"""

    def __init__(self, detail: str | None = None):
        super().__init__("file contains multiple URLs", detail)


class USDBIDFileParserEmptyFileError(USDBIDFileParserError):
    """Files do not contain any USDB ID but were selected for import"""

    def __init__(self, detail: str | None = None):
        super().__init__("empty file", detail)


class USDBIDFileParserInvalidJSONError(USDBIDFileParserError):
    """failed to interpret file content as JSON"""

    def __init__(self, detail: str | None = None):
        super().__init__("invalid JSON format", detail)


class USDBIDFileParserEmptyJSONArrayError(USDBIDFileParserError):
    """file content is an emty JSON array"""

    def __init__(self, detail: str | None = None):
        super().__init__("empty JSON array", detail)


class USDBIDFileParserNoJSONArrayError(USDBIDFileParserError):
    """file content is valid JSON, but not an array"""

    def __init__(self, detail: str | None = None):
        super().__init__("file does not contain a JSON array", detail)


class USDBIDFileParserInvalidUSDBIDError(USDBIDFileParserError):
    """expected USDB ID string cannot be converted correctly"""

    def __init__(self, detail: str | None = None):
        super().__init__("invalid USDB ID in file", detail)


class UnexpectedUSDBIDFileParserInvalidUSDBIDError(USDBIDFileParserInvalidUSDBIDError):
    """some unknown error around parsing an USDB ID string"""


class USDBIDFileParserNoURLFoundError(USDBIDFileParserError):
    """parser could not find an URL in file content"""

    def __init__(self, detail: str | None = None):
        super().__init__("no URL found", detail)


class USDBIDFileParserInvalidURLError(USDBIDFileParserError):
    """URL in file cannot be parsed properly"""


class USDBIDFileParser:
    """file parser for USDB IDs"""

    ids: list[SongId] = []
    errors: list[USDBIDFileParserError] = []

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.ids = []
        self.errors = []
        try:
            self.parse()
        except USDBIDFileParserError as exception:
            self.errors.append(exception)

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
            raise USDBIDFileParserUnsupportedExtensionError()

    def get_json_file_content(self) -> str:
        filecontent: str
        try:
            with open(self.filepath, "r", encoding="utf-8") as file:
                filecontent = file.read()
        except OSError as exception:
            raise USDBIDFileParserReadError() from exception
        except Exception as exception:
            raise UnexpectedUSDBIDFileParserError() from exception
        if not filecontent:
            raise USDBIDFileParserEmptyFileError()
        return filecontent

    def parse_json_file(self) -> None:
        filecontent = self.get_json_file_content()

        parsed_json = None
        try:
            parsed_json = json.loads(filecontent)
        except json.decoder.JSONDecodeError as exception:
            raise USDBIDFileParserInvalidJSONError() from exception
        except Exception as exception:
            raise UnexpectedUSDBIDFileParserError() from exception

        if not isinstance(parsed_json, list):
            raise USDBIDFileParserNoJSONArrayError()

        if not parsed_json:
            raise USDBIDFileParserEmptyJSONArrayError()

        key = "id"
        try:
            self.ids = [SongId(int(element[key])) for element in parsed_json]
        except ValueError as exception:
            raise USDBIDFileParserInvalidUSDBIDError() from exception
        except IndexError as exception:
            raise USDBIDFileParserInvalidFormatError(
                f"missing key '{key}'"
            ) from exception
        except Exception as exception:
            raise UnexpectedUSDBIDFileParserInvalidUSDBIDError() from exception

    def parse_ini_file(self, section: str, key: str) -> None:
        config = configparser.ConfigParser()
        try:
            config.read(self.filepath)
        except configparser.MissingSectionHeaderError as exception:
            raise USDBIDFileParserMissingSectionHeaderFormatError() from exception
        except Exception as exception:
            raise USDBIDFileParserMissingOrDublicateOptionFormatError() from exception
        if not config.sections():
            raise USDBIDFileParserEmptyFileError()
        if section not in config:
            raise USDBIDFileParserInvalidFormatError(f"missing section '{section}'")
        if key not in config[section]:
            raise USDBIDFileParserInvalidFormatError(f"missing key '{key}'")
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
            raise USDBIDFileParserReadError() from exception
        except Exception as exception:
            raise UnexpectedUSDBIDFileParserError() from exception

        if soup.is_empty_element:
            raise USDBIDFileParserEmptyFileError()
        tag = "plist"
        xml_plist = soup.find_all(tag)
        if not xml_plist:
            raise USDBIDFileParserInvalidFormatError(f"missing tag '{tag}'")
        if len(xml_plist) > 1:
            raise USDBIDFileParserInvalidFormatError(f"multiple tags '{tag}'")
        tag = "dict"
        xml_dict = xml_plist[0].find_all(tag)
        if not xml_dict:
            raise USDBIDFileParserInvalidFormatError(f"missing tag '{tag}'")
        if len(xml_dict) > 1:
            raise USDBIDFileParserInvalidFormatError(f"multiple tags '{tag}'")
        tag = "string"
        xml_string = xml_dict[0].find_all(tag)
        if not xml_string:
            raise USDBIDFileParserInvalidFormatError(f"missing URL tag '{tag}'")
        if len(xml_string) > 1:
            raise USDBIDFileParserMultipleURLsFormatError()

        url = xml_string[0].get_text()
        self.parse_url(url)

    def parse_usdb_ids_file(self) -> None:
        lines: list[str] = []
        try:
            with open(self.filepath, "r", encoding="utf-8") as file:
                lines = file.readlines()
        except OSError as exception:
            raise USDBIDFileParserReadError() from exception
        except Exception as exception:
            raise UnexpectedUSDBIDFileParserError() from exception

        if not lines:
            raise USDBIDFileParserEmptyFileError()

        try:
            self.ids = [SongId(int(line)) for line in lines]
        except ValueError as exception:
            raise USDBIDFileParserInvalidUSDBIDError() from exception
        except Exception as exception:
            raise UnexpectedUSDBIDFileParserInvalidUSDBIDError() from exception

    def parse_url(self, url: str | None) -> None:
        if not url:
            raise USDBIDFileParserNoURLFoundError()
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            raise USDBIDFileParserInvalidURLError(f"malformed URL: {url}")
        if parsed_url.netloc != "usdb.animux.de":
            raise USDBIDFileParserInvalidURLError(
                f"found URL has invalid domain: {parsed_url.netloc}"
            )
        if not parsed_url.query:
            raise USDBIDFileParserInvalidURLError(
                f"found URL has no query parameters: {url}"
            )
        query_params = parse_qs(parsed_url.query)
        id_param = "id"
        if id_param not in query_params:
            raise USDBIDFileParserInvalidURLError(
                f"missing '{id_param}' query parameter in found URL: {url}"
            )
        if len(query_params[id_param]) > 1:
            raise USDBIDFileParserInvalidURLError(
                f"repeated query parameter '{id_param}' in found URL: {url}"
            )
        try:
            self.ids = [SongId(int(query_params[id_param][0]))]
        except ValueError as exception:
            raise USDBIDFileParserInvalidURLError(
                f"invalid '{id_param}' query parameter in found URL: {url}"
            ) from exception
        except Exception as exception:
            # handle any other exception
            raise USDBIDFileParserInvalidURLError(
                f"could not parse '{id_param}' query parameter in '{url}': {exception}"
            ) from exception


def write_song_ids_to_file(path: str, song_ids: list[SongId]) -> None:
    with open(path, encoding="utf-8", mode="w") as file:
        file.write("\n".join([str(id) for id in song_ids]))
