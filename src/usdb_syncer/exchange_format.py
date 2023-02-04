"""Import and export lists of USDB IDs from file system."""

import logging
import re

from usdb_syncer import SongId


def get_song_ids_from_files(path: str) -> list[SongId]:
    logger = logging.getLogger(path)
    logger.info(path)

    with open(path, encoding="utf-8") as file:
        return [
            SongId(int(id))
            for id in [
                re.sub(
                    r"^.*https://usdb\.animux\.de/index\.php?.*id=(\d+).*$",
                    r"\1",
                    line.strip(),
                )
                for line in file.readlines()
            ]
            if re.match(r"^\d+$", id)
        ]
