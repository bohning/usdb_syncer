"""Build a JSON file with all available songs from USDB."""

import argparse
import sys
from pathlib import Path

from usdb_syncer import settings, song_list_fetcher
from usdb_syncer.usdb_scraper import create_session, login_to_usdb


def main(target: Path, user: str, password: str) -> None:
    session = create_session(settings.Browser.NONE)
    if not login_to_usdb(session, user, password):
        print("Invalid credentials!")
        sys.exit(1)
    songs = song_list_fetcher.get_available_songs(force_reload=True, session=session)
    song_list_fetcher.dump_available_songs(songs, target)
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
