"""Contains a runnable song loader."""

from __future__ import annotations

import base64
import copy
import os
import traceback
from pathlib import Path
from typing import Iterable, Iterator

import attrs
import mutagen.mp4
import mutagen.oggvorbis
from mutagen import id3
from mutagen.flac import Picture
from PIL import Image
from PySide6.QtCore import QRunnable, QThreadPool

from usdb_syncer import SongId, errors, events, resource_dl, usdb_scraper
from usdb_syncer.constants import ISO_639_2B_LANGUAGE_CODES
from usdb_syncer.download_options import Options, download_options
from usdb_syncer.logger import Log, get_logger
from usdb_syncer.resource_dl import ImageKind, download_and_process_image
from usdb_syncer.song_txt import Headers, SongTxt
from usdb_syncer.sync_meta import ResourceFile, SyncMeta
from usdb_syncer.usdb_scraper import SongDetails

# from usdb_syncer.db.models import LocalSong, ResourceFile, UsdbSong
from usdb_syncer.usdb_song import DownloadStatus, UsdbSong
from usdb_syncer.utils import (
    is_name_maybe_with_suffix,
    next_unique_directory,
    resource_file_ending,
    sanitize_filename,
)


@attrs.define(kw_only=True)
class Locations:
    """Paths for downloading a song."""

    folder: Path
    filename_stem: str

    @classmethod
    def new(cls, song: UsdbSong, song_dir: Path, headers: Headers) -> Locations:
        filename_stem = sanitize_filename(headers.artist_title_str())
        if song.sync_meta:
            folder = song.sync_meta.path.parent
        else:
            folder = next_unique_directory(song_dir.joinpath(filename_stem))
        return cls(folder=folder, filename_stem=filename_stem)

    def file_path(self, file: str = "", ext: str = "") -> Path:
        """Path to file in the song directory. The final path component is the generic
        name or the provided file, optionally with the provided extension.
        """
        name = file or self.filename_stem
        if ext:
            name = f"{name}.{ext}"
        return self.folder.joinpath(name)

    def ensure_correct_paths(self, sync_meta: SyncMeta) -> None:
        """Ensure meta path and given resource paths match the generic filename."""
        if is_name_maybe_with_suffix(self.folder.name, self.filename_stem):
            return
        self._rename_folder()
        self._update_sync_meta_paths(sync_meta)

    def _rename_folder(self) -> None:
        new = next_unique_directory(self.folder.with_name(self.filename_stem))
        self.folder.rename(new)
        self.folder = new

    def _update_sync_meta_paths(self, sync_meta: SyncMeta) -> None:
        sync_meta.path = self.file_path(file=sync_meta.path.name)
        for meta in sync_meta.resource_files():
            old_path = self.file_path(file=meta.fname)
            new_path = self.file_path(
                file=self.filename_stem + resource_file_ending(meta.fname)
            )
            if old_path == new_path or new_path.exists() or not old_path.exists():
                continue
            old_path.rename(new_path)
            meta.fname = new_path.name


@attrs.define
class Context:
    """Context for downloading media and creating a song folder."""

    # deep copy of the passed in song
    song: UsdbSong
    # alias to song.sync_meta
    sync_meta: SyncMeta
    details: SongDetails
    options: Options
    txt: SongTxt
    locations: Locations
    logger: Log

    @classmethod
    def new(cls, song: UsdbSong, options: Options, logger: Log) -> Context:
        song = copy.deepcopy(song)
        details, txt = _get_usdb_data(song.song_id, logger)
        _update_song_with_usdb_data(song, details, txt)
        paths = Locations.new(song, options.song_dir, txt.headers)
        if not song.sync_meta:
            song.sync_meta = SyncMeta.new(song.song_id, paths.folder, txt.meta_tags)
        return cls(song, song.sync_meta, details, options, txt, paths, logger)

    def all_audio_resources(self) -> Iterator[str]:
        if self.txt.meta_tags.audio:
            yield self.txt.meta_tags.audio
        if not self.txt.meta_tags.video:
            self.logger.debug("No valid audio/video meta tag. Looking in comments.")
        yield from self.all_video_resources()

    def all_video_resources(self) -> Iterator[str]:
        if self.txt.meta_tags.video:
            yield self.txt.meta_tags.video
        yield from self.details.all_comment_videos()

    def cover_url(self) -> str | None:
        url = None
        if self.txt.meta_tags.cover:
            url = self.txt.meta_tags.cover.source_url(self.logger)
            self.logger.debug(f"downloading cover from #VIDEO params: {url}")
        elif self.details.cover_url:
            url = self.details.cover_url
            self.logger.warning(
                "no cover resource in #VIDEO tag, so fallback to small usdb cover!"
            )
        return url

    def background_url(self) -> str | None:
        url = None
        if self.txt.meta_tags.background:
            url = self.txt.meta_tags.background.source_url(self.logger)
            self.logger.debug(f"downloading background from #VIDEO params: {url}")
        return url


