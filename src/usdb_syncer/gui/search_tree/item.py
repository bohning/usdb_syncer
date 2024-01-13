"""Representations of rows of the filter tree."""

from __future__ import annotations

import enum
from functools import cache
from typing import Any, Iterable, assert_never

import attrs
from PySide6.QtGui import QIcon

from usdb_syncer import db


class SongMatch:
    """Interface for objects that can be matched against a song."""

    def build_search(self, search: db.SearchBuilder) -> None:
        raise NotImplementedError


@attrs.define
class SongValueMatch(SongMatch):
    """str that can be matched against a specific attribute of a song."""

    val: str
    count: int

    def __str__(self) -> str:
        return f"{self.val} [{self.count}]"

    def build_search(self, search: db.SearchBuilder) -> None:
        raise NotImplementedError


class SongArtistMatch(SongValueMatch):
    """str that can be matched against a song's artist."""

    def build_search(self, search: db.SearchBuilder) -> None:
        search.artists.append(self.val)


class SongTitleMatch(SongValueMatch):
    """str that can be matched against a song's title."""

    def build_search(self, search: db.SearchBuilder) -> None:
        search.titles.append(self.val)


class SongEditionMatch(SongValueMatch):
    """str that can be matched against a song's edition."""

    def build_search(self, search: db.SearchBuilder) -> None:
        search.editions.append(self.val)


class SongLanguageMatch(SongValueMatch):
    """str that can be matched against a song's language."""

    def build_search(self, search: db.SearchBuilder) -> None:
        search.languages.append(self.val)


@attrs.define(kw_only=True)
class TreeItem:
    """A row in the tree."""

    data: Any
    parent: TreeItem | None
    row_in_parent: int = attrs.field(default=0, init=False)
    children: tuple[TreeItem, ...] = attrs.field(factory=tuple, init=False)
    checked: bool = attrs.field(default=False, init=False)
    checkable: bool = attrs.field(default=False, init=False)

    def toggle_checked(self, _keep_siblings: bool) -> list[TreeItem]:
        """Returns toggled items."""
        return []

    def decoration(self) -> QIcon | None:
        return None


@attrs.define(kw_only=True)
class RootItem(TreeItem):
    """The root item of the tree. Only used internally."""

    data: None = attrs.field(default=None, init=False)
    parent: None = attrs.field(default=None, init=False)
    children: tuple[FilterItem, ...] = attrs.field(factory=tuple, init=False)

    def set_children(self, children: Iterable[FilterItem]) -> None:
        self.children = tuple(children)
        for row, child in enumerate(self.children):
            child.parent = self
            child.row_in_parent = row


@attrs.define(kw_only=True)
class FilterItem(TreeItem):
    """A top-level row in the tree representing a filter kind."""

    data: Filter
    parent: RootItem
    children: tuple[VariantItem, ...] = attrs.field(factory=tuple, init=False)
    checked_children: set[int] = attrs.field(factory=set, init=False)

    def add_child(self, child: VariantItem) -> None:
        child.parent = self
        child.row_in_parent = len(self.children)
        self.children = (*self.children, child)

    def set_children(self, children: Iterable[VariantItem]) -> None:
        self.children = tuple(children)
        for row, child in enumerate(self.children):
            child.parent = self
            child.row_in_parent = row

    def is_checkable(self) -> bool:
        return bool(self.checked_children)

    def toggle_checked(self, _keep_siblings: bool) -> list[TreeItem]:
        return self.uncheck_children() if self.checked else []

    def uncheck_children(self) -> list[TreeItem]:
        changed = list(self.checked_child_items())
        for child in changed:
            child.checked = False
        self.checked_children.clear()
        self.checkable = self.checked = False
        return changed + [self]

    def set_child_checked(
        self, child: int, checked: bool, keep_siblings: bool
    ) -> list[TreeItem]:
        changed = [self, self.children[child]]
        if checked:
            if not keep_siblings:
                changed += self.uncheck_children()
            self.checked_children.add(child)
        else:
            self.checked_children.remove(child)
        self.children[child].checked = checked
        self.checkable = self.checked = bool(self.checked_children)
        return changed

    def decoration(self) -> QIcon:
        return self.data.decoration()

    def checked_child_items(self) -> Iterable[VariantItem]:
        return (self.children[row] for row in self.checked_children)

    def build_search(self, search: db.SearchBuilder) -> None:
        for child in self.checked_child_items():
            child.data.build_search(search)


@attrs.define(kw_only=True)
class VariantItem(TreeItem):
    """A node row in the tree representing one variant of a specific filter."""

    data: SongMatch
    parent: FilterItem
    checkable: bool = attrs.field(default=True, init=False)
    children: tuple[TreeItem, ...] = attrs.field(factory=tuple, init=False)

    def is_checkable(self) -> bool:
        return True

    def toggle_checked(self, keep_siblings: bool) -> list[TreeItem]:
        return self.parent.set_child_checked(
            self.row_in_parent, not self.checked, keep_siblings
        )


