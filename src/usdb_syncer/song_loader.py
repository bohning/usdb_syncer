"""Contains a runnable song loader."""

from __future__ import annotations

import base64
import copy
import tempfile
import traceback
from pathlib import Path
from typing import Iterable, Iterator

import attrs
import mutagen.mp4
import mutagen.oggvorbis
import send2trash
from mutagen import id3
from mutagen.flac import Picture
from PIL import Image
from PySide6.QtCore import QRunnable, QThreadPool

from usdb_syncer import SongId, db, errors, events, resource_dl, usdb_scraper
from usdb_syncer.constants import ISO_639_2B_LANGUAGE_CODES
from usdb_syncer.download_options import Options, download_options
from usdb_syncer.logger import Log, get_logger
from usdb_syncer.resource_dl import ImageKind, download_and_process_image
from usdb_syncer.song_txt import Headers, SongTxt
from usdb_syncer.sync_meta import SyncMeta
from usdb_syncer.usdb_scraper import SongDetails
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
    tempdir: Path

    @classmethod
    def new(
        cls, song: UsdbSong, song_dir: Path, headers: Headers, tempdir: Path
    ) -> Locations:
        filename_stem = sanitize_filename(headers.artist_title_str())
        if song.sync_meta:
            folder = song.sync_meta.path.parent
        else:
            folder = next_unique_directory(song_dir.joinpath(filename_stem))
        return cls(folder=folder, filename_stem=filename_stem, tempdir=tempdir)

    def filename_with_ending(self, filename: str) -> str:
        """Path to file in the final song folder with the ending of the given file."""
        return self.filename_stem + resource_file_ending(filename)

    def file_path(self, filename: str) -> Path:
        """Path to file in the final song folder."""
        return self.folder.joinpath(filename)

    def temp_path(self, file: str = "", ext: str = "") -> Path:
        """Path to file in the temporary download directory. The final path component is
        the generic name or the provided file, optionally with the provided extension.
        """
        name = file or self.filename_stem
        if ext:
            name = f"{name}.{ext}"
        return self.tempdir.joinpath(name)

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
        sync_meta.path = self.file_path(sync_meta.path.name)
        for meta in sync_meta.resource_files():
            old_path = self.file_path(meta.fname)
            new_path = self.file_path(self.filename_with_ending(meta.fname))
            if old_path == new_path or new_path.exists() or not old_path.exists():
                continue
            old_path.rename(new_path)
            meta.fname = new_path.name


