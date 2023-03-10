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


class USDBIDFileParserEmptyFileError(USDBIDFileParserError):
    """Files do not contain any USDB ID but were selected for import"""

    def __init__(self, detail: str | None = None):
        super().__init__("empty file", detail)


class USDBIDFileParser:
    """file parser for USDB IDs"""

    ids: list[SongId] = []
    errors: list[str] = []

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.ids = []
        self.errors = []
        try:
            self.parse()
        except USDBIDFileParserError as exception:
            self.errors.append(exception.message)

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
            raise USDBIDFileParserError("file extension is not supported")

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
            raise USDBIDFileParserError("invalid JSON format") from exception
        except Exception as exception:
            raise USDBIDFileParserError(
                "Unexpected error parsing file content"
            ) from exception

        if not isinstance(parsed_json, list):
            raise USDBIDFileParserError("file does not contain a JSON array")

        if not parsed_json:
            raise USDBIDFileParserError("empty JSON array")

        key = "id"
        try:
            self.ids = [SongId(int(element[key])) for element in parsed_json]
        except ValueError as exception:
            raise USDBIDFileParserError(
                "Invalid or missing USDB ID in file"
            ) from exception
        except IndexError as exception:
            raise USDBIDFileParserError(f"missing key '{key}'") from exception
        except Exception as exception:
            raise USDBIDFileParserError(
                "invalid or missing USDB ID in file"
            ) from exception

    def parse_ini_file(self, section: str, key: str) -> None:
        config = configparser.ConfigParser()
        try:
            config.read(self.filepath)
        except configparser.MissingSectionHeaderError as exception:
            raise USDBIDFileParserInvalidFormatError(
                "missing a section header"
            ) from exception
        except Exception as exception:
            raise USDBIDFileParserInvalidFormatError(
                "missing or dublicate option"
            ) from exception
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

        tag = "plist"
        xml_plist = soup.find_all(tag)
        if not xml_plist:
            raise USDBIDFileParserInvalidFormatError(f"missing tag '{tag}'")
        if len(xml_plist) > 1:
            raise USDBIDFileParserInvalidFormatError(f"multiple tag '{tag}'")
        tag = "dict"
        xml_dict = xml_plist[0].find_all(tag)
        if not xml_dict:
            raise USDBIDFileParserInvalidFormatError(f"missing tag '{tag}'")
        if len(xml_dict) > 1:
            raise USDBIDFileParserInvalidFormatError(f"multiple tag '{tag}'")
        tag = "string"
        xml_string = xml_dict[0].find_all(tag)
        if not xml_string:
            raise USDBIDFileParserInvalidFormatError(f"missing URL tag '{tag}'")
        if len(xml_string) > 1:
            raise USDBIDFileParserInvalidFormatError("multiple URLs detected")

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
            raise USDBIDFileParserError("invalid USDB ID in file") from exception
        except Exception as exception:
            raise USDBIDFileParserError("invalid USDB ID in file") from exception

    def parse_url(self, url: str | None) -> None:
        if not url:
            raise USDBIDFileParserError("no URL found")
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            raise USDBIDFileParserError(f"malformed URL: {url}")
        if parsed_url.netloc != "usdb.animux.de":
            raise USDBIDFileParserError(
                f"found URL has invalid domain: {parsed_url.netloc}"
            )
        if not parsed_url.query:
            raise USDBIDFileParserError(f"found URL has no query parameters: {url}")
        query_params = parse_qs(parsed_url.query)
        id_param = "id"
        if id_param not in query_params:
            raise USDBIDFileParserError(
                f"missing '{id_param}' query parameter in found URL: {url}"
            )
        if len(query_params[id_param]) > 1:
            raise USDBIDFileParserError(
                f"multiple '{id_param}' query parameter in found URL: {url}"
            )
        try:
            self.ids = [SongId(int(query_params[id_param][0]))]
        except ValueError as exception:
            raise USDBIDFileParserError(
                f"invalid '{id_param}' query parameter in found URL: {url}"
            ) from exception
        except Exception as exception:
            # handle any other exception
            raise USDBIDFileParserError(
                f"could not parse '{id_param}' query parameter in '{url}': {exception}"
            ) from exception


def write_song_ids_to_file(path: str, song_ids: list[SongId]) -> None:
    with open(path, encoding="utf-8", mode="w") as file:
        file.write("\n".join([str(id) for id in song_ids]))
