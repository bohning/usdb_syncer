from pathlib import Path
from usdb_syncer import db
from usdb_syncer.db import SearchBuilder, find_similar_usdb_songs
from usdb_syncer.meta_tags import MetaTags
from usdb_syncer.song_routines import try_parse_txt_headers
from usdb_syncer.song_txt import Headers
from usdb_syncer.sync_meta import SyncMeta, ResourceFile
from usdb_syncer.usdb_song import UsdbSong
from usdb_syncer.utils import normalize as _normalize, AppPaths
import argparse
import logging


def normalize(text: str):
    text = _normalize(text)
    text = text.replace('&', '&amp;')
    return text


def sync_meta_from_textfile(text_file: Path, song: UsdbSong, headers: Headers | None = None):
    if not headers:
        headers = try_parse_txt_headers(text_file)
    if not headers:
        logger.error(f"Could not parse headers from {text_file}.")
        return
    folder = text_file.parent
    sync_meta = SyncMeta.new(song_id=song.song_id, usdb_mtime=song.usdb_mtime, folder=folder, meta_tags=MetaTags())
    # txt resource
    sync_meta.txt = ResourceFile.new(path=text_file, resource=song.song_id.usdb_gettxt_url())
    # audio resource
    audio = headers.audio or headers.mp3
    if audio and Path(folder / audio).exists():
        res = headers.audiourl or ''
        sync_meta.audio = ResourceFile.new(path=folder / audio, resource=res)
    for resName in ('background', 'cover', 'video'):
        res = headers.__getattribute__(resName)
        if res and Path(folder / res).exists():
            res_url = headers.__getattribute__(resName + 'url') or ''
            sync_meta.__setattr__(resName, ResourceFile.new(path=folder / res, resource=res_url))
    return sync_meta


def main(search_folder: Path):
    db.connect(AppPaths.db)
    text_files = search_folder.glob("**/*.txt")
    for textFile in text_files:
        has_usdb_file = any(textFile.parent.glob("*.usdb"))
        if has_usdb_file:
            logger.debug(f"Skipping {textFile.stem} because a .usdb file already exists.")
            continue
        headers = try_parse_txt_headers(textFile)
        if not headers:
            logger.error(f"Could not parse {textFile.stem}. Skipping.")
            continue
        # get the USDB song corresponding to the txt file from the database
        search = SearchBuilder(
            titles=[normalize(headers.title)],
            artists=[normalize(headers.artist)],
            creators=[normalize(headers.creator)]
        ) if headers.creator else SearchBuilder(
            titles=[normalize(headers.title)],
            artists=[normalize(headers.artist)]
        )
        song_ids = list(db.search_usdb_songs(search))
        if not song_ids:
            # this is a fallback for song titles containing [DUET], which is removed by the header parser
            song_ids = list(find_similar_usdb_songs(artist=normalize(headers.artist), title=normalize(headers.title)))
        if not song_ids:
            logger.warning(f"No USDB song found for {headers.artist} - {headers.title}. Skipping.")
            continue
        if len(song_ids) > 1:
            logger.warning(f"Multiple USDB songs found for {headers.artist} - {headers.title}. Skipping.")
            continue
        song = UsdbSong.get(song_ids[0])
        if not song:
            logger.error(f"Could not load USDB song with ID {song_ids[0]} for {textFile.name}. Skipping.")
            continue
        if song.sync_meta:
            logger.info(f"Sync meta for {textFile.stem} already exists. Writing .usdb file.")
            song.sync_meta.synchronize_to_file()
            continue
        # we found the matching song and can start writing the sync meta
        song.sync_meta = sync_meta_from_textfile(text_file=textFile, song=song, headers=headers)
        if not song.sync_meta:
            logger.error(f"Could not create sync meta for {textFile.stem}. Skipping.")
            continue
        song.sync_meta.synchronize_to_file()
        logger.info(f"Successfully matched {textFile.stem} and created sync meta.")


def parse_args():
    parser = argparse.ArgumentParser(description="Match local song folders with USDB database entries and "
                                                 "create synchronization files.")
    parser.add_argument("path", type=str, help="Path to the song folder.")
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set the logging level (default: INFO).")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()))
    logger = logging.getLogger("usdb_matcher")
    main(Path(args.path))
