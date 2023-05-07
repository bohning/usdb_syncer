"""Import and export lists of USDB IDs from file system."""

from __future__ import annotations

import configparser
import json
import os
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

import attrs
from bs4 import BeautifulSoup

from usdb_syncer import SongId


@attrs.define
class UsdbIdFileError(Exception):
    """USDB File Parser root exception"""


@attrs.define
class UsdbIdFileUnsupportedExtensionError(UsdbIdFileError):
    """file extension is not supported for parsing"""

    def __str__(self) -> str:
        return "file extension is not supported"


@attrs.define
class UnexpectedUsdbIdFileError(UsdbIdFileError):
    """Unknown cause while reading file"""

    def __str__(self) -> str:
        return "Unexpected error reading file"


@attrs.define
class UsdbIdFileReadError(UsdbIdFileError):
    """Error reading file from file system"""

    def __str__(self) -> str:
        return "failed to read file"


@attrs.define
class UsdbIdFileInvalidFormatError(UsdbIdFileError):
    """Invalid file format"""

    def __str__(self) -> str:
        return "invalid file format"


@attrs.define
class UsdbIdFileMissingSectionHeaderFormatError(UsdbIdFileInvalidFormatError):
    """Invalid file format with missing section header"""

    def __str__(self) -> str:
        return f"{super().__str__()}: missing a section header"


@attrs.define
class UsdbIdFileMissingOrDuplicateOptionFormatError(UsdbIdFileInvalidFormatError):
    """Invalid file format with missing or duplicate option"""

    def __str__(self) -> str:
        return f"{super().__str__()}: missing or duplicate option"


@attrs.define
class UsdbIdFileMultipleUrlsFormatError(UsdbIdFileInvalidFormatError):
    """Invalid file format with multiple URLs"""

    def __str__(self) -> str:
        return f"{super().__str__()}: file contains multiple URLs"


@attrs.define
class UsdbIdFileMissingKeyFormatError(UsdbIdFileInvalidFormatError):
    """Invalid file format with missing key in file"""

    missing_key: str

    def __str__(self) -> str:
        return f"{super().__str__()}: missing key '{self.missing_key}'"


@attrs.define
class UsdbIdFileMissingSectionFormatError(UsdbIdFileInvalidFormatError):
    """Invalid file format with missing section in file"""

    missing_section: str

    def __str__(self) -> str:
        return f"{super().__str__()}: missing section '{self.missing_section}'"


@attrs.define
class UsdbIdFileMissingTagFormatError(UsdbIdFileInvalidFormatError):
    """Invalid file format with missing tag in file"""

    missing_tag: str

    def __str__(self) -> str:
        return f"{super().__str__()}: missing tag '{self.missing_tag}'"


@attrs.define
class UsdbIdFileMultipleTagsFormatError(UsdbIdFileInvalidFormatError):
    """Invalid file format with a tag occurring multiple times instead of just once"""

    multiple_tag: str

    def __str__(self) -> str:
        return f"{super().__str__()}: multiple tags '{self.multiple_tag}'"


@attrs.define
class UsdbIdFileMissingUrlTagFormatError(UsdbIdFileInvalidFormatError):
    """Invalid file format with missing tag for URL in file"""

    missing_tag: str

    def __str__(self) -> str:
        return f"{super().__str__()}: missing URL tag '{self.missing_tag}'"


@attrs.define
class UsdbIdFileMalformedUrlFormatError(UsdbIdFileInvalidFormatError):
    """Invalid file format with URL in bad format"""

    bad_url: str

    def __str__(self) -> str:
        return f"{super().__str__()}: malformed URL '{self.bad_url}'"


@attrs.define
class UsdbIdFileInvalidDomainMalformedUrlFormatError(UsdbIdFileMalformedUrlFormatError):
    """Invalid file format with URL containing bad domain"""

    bad_domain: str

    def __str__(self) -> str:
        return f"{super().__str__()}: has invalid domain '{self.bad_domain}'"


@attrs.define
class UsdbIdFileNoParametersMalformedUrlFormatError(UsdbIdFileMalformedUrlFormatError):
    """Invalid file format with URL having no query parameters"""

    def __str__(self) -> str:
        return f"{super().__str__()}: has no query parameters"


@attrs.define
class UsdbIdFileMissingQueryParameterMalformedUrlFormatError(
    UsdbIdFileMalformedUrlFormatError
):
    """Invalid file format with URL missing a specific query parameter"""

    missing_parameter: str

    def __str__(self) -> str:
        return (
            f"{super().__str__()}: missing query parameter '{self.missing_parameter}'"
        )


