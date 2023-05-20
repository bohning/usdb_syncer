"""pyside-related wrapper for pyside-independent usdb_id_file module"""

from usdb_syncer import SongId
from usdb_syncer.logger import Log

from .gui.song_table.song_table import SongTable
from .usdb_id_file import UsdbIdFileError, parse_usdb_id_file


def get_available_song_ids_from_files(
    file_list: list[str], song_table: SongTable, logger: Log
) -> list[SongId]:
    song_ids: list[SongId] = []
    has_error = False
    for path in file_list:
        try:
            song_ids += parse_usdb_id_file(path)
        except UsdbIdFileError as error:
            logger.error(f"failed importing file {path}: {str(error)}")
            has_error = True

    # stop import if encounter errors
    if has_error:
        return []

    unique_song_ids = list(set(song_ids))
    unique_song_ids.sort()
    logger.info(
        f"read {len(file_list)} file(s), "
        f"found {len(unique_song_ids)} "
        f"USDB IDs: {', '.join(str(id) for id in unique_song_ids)}"
    )
    if unavailable_song_ids := [
        song_id for song_id in unique_song_ids if not song_table.get_data(song_id)
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
            "imported USDB IDs are added to Batch: "
            f"{', '.join(str(song_id) for song_id in available_song_ids)}"
        )

    return available_song_ids
