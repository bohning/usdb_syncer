"""Build a JSON file with all available songs from the local database."""

from usdb_syncer import db, song_routines, utils
from usdb_syncer.usdb_song import UsdbSong


def main() -> None:
    with db.managed_connection(utils.AppPaths.db):
        ids = db.search_usdb_songs(db.SearchBuilder())
        songs = [s for i in ids if (s := UsdbSong.get(i))]
    if songs:
        song_routines.dump_available_songs(songs, utils.AppPaths.song_list)
        print(f"{len(songs)} entries written to {utils.AppPaths.song_list}.")
    else:
        print("No songs found in database! Out file is unchanged.")


if __name__ == "__main__":
    main()