class Filter(enum.Enum):
    """Kinds of filters in the tree."""

    STATUS = 0
    ARTIST = enum.auto()
    TITLE = enum.auto()
    EDITION = enum.auto()
    LANGUAGE = enum.auto()
    GOLDEN_NOTES = enum.auto()
    RATING = enum.auto()
    VIEWS = enum.auto()

    def __str__(self) -> str:
        match self:
            case Filter.STATUS:
                return "Status"
            case Filter.ARTIST:
                return "Artist"
            case Filter.TITLE:
                return "Title"
            case Filter.EDITION:
                return "Edition"
            case Filter.LANGUAGE:
                return "Language"
            case Filter.GOLDEN_NOTES:
                return "Golden Notes"
            case Filter.RATING:
                return "Rating"
            case Filter.VIEWS:
                return "Views"
            case _ as unreachable:
                assert_never(unreachable)

    def variants(self) -> Iterable[SongMatch]:
        match self:
            case Filter.ARTIST:
                return (SongArtistMatch(v, c) for v, c in db.usdb_song_artists())
            case Filter.TITLE:
                return (SongTitleMatch(v, c) for v, c in db.usdb_song_titles())
            case Filter.EDITION:
                return (SongEditionMatch(v, c) for v, c in db.usdb_song_editions())
            case Filter.LANGUAGE:
                return (SongLanguageMatch(v, c) for v, c in db.usdb_song_languages())
            case Filter.STATUS:
                return StatusVariant
            case Filter.GOLDEN_NOTES:
                return GoldenNotesVariant
            case Filter.RATING:
                return RatingVariant
            case Filter.VIEWS:
                return ViewsVariant
            case _ as unreachable:
                assert_never(unreachable)

    # https://github.com/PyCQA/pylint/issues/7857
    @cache  # pylint: disable=method-cache-max-size-none
    def decoration(self) -> QIcon:
        match self:
            case Filter.STATUS:
                return QIcon(":/icons/status.png")
            case Filter.ARTIST:
                return QIcon(":/icons/artist.png")
            case Filter.TITLE:
                return QIcon(":/icons/title.png")
            case Filter.EDITION:
                return QIcon(":/icons/edition.png")
            case Filter.LANGUAGE:
                return QIcon(":/icons/language.png")
            case Filter.GOLDEN_NOTES:
                return QIcon(":/icons/golden_notes.png")
            case Filter.RATING:
                return QIcon(":/icons/rating.png")
            case Filter.VIEWS:
                return QIcon(":/icons/views.png")
            case _ as unreachable:
                assert_never(unreachable)


class StatusVariant(SongMatch, enum.Enum):
    """Variants of the status of a song."""

    NONE = enum.auto()
    DOWNLOADED = enum.auto()
    IN_PROGRESS = enum.auto()
    FAILED = enum.auto()

    def __str__(self) -> str:
        match self:
            case StatusVariant.NONE:
                return "Not downloaded"
            case StatusVariant.DOWNLOADED:
                return "Downloaded"
            case StatusVariant.IN_PROGRESS:
                return "In progress"
            case StatusVariant.FAILED:
                return "Download failed"
            case _ as unreachable:
                assert_never(unreachable)

    def build_search(self, search: db.SearchBuilder) -> None:
        pass
        # TODO
        # match self:
        #     case StatusVariant.NONE:
        #         return LocalSong.str_path.is_(None) & UsdbSong.status.is_(
        #             DownloadStatus.NONE
        #         )
        #     case StatusVariant.DOWNLOADED:
        #         return LocalSong.str_path.is_not(None)
        #     case StatusVariant.IN_PROGRESS:
        #         return UsdbSong.status.in_(
        #             (DownloadStatus.PENDING, DownloadStatus.DOWNLOADING)
        #         )
        #     case StatusVariant.FAILED:
        #         return UsdbSong.status == DownloadStatus.FAILED
        #     case _ as unreachable:
        #         assert_never(unreachable)


class RatingVariant(SongMatch, enum.Enum):
    """Selectable variants for the song rating filter."""

    R_NONE = None
    R_1 = 1
    R_2 = 2
    R_3 = 3
    R_4 = 4
    R_5 = 5

    def __str__(self) -> str:
        if self == RatingVariant.R_NONE:
            return "None"
        return self.value * "★"

    def build_search(self, search: db.SearchBuilder) -> None:
        search.ratings.append(self.value or 0)


class GoldenNotesVariant(SongMatch, enum.Enum):
    """Selectable variants for the golden notes filter."""

    NO = False
    YES = True

    def __str__(self) -> str:
        match self:
            case GoldenNotesVariant.NO:
                return "No"
            case GoldenNotesVariant.YES:
                return "Yes"
            case _ as unreachable:
                assert_never(unreachable)

    def build_search(self, search: db.SearchBuilder) -> None:
        if search.golden_notes is None:
            search.golden_notes = self.value
        else:
            # Yes *and* No is the same as no filter
            search.golden_notes = None


class ViewsVariant(SongMatch, enum.Enum):
    """Selectable variants for the views filter."""

    V_0 = (0, 100)
    V_100 = (100, 200)
    V_200 = (200, 300)
    V_300 = (300, 400)
    V_400 = (400, 500)
    V_500 = (500, None)

    def __str__(self) -> str:
        if self.value[1] is None:
            return f"{self.value[0]}+"
        return f"{self.value[0]} to {self.value[1] - 1}"

    def build_search(self, search: db.SearchBuilder) -> None:
        search.views.append(self.value)
