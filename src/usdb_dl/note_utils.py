"""Functionality related to notes.txt file parsing."""

import logging
import os
import re
from typing import Dict, List, Tuple

_logger: logging.Logger = logging.getLogger(__file__)


def parse_notes(notes: str) -> Tuple[Dict[str, str], List[str]]:
    """Split notes string into interable header and body.

    Parameters:
        notes: note file string

    Returns:
        header and body of note file
    """
    header: Dict[str, str] = {}
    body: List[str] = []

    for line in notes.split("\n"):
        if line.startswith("#"):
            key, value = line.split(":", 1)
            # #AUTHOR should be #CREATOR
            if key == "#AUTHOR":
                key = "#CREATOR"
            # some quick fixes to improve song search in other databases
            if key in ["#ARTIST", "#TITLE", "#EDITION", "#GENRE"]:
                value = value.replace("´", "'")
                value = value.replace("`", "'")
                value = value.replace(" ft. ", " feat. ")
                value = value.replace(" ft ", " feat. ")
                value = value.replace(" feat ", " feat. ")
            header[key] = value.strip()
        else:
            body.append(line.replace("\r", "") + "\n")
    return header, body


def get_params_from_video_tag(header: Dict[str, str]) -> Dict[str, str]:
    """Optain additional resource parameter from overloaded video tag.

    Parameters:
        header: song meta data

    Returns:
        additional resource parameters
    """
    params = {}
    if params_line := header.get("#VIDEO"):
        params = dict(r.split("=") for r in params_line.split(","))
        if not params:
            logging.error("\t- no resources in #VIDEO tag")
    else:
        logging.error("\t- no #VIDEO tag present")
    return params


def is_duet(header: Dict[str, str], resource_params: Dict[str, str]) -> bool:
    """Check if song is duet.

    Parameters:
        header: song meta data
        resource_params: additional resource parameters from video tag

    Returns:
        True if song is duet
    """
    duet = bool(resource_params.get("p1") and resource_params.get("p2"))
    title = header["#TITLE"].lower()
    edition = header.get("#EDITION")
    edition = edition.lower() if edition else ""
    duet = "duet" in title or "duet" in edition or duet
    return duet


def generate_filename(header: Dict[str, str]) -> str:
    """Create file name from song meta data.

    Parameters:
        header: song meta data

    Returns:
        file name
    """
    artist = header["#ARTIST"]
    title = header["#TITLE"]
    # replace special characters
    replacements = [(r"\?|:|\"", ""), ("<", "("), (">", ")"), (r"\/|\\|\||\*", "-")]
    for replacement in replacements:
        artist = re.sub(replacement[0], replacement[1], artist).strip()
        title = re.sub(replacement[0], replacement[1], title).strip()
    return f"{artist} - {title}"


def generate_dirname(header: Dict[str, str], resource_params: Dict[str, str]) -> str:
    """Create directory name from song meta data.

    Parameters:
        header: song meta data
        resource_params: additional resource parameters from video tag

    Returns:
        directory name
    """
    dirname = generate_filename(header)
    if resource_params.get("v"):
        dirname += " [VIDEO]"
    if edition := header.get("#EDITION"):
        if "singstar" in edition.lower():
            dirname += " [SS]"
        if "[SC]" in edition:
            dirname += " [SC]"
        if "rock band" in edition.lower():
            dirname += " [RB]"
    return dirname


def dump_notes(
    header: Dict[str, str],
    body: List[str],
    pathname: str,
    duet: bool = False,
    encoding: str | None = None,
    newline: str | None = None,
) -> str:
    """Write notes to file.

    Parameters:
        header: song meta data
        body: song notes
        duet: add (duet) to file name
        encoding: file encoding
        newline: newline character

    Returns:
        file name
    """
    txt_filename = generate_filename(header)
    duetstring = " (duet)" if duet else ""
    filename = f"{txt_filename}{duetstring}.txt"
    _logger.debug("\t- writing text file with encoding %s", encoding)
    with open(
        os.path.join(pathname, filename), "w", encoding=encoding, newline=newline
    ) as notes_file:
        tags = [
            "#TITLE",
            "#ARTIST",
            "#LANGUAGE",
            "#EDITION",
            "#GENRE",
            "#YEAR",
            "#CREATOR",
            "#MP3",
            "#COVER",
            "#BACKGROUND",
            "#VIDEO",
            "#VIDEOGAP",
            "#START",
            "#END",
            "#PREVIEWSTART",
            "#BPM",
            "#GAP",
            "#RELATIVE",
            "#P1",
            "#P2",
        ]
        for tag in tags:
            if value := header.get(tag):
                notes_file.write(tag + ":" + value + "\n")
        for line in body:
            notes_file.write(line)
    return filename
