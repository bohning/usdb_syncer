"""Import and export lists of USDB IDs from file system."""

import logging
import re

from usdb_syncer import SongId


def get_song_ids_from_files(path: str) -> list[SongId]:
    logger = logging.getLogger(path)
    logger.info(path)

    with open(path, encoding="utf-8") as file:
        return [
            SongId(int(first_column))
            for line in [
                re.sub(
                    r"^.*https://usdb\.animux\.de/index\.php?.*id=(\d+).*$",
                    r"\1",
                    raw_line.strip(),
                )
                for raw_line in file.readlines()
            ]
            # support possible csv separators ",", ";" and "\t"
            if re.match(
                r"^\d+$", first_column := re.sub(r"^(\d+)[;,\t].*$", r"\1", line)
            )
        ]


def write_song_ids_to_file(path: str, song_ids: list[SongId]) -> None:
    with open(path, encoding="utf-8", mode="w") as file:
        file.write("\n".join([str(id) for id in song_ids]))