def _get_usdb_data(song_id: SongId, logger: Log) -> tuple[SongDetails, SongTxt]:
    details = usdb_scraper.get_usdb_details(song_id)
    logger.info(f"Found '{details.artist} - {details.title}' on USDB.")
    txt_str = usdb_scraper.get_notes(details.song_id, logger)
    txt = SongTxt.parse(txt_str, logger)
    txt.sanitize()
    txt.headers.creator = txt.headers.creator or details.uploader or None
    return details, txt


def _update_song_with_usdb_data(
    song: UsdbSong, details: SongDetails, txt: SongTxt
) -> None:
    song.artist = details.artist
    song.title = details.title
    song.language = txt.headers.language or ""
    song.edition = txt.headers.edition or ""
    song.golden_notes = details.golden_notes
    song.rating = details.rating
    song.views = details.views


class SongLoader(QRunnable):
    """Runnable to create a complete song folder."""

    def __init__(self, song: UsdbSong, options: Options) -> None:
        super().__init__()
        self.song = song
        self.song_id = song.song_id
        self.options = options
        self.logger = get_logger(__file__, self.song_id)

    def run(self) -> None:
        change_event: events.SubscriptableEvent = events.SongChanged(self.song_id)
        try:
            updated_song = self._run_inner()
        except errors.UsdbLoginError:
            self.logger.error("Aborted; download requires login.")
            self.song.status = DownloadStatus.FAILED
        except errors.UsdbNotFoundError:
            self.logger.error("Song has been deleted from USDB.")
            self.song.delete(commit=True)
            change_event = events.SongDeleted(self.song_id)
        except Exception:  # pylint: disable=broad-except
            self.logger.debug(traceback.format_exc())
            self.logger.error(
                "Failed to finish download due to an unexpected error. "
                "See debug log for more information."
            )
            self.song.status = DownloadStatus.FAILED
        else:
            updated_song.status = DownloadStatus.NONE
            updated_song.upsert(commit=True)
            self.logger.info("All done!")
        change_event.post()
        events.DownloadFinished(self.song_id).post()

    def _run_inner(self) -> UsdbSong:
        self.song.status = DownloadStatus.DOWNLOADING
        events.SongChanged(self.song_id).post()
        ctx = Context.new(self.song, self.options, self.logger)
        ctx.locations.folder.mkdir(parents=True, exist_ok=True)
        ctx.locations.ensure_correct_paths(ctx.sync_meta)
        _maybe_download_audio(ctx)
        _maybe_download_video(ctx)
        _maybe_download_cover(ctx)
        _maybe_download_background(ctx)
        _maybe_write_txt(ctx)
        _maybe_write_audio_tags(ctx)
        ctx.sync_meta.synchronize_to_file()
        return ctx.song


def download_songs(songs: Iterable[UsdbSong]) -> None:
    options = download_options()
    threadpool = QThreadPool.globalInstance()
    for song in songs:
        worker = SongLoader(song, options)
        threadpool.start(worker)


def _maybe_download_audio(ctx: Context) -> None:
    if not (options := ctx.options.audio_options):
        return
    meta = ctx.sync_meta.synced_audio(ctx.locations.folder)
    for idx, resource in enumerate(ctx.all_audio_resources()):
        if meta and meta.resource == resource:
            ctx.txt.headers.mp3 = meta.fname
            ctx.logger.info("Audio resource is unchanged.")
            return
        if idx > 9:
            break
        if ext := resource_dl.download_audio(
            resource,
            options,
            ctx.options.browser,
            ctx.locations.file_path(),
            ctx.logger,
        ):
            path = ctx.locations.file_path(ext=ext)
            ctx.sync_meta.set_audio_meta(path, resource)
            ctx.txt.headers.mp3 = os.path.basename(path)
            ctx.logger.info("Success! Downloaded audio.")

            return

    ctx.logger.error(
        f"Failed to download audio (song duration > {ctx.txt.minimum_song_length()})!"
    )


