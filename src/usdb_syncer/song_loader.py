"""Contains a runnable song loader."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Iterable, Iterator

import attrs
import mutagen.mp4
from mutagen import id3
from PySide6.QtCore import QRunnable, QThreadPool

from usdb_syncer import SongId, resource_dl, usdb_scraper
from usdb_syncer.constants import ISO_639_2B_LANGUAGE_CODES
from usdb_syncer.download_options import Options, download_options
from usdb_syncer.logger import Log, get_logger
from usdb_syncer.meta_tags import MetaTags
from usdb_syncer.resource_dl import ImageKind, download_and_process_image
from usdb_syncer.song_data import (
    DownloadErrorReason,
    DownloadResult,
    DownloadStatus,
    LocalFiles,
    SongData,
)
from usdb_syncer.song_txt import Headers, SongTxt
from usdb_syncer.sync_meta import FileMeta, SyncMeta
from usdb_syncer.usdb_scraper import SongDetails, UsdbLoginError, UsdbNotFoundError
from usdb_syncer.usdb_song import UsdbSong
from usdb_syncer.utils import (
    is_name_maybe_with_suffix,
    next_unique_directory,
    resource_file_ending,
    sanitize_filename,
)


@attrs.define
class DownloadInfo:
    """Data required to start a song download."""

    song_id: SongId
    meta_path: Path | None

    @classmethod
    def from_song_data(cls, data: SongData) -> DownloadInfo:
        return cls(data.data.song_id, data.local_files.usdb_path)


@attrs.define(kw_only=True)
class Locations:
    """Paths for downloading a song."""

    meta_path: Path
    filename_stem: str

    @classmethod
    def new(
        cls, song_id: SongId, song_dir: Path, meta_path: Path | None, headers: Headers
    ) -> Locations:
        filename_stem = sanitize_filename(headers.artist_title_str())
        if not meta_path:
            dir_path = next_unique_directory(song_dir.joinpath(filename_stem))
            meta_path = dir_path.joinpath(f"{song_id}.usdb")
        return cls(meta_path=meta_path, filename_stem=filename_stem)

    def dir_path(self) -> Path:
        """The song directory."""
        return self.meta_path.parent

    def file_path(self, file: str = "", ext: str = "") -> Path:
        """Path to file in the song directory. The final path component is the generic
        name or the provided file, optionally with the provided extension.
        """
        name = file or self.filename_stem
        if ext:
            name = f"{name}.{ext}"
        return self.meta_path.with_name(name)

    def ensure_correct_paths(self, sync_meta: SyncMeta) -> None:
        """Ensure meta path and given resource paths match the generic filename."""
        if is_name_maybe_with_suffix(self.dir_path().name, self.filename_stem):
            return
        self._fix_meta_path()
        self._fix_resource_paths(sync_meta)

    def _fix_meta_path(self) -> None:
        new = next_unique_directory(self.dir_path().with_name(self.filename_stem))
        self.dir_path().rename(new)
        self.meta_path = new.joinpath(self.meta_path.name)

    def _fix_resource_paths(self, sync_meta: SyncMeta) -> None:
        for meta in sync_meta.file_metas():
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

    details: SongDetails
    options: Options
    txt: SongTxt
    locations: Locations
    sync_meta: SyncMeta
    logger: Log

    @classmethod
    def new(
        cls, details: SongDetails, options: Options, info: DownloadInfo, logger: Log
    ) -> Context:
        txt_str = usdb_scraper.get_notes(details.song_id, logger)
        txt = SongTxt.parse(txt_str, logger)
        txt.sanitize()
        txt.headers.creator = txt.headers.creator or details.uploader or None
        paths = Locations.new(
            details.song_id, options.song_dir, info.meta_path, txt.headers
        )
        sync_meta = _load_sync_meta(paths.meta_path, details.song_id, txt.meta_tags)
        return cls(details, options, txt, paths, sync_meta, logger)

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
            url = self.txt.meta_tags.cover.source_url()
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
            url = self.txt.meta_tags.background.source_url()
            self.logger.debug(f"downloading background from #VIDEO params: {url}")
        return url

    def usdb_song(self) -> UsdbSong:
        return UsdbSong(
            song_id=self.sync_meta.song_id,
            artist=self.details.artist,
            title=self.details.title,
            language=self.txt.headers.language or "",
            edition=self.txt.headers.edition or "",
            golden_notes=self.details.golden_notes,
            rating=self.details.rating,
            views=self.details.views,
        )

    def finished_song_data(self) -> SongData:
        return SongData.from_usdb_song(
            self.usdb_song(),
            LocalFiles.from_sync_meta(self.locations.meta_path, self.sync_meta),
            DownloadStatus.DONE,
        )


def _load_sync_meta(path: Path, song_id: SongId, meta_tags: MetaTags) -> SyncMeta:
    """Loads meta from path if valid or creates a new one."""
    if path.exists() and (meta := SyncMeta.try_from_file(path)):
        return meta
    return SyncMeta.new(song_id, meta_tags)


class SongLoader(QRunnable):
    """Runnable to create a complete song folder."""

    def __init__(
        self,
        info: DownloadInfo,
        options: Options,
        on_start: Callable[[SongId], None],
        on_finish: Callable[[DownloadResult], None],
    ) -> None:
        super().__init__()
        self.song_id = info.song_id
        self.data = info
        self.options = options
        self.on_start = on_start
        self.on_finish = on_finish
        self.logger = get_logger(__file__, info.song_id)

    def run(self) -> None:
        result = DownloadResult(self.song_id)
        try:
            result.data = self._run_inner()
        except UsdbLoginError:
            self.logger.error("Aborted; download requires login.")
            result.error = DownloadErrorReason.NOT_LOGGED_IN
        except UsdbNotFoundError:
            self.logger.error("Song seems to have been deleted from USDB.")
            result.error = DownloadErrorReason.NOT_FOUND
        except Exception as exception:  # pylint: disable=broad-except
            self.logger.debug(exception)
            self.logger.error(
                "Failed to finish download due to an unexpected error. "
                "See debug log for more information."
            )
            result.error = DownloadErrorReason.UNKNOWN
        self.on_finish(result)

    def _run_inner(self) -> SongData:
        self.on_start(self.song_id)
        details = usdb_scraper.get_usdb_details(self.song_id)
        self.logger.info(f"Found '{details.artist} - {details.title}' on USDB")
        ctx = Context.new(details, self.options, self.data, self.logger)
        ctx.locations.dir_path().mkdir(parents=True, exist_ok=True)
        ctx.locations.ensure_correct_paths(ctx.sync_meta)
        _maybe_download_audio(ctx)
        _maybe_download_video(ctx)
        _maybe_download_cover(ctx)
        _maybe_download_background(ctx)
        _maybe_write_txt(ctx)
        _maybe_write_audio_tags(ctx)
        _write_sync_meta(ctx)
        return ctx.finished_song_data()


def download_songs(
    infos: Iterable[DownloadInfo],
    on_start: Callable[[SongId], None],
    on_finish: Callable[[DownloadResult], None],
) -> None:
    options = download_options()
    threadpool = QThreadPool.globalInstance()
    for info in infos:
        worker = SongLoader(info, options, on_start, on_finish)
        threadpool.start(worker)


def _maybe_download_audio(ctx: Context) -> None:
    if not (options := ctx.options.audio_options):
        return
    meta = ctx.sync_meta.synced_audio(ctx.locations.dir_path())
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
    meta = ctx.sync_meta.synced_video(ctx.locations.dir_path())
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
    if ctx.sync_meta.meta_tags.cover == ctx.txt.meta_tags.cover:
        if meta := ctx.sync_meta.synced_cover(ctx.locations.dir_path()):
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
    if ctx.sync_meta.meta_tags.background == ctx.txt.meta_tags.background:
        if meta := ctx.sync_meta.synced_background(ctx.locations.dir_path()):
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


def _write_sync_meta(ctx: Context) -> None:
    ctx.sync_meta.to_file(ctx.locations.dir_path())


def _maybe_write_audio_tags(ctx: Context) -> None:
    if not (options := ctx.options.audio_options) or not (meta := ctx.sync_meta.audio):
        return

    audiofile = ctx.locations.file_path(meta.fname)

    match audiofile.suffix:
        case ".m4a":
            _write_m4a_tags(meta, ctx, options.embed_artwork)
        case ".mp3":
            _write_mp3_tags(meta, ctx, options.embed_artwork)

    ctx.sync_meta.audio.bump_mtime(ctx.locations.dir_path())


def _write_m4a_tags(audio_meta: FileMeta, ctx: Context, embed_artwork: bool) -> None:
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


def _write_mp3_tags(audio_meta: FileMeta, ctx: Context, embed_artwork: bool) -> None:
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
