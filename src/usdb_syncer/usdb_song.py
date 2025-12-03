"""Meta data about a song that USDB shows in the result list."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from html import escape
from json import JSONEncoder
from pathlib import Path
from typing import Any, Callable, ClassVar

import attrs
from diff_match_patch import diff_match_patch

from usdb_syncer import SongId, db
from usdb_syncer.constants import UsdbStrings
from usdb_syncer.db import DownloadStatus
from usdb_syncer.logger import song_logger
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.sync_meta import SyncMeta


@attrs.define(kw_only=True)
class UsdbSong:
    """Meta data about a song that USDB shows in the result list."""

    song_id: SongId
    usdb_mtime: int
    artist: str
    title: str
    genre: str
    year: int | None = None
    language: str
    creator: str
    edition: str
    golden_notes: bool
    rating: int
    views: int
    sample_url: str
    # not in USDB song list
    tags: str = ""
    # internal
    sync_meta: SyncMeta | None = None
    status: DownloadStatus = DownloadStatus.NONE
    is_playing: bool = False

    @classmethod
    def from_json(cls, dct: dict[str, Any]) -> UsdbSong:
        dct["song_id"] = SongId(dct["song_id"])
        return cls(**dct)

    @classmethod
    def from_html(
        cls,
        strings: type[UsdbStrings],
        *,
        song_id: str,
        usdb_mtime: str,
        artist: str,
        title: str,
        genre: str,
        year: str,
        language: str,
        creator: str,
        edition: str,
        golden_notes: str,
        rating: str,
        views: str,
        sample_url: str,
    ) -> UsdbSong:
        return cls(
            song_id=SongId.parse(song_id),
            usdb_mtime=int(usdb_mtime),
            artist=artist,
            title=title,
            genre=genre,
            year=int(year) if len(year) == 4 and year.isdigit() else None,
            language=language,
            creator=creator,
            edition=edition,
            golden_notes=golden_notes == strings.YES,
            rating=rating.count("star.png"),
            views=int(views),
            sample_url=sample_url,
        )

    @classmethod
    def from_db_row(cls, song_id: SongId, row: tuple) -> UsdbSong:
        assert len(row) == 43
        return cls(
            song_id=song_id,
            usdb_mtime=row[1],
            artist=row[2],
            title=row[3],
            language=row[4],
            edition=row[5],
            golden_notes=bool(row[6]),  # else would be 0/1 instead of False/True
            rating=row[7],
            views=row[8],
            sample_url=row[9],
            year=row[10],
            genre=row[11],
            creator=row[12],
            tags=row[13],
            status=DownloadStatus(row[14]),
            is_playing=bool(row[15]),
            sync_meta=None if row[16] is None else SyncMeta.from_db_row(row[16:]),
        )

    @classmethod
    def get(cls, song_id: SongId) -> UsdbSong | None:
        if song := _UsdbSongCache.get(song_id):
            return song
        if row := db.get_usdb_song(song_id):
            song = UsdbSong.from_db_row(song_id, row)
            _UsdbSongCache.update(song)
            return song
        return None

    def delete(self) -> None:
        db.delete_usdb_song(self.song_id)
        _UsdbSongCache.remove(self.song_id)

    def remove_sync_meta(self) -> None:
        self.status = DownloadStatus.NONE
        if self.sync_meta:
            self.sync_meta.delete()
            self.sync_meta = None
            _UsdbSongCache.update(self)

    @classmethod
    def delete_all(cls) -> None:
        db.delete_all_usdb_songs()
        _UsdbSongCache.clear()

    def upsert(self) -> None:
        db.upsert_usdb_song(self.db_params())
        db.upsert_usdb_songs_languages([(self.song_id, self.languages())])
        db.upsert_usdb_songs_genres([(self.song_id, self.genres())])
        db.upsert_usdb_songs_creators([(self.song_id, self.creators())])
        if self.sync_meta:
            self.sync_meta.upsert()
        _UsdbSongCache.update(self)

    @classmethod
    def upsert_many(cls, songs: list[UsdbSong]) -> None:
        db.upsert_usdb_songs([song.db_params() for song in songs])
        db.upsert_usdb_songs_languages([(s.song_id, s.languages()) for s in songs])
        db.upsert_usdb_songs_genres([(s.song_id, s.genres()) for s in songs])
        db.upsert_usdb_songs_creators([(s.song_id, s.creators()) for s in songs])
        SyncMeta.upsert_many([song.sync_meta for song in songs if song.sync_meta])
        for song in songs:
            _UsdbSongCache.update(song)

    def db_params(self) -> db.UsdbSongParams:
        return db.UsdbSongParams(
            song_id=self.song_id,
            usdb_mtime=self.usdb_mtime,
            artist=self.artist,
            title=self.title,
            language=self.language,
            edition=self.edition,
            golden_notes=self.golden_notes,
            rating=self.rating,
            views=self.views,
            sample_url=self.sample_url,
            year=self.year,
            genre=self.genre,
            creator=self.creator,
            tags=self.tags,
        )

    def is_local(self) -> bool:
        return self.sync_meta is not None and self.sync_meta.path is not None

    def is_pinned(self) -> bool:
        return self.sync_meta is not None and self.sync_meta.pinned

    def languages(self) -> Iterable[str]:
        return (s for lang in self.language.split(",") if (s := lang.strip()))

    def genres(self) -> Iterable[str]:
        return (s for genre in self.genre.split(",") if (s := genre.strip()))

    def creators(self) -> Iterable[str]:
        return (s for creator in self.creator.split(",") if (s := creator.strip()))

    def txt_path(self) -> Path | None:
        if not self.sync_meta:
            return None
        return self.sync_meta.txt_path()

    def audio_path(self) -> Path | None:
        if not self.sync_meta:
            return None
        return self.sync_meta.audio_path()

    def video_path(self) -> Path | None:
        if not self.sync_meta:
            return None
        return self.sync_meta.video_path()

    def cover_path(self) -> Path | None:
        if not self.sync_meta:
            return None
        return self.sync_meta.cover_path()

    @classmethod
    def clear_cache(cls) -> None:
        _UsdbSongCache.clear()

    def is_new_since_last_update(self, last_update: db.LastUsdbUpdate) -> bool:
        return self.usdb_mtime > last_update.usdb_mtime or (
            self.usdb_mtime >= last_update.usdb_mtime
            and self.song_id not in last_update.song_ids
        )

    def get_resetted_status(self) -> DownloadStatus:
        if self.sync_meta:
            if self.sync_meta.usdb_mtime < self.usdb_mtime:
                status = DownloadStatus.OUTDATED
            else:
                status = DownloadStatus.SYNCHRONIZED
        else:
            status = DownloadStatus.NONE
        return status

    def set_status(self, status: DownloadStatus) -> None:
        if self.status != status:
            self.status = status
            db.set_usdb_song_status(self.song_id, status)
            _UsdbSongCache.update(self)

    def set_playing(self, is_playing: bool) -> None:
        if self.is_playing != is_playing:
            self.is_playing = is_playing
            db.set_usdb_song_playing(self.song_id, is_playing)
            _UsdbSongCache.update(self)

    def get_changes(self, remote_txt: SongTxt) -> SongChanges | None:
        """Analyze changes between local and remote versions of a song."""

        logger = song_logger(self.song_id)

        remote_str = remote_txt.str_for_upload()

        # Read local song file and get uploadable string
        if not (sync_meta := self.sync_meta):
            return None
        if not (txt_path := sync_meta.txt_path()):
            return None
        if not (txt_path.is_file()):
            return None
        if not (local_txt := SongTxt.try_from_file(txt_path, logger)):
            return None
        local_str = local_txt.str_for_upload(sync_meta.meta_tags, remote_txt.headers)

        diff_remote, diff_local, builder = generate_remote_vs_local_diffs(
            remote_str, local_str
        )

        return SongChanges(local_str, diff_remote, diff_local, builder)


def generate_remote_vs_local_diffs(
    remote: str, local: str
) -> tuple[str, str, _DiffLineBuilder]:
    """Generate a side-by-side HTML diff with per-character highlights.

    Returns:
        Tuple of (remote_html, local_html, builder)
    """

    dmp = diff_match_patch()
    diffs = dmp.diff_main(remote, local)
    dmp.diff_cleanupSemantic(diffs)

    def render_inline_diff(chunk: str, op: int) -> str:
        """Render inline character-level differences."""
        if not chunk:
            return ""
        text = escape(chunk).replace(" ", "&nbsp;")
        if op == -1:
            return f"<span class='del-inline'>{text}</span>"
        elif op == 1:
            return f"<span class='add-inline'>{text}</span>"
        return text

    builder = _DiffLineBuilder()

    for op, data in diffs:
        parts = data.split("\r\n")
        for i, part in enumerate(parts):
            builder.add_content(part, op, render_inline_diff)
            if i < len(parts) - 1:
                builder.flush_lines()

    builder.flush_lines()

    remote_html, local_html = builder.build_html()

    return remote_html, local_html, builder


@attrs.define
class _DiffLineBuilder:
    """Helper class to build diff HTML line by line."""

    remote_lines: list[str] = attrs.field(factory=list)
    local_lines: list[str] = attrs.field(factory=list)
    line_num_remote: int = 1
    line_num_local: int = 1
    left_line: str = ""
    right_line: str = ""
    left_has_change: bool = False
    right_has_change: bool = False
    changed_line_numbers: list[int] = attrs.field(factory=list)
    current_line_num: int = 1

    def add_content(
        self, part: str, op: int, renderer: Callable[[str, int], str]
    ) -> None:
        """Add content to current line buffers."""
        if op == 0:  # Equal
            self.left_line += renderer(part, 0)
            self.right_line += renderer(part, 0)
        elif op == -1:  # Deletion
            self.left_line += renderer(part, op)
            if part:
                self.left_has_change = True
                self.right_has_change = True
        elif op == 1:  # Addition
            self.right_line += renderer(part, op)
            if part:
                self.right_has_change = True
                self.left_has_change = True

    def flush_lines(self) -> None:
        """Output current line buffers to both sides."""
        if not self.left_line and not self.right_line:
            return

        if self.left_has_change or self.right_has_change:
            self.changed_line_numbers.append(self.current_line_num)

        self._add_left_line()
        self._add_right_line()
        self.current_line_num += 1
        self._reset_buffers()

    def get_changed_line_indices(self) -> list[int]:
        """Return list of line numbers that contain changes."""
        return self.changed_line_numbers

    def _add_left_line(self) -> None:
        """Add left side line or empty placeholder."""
        if self.left_line:
            line_class = "del" if self.left_has_change else "equal"
            self.remote_lines.append(
                f"<tr><td class='lineno'>{self.line_num_remote}</td>"
                f"<td class='line {line_class}'>{self.left_line}</td></tr>"
            )
            self.line_num_remote += 1
        elif self.right_line:
            self.remote_lines.append(
                "<tr><td class='lineno'>&nbsp;</td>"
                "<td class='line empty'>&nbsp;</td></tr>"
            )

    def _add_right_line(self) -> None:
        """Add right side line or empty placeholder."""
        if self.right_line:
            line_class = "add" if self.right_has_change else "equal"
            self.local_lines.append(
                f"<tr><td class='lineno'>{self.line_num_local}</td>"
                f"<td class='line {line_class}'>{self.right_line}</td></tr>"
            )
            self.line_num_local += 1
        elif self.left_line:
            self.local_lines.append(
                "<tr><td class='lineno'>&nbsp;</td>"
                "<td class='line empty'>&nbsp;</td></tr>"
            )

    def _reset_buffers(self) -> None:
        """Reset line buffers for next line."""
        self.left_line = ""
        self.right_line = ""
        self.left_has_change = False
        self.right_has_change = False

    def build_html(self) -> tuple[str, str]:
        """Build final HTML tables."""
        html_remote = (
            "<table class='diff-table'>" + "".join(self.remote_lines) + "</table>"
        )
        html_local = (
            "<table class='diff-table'>" + "".join(self.local_lines) + "</table>"
        )
        return html_remote, html_local

    def build_filtered_html(
        self, context_lines: int, changed_indices: list[int]
    ) -> tuple[str, str]:
        """Build HTML with only changed lines and context."""
        if not changed_indices:
            return self.build_html()

        lines_to_show = self._calculate_lines_with_context(
            context_lines, changed_indices
        )
        groups = self._group_consecutive_lines(lines_to_show)

        remote_filtered = self._build_filtered_lines(self.remote_lines, groups)
        local_filtered = self._build_filtered_lines(self.local_lines, groups)

        html_remote = (
            "<table class='diff-table'>" + "".join(remote_filtered) + "</table>"
        )
        html_local = "<table class='diff-table'>" + "".join(local_filtered) + "</table>"
        return html_remote, html_local

    def _calculate_lines_with_context(
        self, context_lines: int, changed_indices: list[int]
    ) -> set[int]:
        """Calculate which lines to show including context around changes."""
        lines_to_show = set()
        for changed_line in changed_indices:
            for offset in range(-context_lines, context_lines + 1):
                line_num = changed_line + offset
                if line_num > 0:
                    lines_to_show.add(line_num)
        return lines_to_show

    def _group_consecutive_lines(self, lines: set[int]) -> list[list[int]]:
        """Group consecutive line numbers together."""
        if not lines:
            return []

        sorted_lines = sorted(lines)
        groups = []
        current_group = [sorted_lines[0]]

        for line in sorted_lines[1:]:
            if line == current_group[-1] + 1:
                current_group.append(line)
            else:
                groups.append(current_group)
                current_group = [line]
        groups.append(current_group)
        return groups

    def _build_filtered_lines(
        self, all_lines: list[str], groups: list[list[int]]
    ) -> list[str]:
        """Build filtered line list with separators between groups."""
        filtered = []

        for group_idx, group in enumerate(groups):
            if group_idx > 0:
                filtered.append(self._create_separator())

            for line_num in group:
                idx = line_num - 1
                if idx < len(all_lines):
                    filtered.append(all_lines[idx])

        return filtered

    def _create_separator(self) -> str:
        """Create a separator row for skipped lines."""
        return (
            "<tr class='separator'>"
            "<td class='lineno'>⋮</td>"
            "<td class='line separator-line'>...</td>"
            "</tr>"
        )


@dataclass
class SongChanges:
    """Information about changes between local and remote versions."""

    uploadable_str: str
    diff_remote: str
    diff_local: str
    builder: _DiffLineBuilder

    def has_changes(self) -> bool:
        return self.diff_remote != self.diff_local


class UsdbSongEncoder(JSONEncoder):
    """Custom JSON encoder"""

    def default(self, o: Any) -> Any:
        if isinstance(o, UsdbSong):
            fields = attrs.fields(UsdbSong)
            filt = attrs.filters.exclude(
                fields.status, fields.sync_meta, fields.is_playing
            )
            dct = attrs.asdict(o, recurse=False, filter=filt)
            return dct
        return super().default(o)


class _UsdbSongCache:
    """Cache for songs loaded from the DB."""

    _songs: ClassVar[dict[SongId, UsdbSong]] = {}

    @classmethod
    def get(cls, song_id: SongId) -> UsdbSong | None:
        return cls._songs.get(song_id)

    @classmethod
    def update(cls, song: UsdbSong) -> None:
        cls._songs[song.song_id] = song

    @classmethod
    def remove(cls, song_id: SongId) -> None:
        if song_id in cls._songs:
            del cls._songs[song_id]

    @classmethod
    def clear(cls) -> None:
        cls._songs = {}
