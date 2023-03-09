"""Import and export lists of USDB IDs from file system."""

import configparser
import json
import logging
import os
import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from usdb_syncer import SongId


class USDBIDFileParser:
    """file parser for USDB IDs"""

    ids: list[SongId] = []
    errors: list[str] = []

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.ids = []
        self.errors = []
        self.parse()

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
            self.errors.append(f"File extension is not supported: {file_extension}")

    def parse_json_file(self) -> None:
        filecontent: str
        try:
            with open(self.filepath, "r", encoding="utf-8") as file:
                filecontent = file.read()
        except OSError:
            self.errors.append(f"Failed to read file")
            return
        except Exception as exception:
            self.errors.append(f"Unexcpected error reading file: {exception}")
            return

        if not filecontent:
            self.errors.append("empty file")
            return

        parsed_json = None
        try:
            parsed_json = json.loads(filecontent)
        except json.decoder.JSONDecodeError as exception:
            self.errors.append(f"invalid JSON format: {exception}")
            return
        except Exception as exception:
            self.errors.append(f"Unexcpected error parsing file: {exception}")
            return

        if not isinstance(parsed_json, list):
            self.errors.append("File does not contain a JSON array")
            return

        if not parsed_json:
            self.errors.append("Empty JSON array")
            return

        key = "id"
        try:
            self.ids = [SongId(int(element[key])) for element in parsed_json]
        except ValueError as exception:
            self.errors.append("Invalid or missing USDB ID in file")
        except IndexError as exception:
            self.errors.append(f"Missing key '{key}': {exception}")
            return
        except Exception as exception:
            # handle any other exception
            self.errors.append("Invalid or missing USDB ID in file")

    def parse_ini_file(self, section: str, key: str) -> None:
        config = configparser.ConfigParser()
        try:
            config.read(self.filepath)
        except configparser.MissingSectionHeaderError:
            self.errors.append("invalid file format: missing a section header")
            return
        except Exception:
            self.errors.append(f"invalid file format: missing or dublicate option")
            return
        if section not in config:
            self.errors.append(f"invalid file format: missing section '{section}'")
            return
        if key not in config[section]:
            self.errors.append(f"invalid file format: missing key '{key}'")
            return
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
        except OSError:
            self.errors.append(f"Failed to read file")
            return
        except Exception as exception:
            self.errors.append(f"Unexcpected error reading file: {exception}")
            return

        tag = "plist"
        xml_plist = soup.find_all(tag)
        if not xml_plist:
            self.errors.append(f"invalid file format: missing tag '{tag}'")
            return
        if len(xml_plist) > 1:
            self.errors.append(f"invalid file format: multiple tag '{tag}'")
            return
        tag = "dict"
        xml_dict = xml_plist[0].find_all(tag)
        if not xml_dict:
            self.errors.append(f"invalid file format: missing tag '{tag}'")
            return
        if len(xml_dict) > 1:
            self.errors.append(f"invalid file format: multiple tag '{tag}'")
            return
        tag = "string"
        xml_string = xml_dict[0].find_all(tag)
        if not xml_string:
            self.errors.append(f"invalid file format: missing URL tag '{tag}'")
            return
        if len(xml_string) > 1:
            self.errors.append(f"invalid file format: multiple URLs detected")
            return

        url = xml_string[0].get_text()
        self.parse_url(url)

    def parse_usdb_ids_file(self) -> None:
        lines: list[str] = []
        try:
            with open(self.filepath, "r", encoding="utf-8") as file:
                lines = file.readlines()
        except OSError:
            self.errors.append(f"Failed to read file")
            return
        except Exception as exception:
            self.errors.append(f"Unexcpected error reading file: {exception}")
            return

        if not lines:
            self.errors.append("empty file")
            return

        try:
            self.ids = [SongId(int(line)) for line in lines]
        except ValueError as exception:
            self.errors.append("Invalid USDB ID in file")
        except Exception as exception:
            # handle any other exception
            self.errors.append("Invalid USDB ID in file")

    def parse_url(self, url: str | None) -> None:
        if not url:
            self.errors.append("No url found")
            return
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            self.errors.append(f"Malformed URL: {url}")
            return
        if parsed_url.netloc != "usdb.animux.de":
            self.errors.append(f"Found URL has invalid domain: {parsed_url.netloc}")
            return
        if not parsed_url.query:
            self.errors.append(f"Found URL has no query parameters: {url}")
            return
        query_params = parse_qs(parsed_url.query)
        id_param = "id"
        if id_param not in query_params:
            self.errors.append(
                f"Missing '{id_param}' query parameter in found URL: {url}"
            )
            return
        if len(query_params[id_param]) > 1:
            self.errors.append(
                f"Multiple '{id_param}' query parameter in found URL: {url}"
            )
            return
        try:
            self.ids = [SongId(int(query_params[id_param][0]))]
        except ValueError:
            self.errors.append(
                f"Invalid '{id_param}' query parameter in found URL: {url}"
            )
        except Exception as exception:
            # handle any other exception
            self.errors.append(
                f"Could not parse '{id_param}' query parameter in '{url}': {exception}"
            )


def write_song_ids_to_file(path: str, song_ids: list[SongId]) -> None:
    with open(path, encoding="utf-8", mode="w") as file:
        file.write("\n".join([str(id) for id in song_ids]))
