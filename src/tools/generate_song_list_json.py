"""Build a JSON file with all available songs from USDB."""

import argparse
import sys
from pathlib import Path

from requests import Session

from usdb_syncer import SongId, song_routines
from usdb_syncer.usdb_scraper import get_usdb_available_songs, login_to_usdb


def main(target: Path, user: str, password: str) -> None:
    session = Session()
    if not login_to_usdb(session, user, password):
        print("Invalid credentials!")
        sys.exit(1)
    songs = get_usdb_available_songs(SongId(0), session=session)
    song_routines.dump_available_songs(songs, target)
    print(f"{len(songs)} entries written to {target}.")


def cli_entry() -> None:
    parser = argparse.ArgumentParser(
        description="Fetches all songs from USDB and stores them in a JSON file."
    )
    parser.add_argument("--target", "-t", help="where to store the output file")
    parser.add_argument("--user", "-u", help="a USDB username")
    parser.add_argument("--password", "-p", help="the USDB user's password")
    args = parser.parse_args()
    main(Path(args.target), args.user, args.password)


if __name__ == "__main__":
    cli_entry()
