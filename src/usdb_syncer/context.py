"""Context for downloading and postprocessing media and creating a song folder."""

from __future__ import annotations

import copy
from collections.abc import Iterator
from pathlib import Path

import attrs

from usdb_syncer import SongId, download_options, usdb_scraper, utils
from usdb_syncer.discord import UsdbSong
from usdb_syncer.logger import Log
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.sync_meta import ResourceFile, SyncMeta
from usdb_syncer.usdb_scraper import SongDetails


@attrs.define(kw_only=True)
class _Locations:
    """Paths for downloading a song."""

    _current: Path | None
    # includes filename stem
    _target: Path
    _tempdir: Path

    @classmethod
    def new(
        cls, song: UsdbSong, options: download_options.Options, tempdir: Path
    ) -> _Locations:
        target = options.path_template.evaluate(song, options.song_dir)
        if (
            _current := song.sync_meta.path.parent if song.sync_meta else None
        ) and utils.path_matches_maybe_with_suffix(_current, target.parent):
            target = _current / target.name
        else:
            target = utils.next_unique_directory(target.parent) / target.name
        return cls(current=_current, target=target, tempdir=tempdir)  # pyright: ignore

    def current_path(self, file: str = "", ext: str = "") -> Path | None:
        """Path to file in the current download directory if it exists.
        The final path component is the generic name or the provided file, optionally
        with the provided extension joined with a '.' unless one is already present.
        """
        return self._path(self._current, file, ext) if self._current else None

    def temp_path(self, file: str = "", ext: str = "") -> Path:
        """Path to file in the temporary download directory.
        The final path component is the generic name or the provided file, optionally
        with the provided extension joined with a '.' unless one is already present.
        """
        return self._path(self._tempdir, file, ext)

    def target_path(self, file: str = "", ext: str = "") -> Path:
        """Path to file in the final download directory.
        The final path component is the generic name or the provided file, optionally
        with the provided extension joined with a '.' unless one is already present.
        """
        return self._path(self._target.parent, file, ext)

    def _path(self, parent: Path, file: str = "", ext: str = "") -> Path:
        name = file or self._target.name
        if ext:
            name = f"{name}{'' if '.' in ext else '.'}{ext}"
        return parent.joinpath(name)

    def filename(self, ext: str = "") -> str:
        if ext:
            return f"{self._target.name}{'' if '.' in ext else '.'}{ext}"
        return self._target.name

    def move_to_target_folder(self) -> None:
        """Rename the path of the song folder if it does not match the template, and
        ensure the target directory exists.
        """
        if self._current and self._current != self._target:
            self._target.parent.parent.mkdir(parents=True, exist_ok=True)
            self._current.rename(self._target.parent)
            self._current = self._target.parent
        else:
            self._target.parent.mkdir(parents=True, exist_ok=True)


@attrs.define
class _TempResourceFile:
    """Interim resource file in the temporary folder, or in the old folder if the
    resource is potentially kept.
    """

    old_fname: str | None = None
    new_fname: str | None = None
    resource: str | None = None

    def path_and_resource(
        self, locations: _Locations, temp: bool
    ) -> tuple[Path, str] | None:
        if (path := self.path(locations, temp=temp)) and self.resource:
            return (path, self.resource)
        return None

    def path(self, locations: _Locations, temp: bool) -> Path | None:
        if self.new_fname:
            if temp:
                return locations.temp_path(self.new_fname)
            return locations.target_path(self.new_fname)
        if self.old_fname:
            return locations.current_path(self.old_fname)
        return None

    def to_resource_file(
        self, locations: _Locations, temp: bool
    ) -> ResourceFile | None:
        if path_resource := self.path_and_resource(locations, temp=temp):
            return ResourceFile.new(*path_resource)
        return None


@attrs.define
class _TempResourceFiles:
    """Collection of all temporary resource files."""

    txt: _TempResourceFile = attrs.field(factory=_TempResourceFile)
    audio: _TempResourceFile = attrs.field(factory=_TempResourceFile)
    video: _TempResourceFile = attrs.field(factory=_TempResourceFile)
    cover: _TempResourceFile = attrs.field(factory=_TempResourceFile)
    background: _TempResourceFile = attrs.field(factory=_TempResourceFile)

    def __iter__(self) -> Iterator[_TempResourceFile]:
        return iter((self.txt, self.audio, self.video, self.cover, self.background))


@attrs.define
class Context:
    """_Context for downloading media and creating a song folder."""

    # deep copy of the passed in song
    song: UsdbSong
    details: SongDetails
    options: download_options.Options
    txt: SongTxt
    locations: _Locations
    logger: Log
    out: _TempResourceFiles = attrs.field(factory=_TempResourceFiles)

    def __attrs_post_init__(self) -> None:
        # reuse old resource files unless we acquire new ones later on
        # txt is always rewritten
        if self.song.sync_meta and (current := self.locations.current_path()):
            for old, out in (
                (self.song.sync_meta.audio, self.out.audio),
                (self.song.sync_meta.video, self.out.video),
                (self.song.sync_meta.cover, self.out.cover),
                (self.song.sync_meta.background, self.out.background),
            ):
                if old and old.is_in_sync(current.parent):
                    out.resource = old.resource
                    out.old_fname = old.fname

    @classmethod
    def new(
        cls, song: UsdbSong, options: download_options.Options, tempdir: Path, log: Log
    ) -> Context:
        song = copy.deepcopy(song)
        details, txt = _get_usdb_data(song.song_id, options.txt_options, log)
        _update_song_with_usdb_data(song, details, txt)
        paths = _Locations.new(song, options, tempdir)
        if not song.sync_meta:
            song.sync_meta = SyncMeta.new(
                song.song_id, paths.target_path().parent, txt.meta_tags
            )
        return cls(song, details, options, txt, paths, log)

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

    def background_url(self) -> str | None:
        url = None
        if self.txt.meta_tags.background:
            url = self.txt.meta_tags.background.source_url(self.logger)
            self.logger.debug(f"downloading background from #VIDEO params: {url}")
        return url


def _get_usdb_data(
    song_id: SongId, txt_options: download_options.TxtOptions | None, log: Log
) -> tuple[SongDetails, SongTxt]:
    details = usdb_scraper.get_usdb_details(song_id)
    log.info(f"Found '{details.artist} - {details.title}' on USDB.")
    txt_str = usdb_scraper.get_notes(details.song_id, log)
    txt = SongTxt.parse(txt_str, log)
    txt.sanitize(txt_options)
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
    if txt.headers.year and len(txt.headers.year) == 4 and txt.headers.year.isdigit():
        song.year = int(txt.headers.year)
    else:
        song.year = None
    song.genre = txt.headers.genre or ""
    song.creator = txt.headers.creator or ""
