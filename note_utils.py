"""Functionality related to notes.txt file parsing."""

import logging
import re
import shlex
from typing import Dict, List, Tuple


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
    if not (params_line := header.get("#VIDEO")):
        raise LookupError("no video tag found in header.")
    lexer = shlex.shlex(params_line.strip(), posix=True)
    lexer.whitespace_split = True
    lexer.whitespace = ","
    try:
        params = dict(pair.split("=", 1) for pair in lexer)
    except ValueError as exception:
        raise LookupError("no parameter in video tag") from exception
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
        if "rockband" in edition.lower():
            dirname += " [RB]"
    return dirname


def dump_notes(
    header: Dict[str, str],
    body: List[str],
    duet: bool = False,
    encoding: str = None,
    newline: str = None,
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
    logging.info("writing text file with encodingr %s", encoding)
    with open(filename, "w", encoding=encoding, newline=newline) as notes_file:
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