@attrs.define
class TempResourceFile:
    """Interim resource file in the temporary folder."""

    path: Path
    resource: str
    kind: db.ResourceFileKind


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
    temp_resources: list[TempResourceFile] = attrs.field(factory=list)

    @classmethod
    def new(
        cls, song: UsdbSong, options: Options, tempdir: Path, logger: Log
    ) -> Context:
        song = copy.deepcopy(song)
        details, txt = _get_usdb_data(song.song_id, logger)
        _update_song_with_usdb_data(song, details, txt)
        paths = Locations.new(song, options.song_dir, txt.headers, tempdir)
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

    def temp_resource(self, kind: db.ResourceFileKind) -> TempResourceFile | None:
        return next((res for res in self.temp_resources if res.kind == kind), None)

    def cover_resource(self) -> TempResourceFile | None:
        """Return the new cover resource, or the existing one as a fallback."""
        kind = db.ResourceFileKind.COVER
        if resource := self.temp_resource(kind):
            return resource
        if cover := self.sync_meta.cover:
            return TempResourceFile(
                self.locations.file_path(cover.fname), cover.resource, kind
            )
        return None

    def background_resource(self) -> TempResourceFile | None:
        """Return the new background resource, or the existing one as a fallback."""
        kind = db.ResourceFileKind.BACKGROUND
        if resource := self.temp_resource(kind):
            return resource
        if background := self.sync_meta.background:
            return TempResourceFile(
                self.locations.file_path(background.fname), background.resource, kind
            )
        return None


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
            with db.transaction():
                self.song.delete()
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
            with db.transaction():
                updated_song.upsert()
            self.logger.info("All done!")
        change_event.post()
        events.DownloadFinished(self.song_id).post()

    def _run_inner(self) -> UsdbSong:
        self.song.status = DownloadStatus.DOWNLOADING
        events.SongChanged(self.song_id).post()
        with tempfile.TemporaryDirectory() as tempdir:
            ctx = Context.new(self.song, self.options, Path(tempdir), self.logger)
            _maybe_download_audio(ctx)
            _maybe_download_video(ctx)
            _maybe_download_cover(ctx)
            _maybe_download_background(ctx)
            _maybe_write_txt(ctx)
            _maybe_write_audio_tags(ctx)
            ctx.locations.folder.mkdir(parents=True, exist_ok=True)
            ctx.locations.ensure_correct_paths(ctx.sync_meta)
            _persist_tempfiles(ctx)
            _synchronize_sync_meta(ctx)
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
    kind = db.ResourceFileKind.AUDIO
    meta = ctx.sync_meta.synced_resource(ctx.locations.folder, kind)
    for idx, resource in enumerate(ctx.all_audio_resources()):
        if meta and meta.resource == resource:
            ctx.txt.headers.mp3 = ctx.locations.filename_with_ending(meta.fname)
            ctx.logger.info("Audio resource is unchanged.")
            return
        if idx > 9:
            break
        if ext := resource_dl.download_audio(
            resource,
            options,
            ctx.options.browser,
            ctx.locations.temp_path(),
            ctx.logger,
        ):
            path = ctx.locations.temp_path(ext=ext)
            ctx.temp_resources.append(TempResourceFile(path, resource, kind))
            ctx.txt.headers.mp3 = path.name
            ctx.logger.info("Success! Downloaded audio.")
            return
    ctx.logger.error(
        f"Failed to download audio (song duration > {ctx.txt.minimum_song_length()})!"
    )


def _maybe_download_video(ctx: Context) -> None:
    if not (options := ctx.options.video_options) or ctx.txt.meta_tags.is_audio_only():
        return
    kind = db.ResourceFileKind.VIDEO
    meta = ctx.sync_meta.synced_resource(ctx.locations.folder, kind)
    for idx, resource in enumerate(ctx.all_video_resources()):
        if meta and meta.resource == resource:
            ctx.txt.headers.video = ctx.locations.filename_with_ending(meta.fname)
            ctx.logger.info("Video resource is unchanged.")
            return
        if idx > 9:
            break
        if ext := resource_dl.download_video(
            resource,
            options,
            ctx.options.browser,
            ctx.locations.temp_path(),
            ctx.logger,
        ):
            path = ctx.locations.temp_path(ext=ext)
            ctx.temp_resources.append(TempResourceFile(path, resource, kind))
            ctx.txt.headers.video = path.name
            ctx.logger.info("Success! Downloaded video.")
            return
    ctx.logger.error("Failed to download video!")


def _maybe_download_cover(ctx: Context) -> None:
    if not ctx.options.cover:
        return
    if not (url := ctx.cover_url()):
        ctx.logger.warning("No cover resource found.")
        return
    kind = db.ResourceFileKind.COVER
    meta = ctx.sync_meta.synced_resource(ctx.locations.folder, kind)
    if meta and meta.resource == url:
        ctx.txt.headers.cover = ctx.locations.filename_with_ending(meta.fname)
        ctx.logger.info("Cover resource is unchanged.")
        return
    if path := download_and_process_image(
        url,
        ctx.locations.temp_path(),
        ctx.txt.meta_tags.cover,
        ctx.details,
        ImageKind.COVER,
        max_width=ctx.options.cover.max_size,
    ):
        ctx.txt.headers.cover = path.name
        ctx.temp_resources.append(TempResourceFile(path, url, kind))
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
    kind = db.ResourceFileKind.BACKGROUND
    meta = ctx.sync_meta.synced_resource(ctx.locations.folder, kind)
    if meta and meta.resource == url:
        ctx.txt.headers.background = ctx.locations.filename_with_ending(meta.fname)
        ctx.logger.info("Background resource is unchanged.")
        return
    if path := download_and_process_image(
        url,
        ctx.locations.temp_path(),
        ctx.txt.meta_tags.background,
        ctx.details,
        ImageKind.BACKGROUND,
        max_width=None,
    ):
        ctx.txt.headers.background = path.name
        ctx.temp_resources.append(TempResourceFile(path, url, kind))
        ctx.logger.info("Success! Downloaded background.")
    else:
        ctx.logger.error("Failed to download background!")


