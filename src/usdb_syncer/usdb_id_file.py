"""Import and export lists of USDB IDs from file system."""

from __future__ import annotations

import configparser
import json
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import attrs
import bs4
from bs4 import BeautifulSoup

from usdb_syncer import SongId, errors
from usdb_syncer.logger import logger
from usdb_syncer.usdb_song import UsdbSong


@attrs.define
class UsdbIdFileError(errors.UsdbSyncerError):
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
class UsdbIdFileEmptySongsArrayError(UsdbIdFileError):
    """songs array is empty"""

    songs_key: str

    def __str__(self) -> str:
        return f"'{self.songs_key}' is empty"


@attrs.define
class UsdbIdFileWrongJsonSongsFormatError(UsdbIdFileError):
    """songs value is not an array"""

    songs_key: str

    def __str__(self) -> str:
        return f"'{self.songs_key}' is not a JSON array"


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


def get_available_song_ids_from_files(file_list: list[Path]) -> list[SongId]:
    song_ids: list[SongId] = []
    for path in file_list:
        try:
            song_ids += parse_usdb_id_file(path)
        except UsdbIdFileError as error:
            logger.error(f"Failed to import file '{path}': {error!s}")
            return []

    unique_song_ids = list(set(song_ids))
    unique_song_ids.sort()
    logger.info(
        f"read {len(file_list)} file(s), "
        f"found {len(unique_song_ids)} "
        f"USDB IDs: {', '.join(str(id_) for id_ in unique_song_ids)}"
    )
    if unavailable_song_ids := [
        song_id for song_id in unique_song_ids if not UsdbSong.get(song_id)
    ]:
        logger.warning(
            f"{len(unavailable_song_ids)}/{len(unique_song_ids)} "
            "imported USDB IDs are not available: "
            f"{', '.join(str(song_id) for song_id in unavailable_song_ids)}"
        )

    if available_song_ids := [
        song_id for song_id in unique_song_ids if song_id not in unavailable_song_ids
    ]:
        logger.info(
            f"available {len(available_song_ids)}/{len(unique_song_ids)} "
            "imported USDB IDs will be selected: "
            f"{', '.join(str(song_id) for song_id in available_song_ids)}"
        )

    return available_song_ids


def _get_json_file_content(filepath: Path) -> str:
    filecontent: str
    try:
        with Path(filepath).open("r", encoding="utf-8") as file:
            filecontent = file.read()
    except OSError as exception:
        raise UsdbIdFileReadError() from exception
    except Exception as exception:
        raise UnexpectedUsdbIdFileError() from exception
    if not filecontent:
        raise UsdbIdFileEmptyFileError()
    return filecontent


def _parse_json_file(filepath: Path) -> list[SongId]:
    filecontent = _get_json_file_content(filepath)

    parsed_json = None
    try:
        parsed_json = json.loads(filecontent)
    except json.decoder.JSONDecodeError as exception:
        raise UsdbIdFileInvalidJsonError() from exception
    except Exception as exception:
        raise UnexpectedUsdbIdFileError() from exception

    if not isinstance(parsed_json, dict):
        raise UsdbIdFileInvalidJsonError()

    return _parse_json_content(parsed_json)


def _parse_json_content(parsed_json: dict) -> list[SongId]:
    top_key = "songs"

    if top_key not in parsed_json:
        raise UsdbIdFileMissingKeyFormatError(top_key)
    if not isinstance(parsed_json[top_key], list):
        raise UsdbIdFileWrongJsonSongsFormatError(songs_key=top_key)
    if not parsed_json[top_key]:
        raise UsdbIdFileEmptySongsArrayError(songs_key=top_key)

    key = "id"
    try:
        return [SongId.parse(element[key]) for element in parsed_json[top_key]]
    except ValueError as exception:
        raise UsdbIdFileInvalidUsdbIdError() from exception
    except (KeyError, IndexError) as exception:
        raise UsdbIdFileMissingKeyFormatError(exception.args[0]) from exception
    except Exception as exception:
        raise UnexpectedUsdbIdFileInvalidUsdbIdError() from exception


def _parse_ini_file(filepath: Path, section: str, key: str) -> SongId:
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


def _parse_url_file(filepath: Path) -> SongId:
    return _parse_ini_file(filepath, section="InternetShortcut", key="URL")


def _parse_desktop_file(filepath: Path) -> SongId:
    return _parse_ini_file(filepath, section="Desktop Entry", key="URL")


def _get_soup(filepath: Path) -> BeautifulSoup:
    try:
        with Path(filepath).open("r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, features="lxml-xml")
    except OSError as exception:
        raise UsdbIdFileReadError() from exception
    except Exception as exception:
        raise UnexpectedUsdbIdFileError() from exception

    if soup.is_empty_element:
        raise UsdbIdFileEmptyFileError()
    return soup


def _parse_webloc_file(filepath: Path) -> SongId:
    soup = _get_soup(filepath)
    tag = "plist"
    xml_plist = soup.find_all(tag)
    if not xml_plist or not isinstance(plist_tag := xml_plist[0], bs4.Tag):
        raise UsdbIdFileMissingTagFormatError(tag)
    if len(xml_plist) > 1:
        raise UsdbIdFileMultipleTagsFormatError(tag)
    tag = "dict"
    xml_dict = plist_tag.find_all(tag)
    if not xml_dict:
        raise UsdbIdFileMissingTagFormatError(tag)
    if len(xml_dict) > 1:
        raise UsdbIdFileMultipleTagsFormatError(tag)
    tag = "string"
    if not isinstance(dict_tag := xml_dict[0], bs4.Tag) or not (
        xml_string := dict_tag.find_all(tag)
    ):
        raise UsdbIdFileMissingUrlTagFormatError(tag)
    if len(xml_string) > 1:
        raise UsdbIdFileMultipleUrlsFormatError()

    url = xml_string[0].get_text()
    return _parse_url(url)


def _parse_usdb_ids_file(filepath: Path) -> list[SongId]:
    lines: list[str] = []
    try:
        with Path(filepath).open("r", encoding="utf-8") as file:
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


def parse_usdb_id_file(filepath: Path) -> list[SongId]:
    """parses files for USDB IDs"""
    song_ids: list[SongId] = []
    if filepath.suffix == ".json":
        song_ids = _parse_json_file(filepath)
    elif filepath.suffix == ".url":
        song_ids = [_parse_url_file(filepath)]
    elif filepath.suffix == ".desktop":
        song_ids = [_parse_desktop_file(filepath)]
    elif filepath.suffix == ".webloc":
        song_ids = [_parse_webloc_file(filepath)]
    elif filepath.suffix == ".usdb_ids":
        song_ids = _parse_usdb_ids_file(filepath)
    else:
        raise UsdbIdFileUnsupportedExtensionError()
    return song_ids


def write_usdb_id_file(filepath: Path, song_ids: Iterable[SongId]) -> None:
    with Path(filepath).open(encoding="utf-8", mode="w") as file:
        file.write("\n".join(str(id_) for id_ in song_ids))