@attrs.define
class UsdbIdFileRepeatedQueryParameterMalformedUrlFormatError(
    UsdbIdFileMalformedUrlFormatError
):
    """Invalid file format with URL specific query parameter occurring multiple times"""

    repeated_parameter: str

    def __str__(self) -> str:
        return (
            f"{super().__str__()}: repeated query parameter '{self.repeated_parameter}'"
        )


@attrs.define
class UsdbIdFileInvalidQueryParameterMalformedUrlFormatError(
    UsdbIdFileMalformedUrlFormatError
):
    """Invalid file format with URL having an invalid query parameter"""

    invalid_parameter: str

    def __str__(self) -> str:
        return (
            f"{super().__str__()}: invalid query parameter '{self.invalid_parameter}'"
        )


@attrs.define
class UsdbIdFileUnparsableQueryParameterMalformedUrlFormatError(
    UsdbIdFileMalformedUrlFormatError
):
    """Invalid file format with URL having a query parameter that cannot be parsed"""

    unparsable_parameter: str

    def __str__(self) -> str:
        return (
            f"{super().__str__()}: could not parse query parameter "
            f"'{self.unparsable_parameter}'"
        )


@attrs.define
class UsdbIdFileEmptyFileError(UsdbIdFileError):
    """Files do not contain any USDB ID but were selected for import"""

    def __str__(self) -> str:
        return "empty file"


@attrs.define
class UsdbIdFileInvalidJsonError(UsdbIdFileError):
    """failed to interpret file content as JSON"""

    def __str__(self) -> str:
        return "invalid JSON format"


@attrs.define
class UsdbIdFileEmptyJsonArrayError(UsdbIdFileError):
    """file content is an emty JSON array"""

    def __str__(self) -> str:
        return "empty JSON array"


@attrs.define
class UsdbIdFileNoJsonArrayError(UsdbIdFileError):
    """file content is valid JSON, but not an array"""

    def __str__(self) -> str:
        return "file does not contain a JSON array"


@attrs.define
class UsdbIdFileInvalidUsdbIdError(UsdbIdFileError):
    """expected USDB ID string cannot be converted correctly"""

    def __str__(self) -> str:
        return "invalid USDB ID in file"


@attrs.define
class UnexpectedUsdbIdFileInvalidUsdbIdError(UsdbIdFileInvalidUsdbIdError):
    """some unknown error around parsing an USDB ID string"""

    def __str__(self) -> str:
        return "unexpected error when parsing USDB ID(s)"


@attrs.define
class UsdbIdFileNoUrlFoundError(UsdbIdFileError):
    """parser could not find an URL in file content"""

    def __str__(self) -> str:
        return "no URL found"


def _get_json_file_content(filepath: str) -> str:
    filecontent: str
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            filecontent = file.read()
    except OSError as exception:
        raise UsdbIdFileReadError() from exception
    except Exception as exception:
        raise UnexpectedUsdbIdFileError() from exception
    if not filecontent:
        raise UsdbIdFileEmptyFileError()
    return filecontent


def _parse_json_file(filepath: str) -> list[SongId]:
    filecontent = _get_json_file_content(filepath)

    parsed_json = None
    try:
        parsed_json = json.loads(filecontent)
    except json.decoder.JSONDecodeError as exception:
        raise UsdbIdFileInvalidJsonError() from exception
    except Exception as exception:
        raise UnexpectedUsdbIdFileError() from exception

    if not isinstance(parsed_json, list):
        raise UsdbIdFileNoJsonArrayError()

    if not parsed_json:
        raise UsdbIdFileEmptyJsonArrayError()

    key = "id"
    try:
        return [SongId.parse(element[key]) for element in parsed_json]
    except ValueError as exception:
        raise UsdbIdFileInvalidUsdbIdError() from exception
    except (KeyError, IndexError) as exception:
        raise UsdbIdFileMissingKeyFormatError(exception.args[0]) from exception
    except Exception as exception:
        raise UnexpectedUsdbIdFileInvalidUsdbIdError() from exception


def _parse_ini_file(filepath: str, section: str, key: str) -> SongId:
    config = configparser.ConfigParser()
    try:
        config.read(filepath)
    except configparser.MissingSectionHeaderError as exception:
        raise UsdbIdFileMissingSectionHeaderFormatError() from exception
    except Exception as exception:
        raise UsdbIdFileMissingOrDuplicateOptionFormatError() from exception
    if not config.sections():
        raise UsdbIdFileEmptyFileError()
    if section not in config:
        raise UsdbIdFileMissingSectionFormatError(section)
    if key not in config[section]:
        raise UsdbIdFileMissingKeyFormatError(key)
    url = config[section][key]
    return _parse_url(url)