def _maybe_write_txt(ctx: Context) -> None:
    if not (options := ctx.options.txt_options):
        return
    path = ctx.locations.temp_path(ext="txt")
    ctx.txt.write_to_file(path, options.encoding.value, options.newline.value)
    ctx.temp_resources.append(
        TempResourceFile(path, ctx.song.song_id.usdb_url(), db.ResourceFileKind.TXT)
    )
    ctx.logger.info("Success! Created song txt.")


def _maybe_write_audio_tags(ctx: Context) -> None:
    if not (options := ctx.options.audio_options):
        return
    if not (meta := ctx.temp_resource(db.ResourceFileKind.AUDIO)):
        return
    try:
        match meta.path:
            case ".m4a":
                _write_m4a_tags(meta, ctx, options.embed_artwork)
            case ".mp3":
                _write_mp3_tags(meta, ctx, options.embed_artwork)
            case ".ogg":
                _write_ogg_tags(meta, ctx, options.embed_artwork)
    except Exception:  # pylint: disable=broad-exception-caught
        ctx.logger.debug(traceback.format_exc())
        ctx.logger.error(f"Failed to write audio tags to file '{meta.path}'!")
    else:
        ctx.logger.debug(f"Audio tags written to file '{meta.path}'.")


def _write_m4a_tags(
    audio_meta: TempResourceFile, ctx: Context, embed_artwork: bool
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
                image.path.read_bytes(), imageformat=mutagen.mp4.MP4Cover.FORMAT_JPEG
            )
            for image in (ctx.cover_resource(), ctx.background_resource())
            if image
        ]

    tags.save(audio_meta.path)


def _write_mp3_tags(
    audio_meta: TempResourceFile, ctx: Context, embed_artwork: bool
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

    if embed_artwork and (cover := ctx.cover_resource()):
        tags.add(
            id3.APIC(
                encoding=id3.Encoding.UTF8,
                mime="image/jpeg",
                type=id3.PictureType.COVER_FRONT,
                desc=f"Source: {cover.resource}",
                data=cover.path.read_bytes(),
            )
        )

    tags.save(audio_meta.path)


def _write_ogg_tags(
    audio_meta: TempResourceFile, ctx: Context, embed_artwork: bool
) -> None:
    audio = mutagen.oggvorbis.OggVorbis(audio_meta.path)

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

    if embed_artwork and (cover := ctx.cover_resource()):
        picture = Picture()
        with cover.path.open("rb") as file:
            picture.data = file.read()
        with Image.open(cover.path) as image:
            picture.width, picture.height = image.size
        picture.type = 3  # "Cover (front)"
        picture.desc = "Cover art"
        picture.mime = "image/jpeg"
        picture.depth = 24

        picture_data = picture.write()
        encoded_data = base64.b64encode(picture_data)
        vcomment_value = encoded_data.decode("ascii")

        audio["metadata_block_picture"] = [vcomment_value]

    audio.save()


def _persist_tempfiles(ctx: Context) -> None:
    ctx.locations.folder.mkdir(parents=True, exist_ok=True)
    for resource in ctx.temp_resources:
        target = ctx.locations.file_path(resource.path.name)
        if target.exists():
            send2trash.send2trash(target)
            ctx.logger.debug(f"Trashed existing file: '{target}'.")
        resource.path.rename(target)
        resource.path = target


def _synchronize_sync_meta(ctx: Context) -> None:
    for res in ctx.temp_resources:
        ctx.sync_meta.set_resource_meta(res.path, res.resource, res.kind)
    ctx.sync_meta.synchronize_to_file()