def _maybe_download_video(ctx: Context) -> None:
    if not (options := ctx.options.video_options) or ctx.txt.meta_tags.is_audio_only():
        return
    meta = ctx.sync_meta.synced_video(ctx.locations.folder)
    for idx, resource in enumerate(ctx.all_video_resources()):
        if meta and meta.resource == resource:
            ctx.txt.headers.video = meta.fname
            ctx.logger.info("Video resource is unchanged.")
            return
        if idx > 9:
            break
        if ext := resource_dl.download_video(
            resource,
            options,
            ctx.options.browser,
            ctx.locations.file_path(),
            ctx.logger,
        ):
            path = ctx.locations.file_path(ext=ext)
            ctx.sync_meta.set_video_meta(path, resource)
            ctx.txt.headers.video = os.path.basename(path)
            ctx.logger.info("Success! Downloaded video.")
            return
    ctx.logger.error("Failed to download video!")


def _maybe_download_cover(ctx: Context) -> None:
    if not ctx.options.cover:
        return
    if not (url := ctx.cover_url()):
        ctx.logger.warning("No cover resource found.")
        return
    meta = ctx.sync_meta.synced_cover(ctx.locations.folder)
    if meta and meta.resource == url:
        ctx.txt.headers.cover = meta.fname
        ctx.logger.info("Cover resource is unchanged.")
        return
    if path := download_and_process_image(
        url,
        ctx.locations.file_path(),
        ctx.txt.meta_tags.cover,
        ctx.details,
        ImageKind.COVER,
        max_width=ctx.options.cover.max_size,
    ):
        ctx.txt.headers.cover = path.name
        ctx.sync_meta.set_cover_meta(path, url)
        ctx.logger.info("Success! Downloaded cover.")
    else:
        ctx.logger.error("Failed to download cover!")


def _maybe_download_background(ctx: Context) -> None:
    if not (options := ctx.options.background_options):
        return
    if not options.download_background(bool(ctx.txt.headers.video)):
        return
    if not (url := ctx.background_url()):
        ctx.logger.warning("No background resource found.")
        return
    meta = ctx.sync_meta.synced_background(ctx.locations.folder)
    if meta and meta.resource == url:
        ctx.txt.headers.background = meta.fname
        ctx.logger.info("Background resource is unchanged.")
        return
    if path := download_and_process_image(
        url,
        ctx.locations.file_path(),
        ctx.txt.meta_tags.background,
        ctx.details,
        ImageKind.BACKGROUND,
        max_width=None,
    ):
        ctx.txt.headers.background = path.name
        ctx.sync_meta.set_background_meta(path, url)
        ctx.logger.info("Success! Downloaded background.")
    else:
        ctx.logger.error("Failed to download background!")


def _maybe_write_txt(ctx: Context) -> None:
    if not (options := ctx.options.txt_options):
        return
    path = ctx.locations.file_path(ext="txt")
    ctx.txt.write_to_file(path, options.encoding.value, options.newline.value)
    ctx.sync_meta.set_txt_meta(path)
    ctx.logger.info("Success! Created song txt.")


def _maybe_write_audio_tags(ctx: Context) -> None:
    if not (options := ctx.options.audio_options) or not (meta := ctx.sync_meta.audio):
        return

    audiofile = ctx.locations.file_path(meta.fname)

    try:
        match audiofile.suffix:
            case ".m4a":
                _write_m4a_tags(meta, ctx, options.embed_artwork)
            case ".mp3":
                _write_mp3_tags(meta, ctx, options.embed_artwork)
            case ".ogg":
                _write_ogg_tags(meta, ctx, options.embed_artwork)
    except Exception:  # pylint: disable=broad-exception-caught
        ctx.logger.debug(traceback.format_exc())
        ctx.logger.error(f"Failed to write audio tags to file '{meta.fname}'!")
    else:
        ctx.logger.debug(f"Audio tags written to file '{meta.fname}'.")

    ctx.sync_meta.audio.bump_mtime(ctx.locations.folder)