def _parse_url_file(filepath: str) -> SongId:
    return _parse_ini_file(filepath, section="InternetShortcut", key="URL")


def _parse_desktop_file(filepath: str) -> SongId:
    return _parse_ini_file(filepath, section="Desktop Entry", key="URL")


def _get_soup(filepath: str) -> BeautifulSoup:
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, features="lxml-xml")
    except OSError as exception:
        raise UsdbIdFileReadError() from exception
    except Exception as exception:
        raise UnexpectedUsdbIdFileError() from exception

    if soup.is_empty_element:
        raise UsdbIdFileEmptyFileError()
    return soup


def _parse_webloc_file(filepath: str) -> SongId:
    soup = _get_soup(filepath)
    tag = "plist"
    xml_plist = soup.find_all(tag)
    if not xml_plist:
        raise UsdbIdFileMissingTagFormatError(tag)
    if len(xml_plist) > 1:
        raise UsdbIdFileMultipleTagsFormatError(tag)
    tag = "dict"
    xml_dict = xml_plist[0].find_all(tag)
    if not xml_dict:
        raise UsdbIdFileMissingTagFormatError(tag)
    if len(xml_dict) > 1:
        raise UsdbIdFileMultipleTagsFormatError(tag)
    tag = "string"
    xml_string = xml_dict[0].find_all(tag)
    if not xml_string:
        raise UsdbIdFileMissingUrlTagFormatError(tag)
    if len(xml_string) > 1:
        raise UsdbIdFileMultipleUrlsFormatError()

    url = xml_string[0].get_text()
    return _parse_url(url)


def _parse_usdb_ids_file(filepath: str) -> list[SongId]:
    lines: list[str] = []
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            lines = file.readlines()
    except OSError as exception:
        raise UsdbIdFileReadError() from exception
    except Exception as exception:
        raise UnexpectedUsdbIdFileError() from exception

    if not lines:
        raise UsdbIdFileEmptyFileError()

    try:
        return [SongId.parse(line) for line in lines]
    except ValueError as exception:
        raise UsdbIdFileInvalidUsdbIdError() from exception
    except Exception as exception:
        raise UnexpectedUsdbIdFileInvalidUsdbIdError() from exception


def _parse_url(url: str | None) -> SongId:
    if not url:
        raise UsdbIdFileNoUrlFoundError()
    parsed_url = urlparse(url)
    if not parsed_url.netloc:
        raise UsdbIdFileMalformedUrlFormatError(url)
    if parsed_url.netloc != "usdb.animux.de":
        raise UsdbIdFileInvalidDomainMalformedUrlFormatError(url, parsed_url.netloc)
    if not parsed_url.query:
        raise UsdbIdFileNoParametersMalformedUrlFormatError(url)
    query_params = parse_qs(parsed_url.query)
    id_param = "id"
    if id_param not in query_params:
        raise UsdbIdFileMissingQueryParameterMalformedUrlFormatError(url, id_param)
    if len(query_params[id_param]) > 1:
        raise UsdbIdFileRepeatedQueryParameterMalformedUrlFormatError(url, id_param)
    try:
        return SongId.parse(query_params[id_param][0])
    except ValueError as exception:
        raise UsdbIdFileInvalidQueryParameterMalformedUrlFormatError(
            url, id_param
        ) from exception
    except Exception as exception:
        # handle any other exception
        raise UsdbIdFileUnparsableQueryParameterMalformedUrlFormatError(
            url, id_param
        ) from exception


@dataclass
class UsdbIdFile:
    """file parser for USDB IDs"""

    ids: list[SongId] = field(default_factory=list)
    error: UsdbIdFileError | None = None

    @classmethod
    def parse(cls, filepath: str) -> UsdbIdFile:
        try:
            file_extension = os.path.splitext(filepath)[1]
            song_ids: list[SongId] = []
            if file_extension == ".json":
                song_ids = _parse_json_file(filepath)
            elif file_extension == ".url":
                song_ids = [_parse_url_file(filepath)]
            elif file_extension == ".desktop":
                song_ids = [_parse_desktop_file(filepath)]
            elif file_extension == ".webloc":
                song_ids = [_parse_webloc_file(filepath)]
            elif file_extension == ".usdb_ids":
                song_ids = _parse_usdb_ids_file(filepath)
            else:
                raise UsdbIdFileUnsupportedExtensionError()
            return cls(song_ids)
        except UsdbIdFileError as exception:
            return cls([], exception)

    def write(self, filepath: str) -> None:
        with open(filepath, encoding="utf-8", mode="w") as file:
            file.write("\n".join(str(id) for id in self.ids))