def _write_m4a_tags(
    audio_meta: ResourceFile, ctx: Context, embed_artwork: bool
) -> None:
    tags = mutagen.mp4.MP4Tags()

    tags["\xa9ART"] = ctx.txt.headers.artist
    tags["\xa9nam"] = ctx.txt.headers.title
    if ctx.txt.headers.genre:
        tags["\xa9gen"] = ctx.txt.headers.genre
    if ctx.txt.headers.year:
        tags["\xa9day"] = ctx.txt.headers.year
    tags["\xa9lyr"] = ctx.txt.unsynchronized_lyrics()
    tags["\xa9cmt"] = audio_meta.resource

    if embed_artwork:
        tags["covr"] = [
            mutagen.mp4.MP4Cover(
                ctx.locations.file_path(image.fname).read_bytes(),
                imageformat=mutagen.mp4.MP4Cover.FORMAT_JPEG,
            )
            for image in (ctx.sync_meta.cover, ctx.sync_meta.background)
            if image
        ]

    tags.save(ctx.locations.file_path(audio_meta.fname))


def _write_mp3_tags(
    audio_meta: ResourceFile, ctx: Context, embed_artwork: bool
) -> None:
    tags = id3.ID3()

    lang = ISO_639_2B_LANGUAGE_CODES.get(ctx.txt.headers.main_language(), "und")
    tags["TPE1"] = id3.TPE1(encoding=id3.Encoding.UTF8, text=ctx.txt.headers.artist)
    tags["TIT2"] = id3.TIT2(encoding=id3.Encoding.UTF8, text=ctx.txt.headers.title)
    tags["TLAN"] = id3.TLAN(encoding=id3.Encoding.UTF8, text=lang)
    if genre := ctx.txt.headers.genre:
        tags["TCON"] = id3.TCON(encoding=id3.Encoding.UTF8, text=genre)
    if year := ctx.txt.headers.year:
        tags["TDRC"] = id3.TDRC(encoding=id3.Encoding.UTF8, text=year)
    tags[f"USLT::'{lang}'"] = id3.USLT(
        encoding=id3.Encoding.UTF8,
        lang=lang,
        desc="Lyrics",
        text=ctx.txt.unsynchronized_lyrics(),
    )
    tags["SYLT"] = id3.SYLT(
        encoding=id3.Encoding.UTF8,
        lang=lang,
        format=2,  # milliseconds as units
        type=1,  # lyrics
        text=ctx.txt.synchronized_lyrics(),
    )
    tags["COMM"] = id3.COMM(
        encoding=id3.Encoding.UTF8,
        lang="eng",
        desc="Audio Source",
        text=audio_meta.resource,
    )

    if embed_artwork and ctx.sync_meta.cover:
        tags.add(
            id3.APIC(
                encoding=id3.Encoding.UTF8,
                mime="image/jpeg",
                type=id3.PictureType.COVER_FRONT,
                desc=f"Source: {ctx.sync_meta.cover.resource}",
                data=ctx.locations.file_path(ctx.sync_meta.cover.fname).read_bytes(),
            )
        )

    tags.save(ctx.locations.file_path(audio_meta.fname))


def _write_ogg_tags(
    audio_meta: ResourceFile, ctx: Context, embed_artwork: bool
) -> None:
    audio = mutagen.oggvorbis.OggVorbis(ctx.locations.file_path(audio_meta.fname))

    # Set basic tags
    audio["artist"] = ctx.txt.headers.artist
    audio["title"] = ctx.txt.headers.title
    lang = ISO_639_2B_LANGUAGE_CODES.get(ctx.txt.headers.main_language(), "und")
    audio["language"] = lang
    if genre := ctx.txt.headers.genre:
        audio["genre"] = genre
    if year := ctx.txt.headers.year:
        audio["date"] = year
    audio["lyrics"] = ctx.txt.unsynchronized_lyrics()

    if embed_artwork and ctx.sync_meta.cover:
        with open(ctx.locations.file_path(ctx.sync_meta.cover.fname), "rb") as cover:
            data = cover.read()
        with Image.open(ctx.locations.file_path(ctx.sync_meta.cover.fname)) as cover:
            width, height = cover.size

        picture = Picture()
        picture.data = data
        picture.type = 3  # "Cover (front)"
        picture.desc = "Cover art"
        picture.mime = "image/jpeg"
        picture.width = width
        picture.height = height
        picture.depth = 24

        picture_data = picture.write()
        encoded_data = base64.b64encode(picture_data)
        vcomment_value = encoded_data.decode("ascii")

        audio["metadata_block_picture"] = [vcomment_value]

    audio.save()
