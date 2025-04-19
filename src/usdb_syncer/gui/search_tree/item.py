"""Representations of rows of the filter tree."""

from __future__ import annotations

import enum
from collections.abc import Iterable
from typing import Any, Generic, TypeVar, assert_never

import attrs
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from usdb_syncer import db
from usdb_syncer.gui.icons import Icon


class SongMatch:
    """Interface for objects that can be matched against a song."""

    def build_search(self, search: db.SearchBuilder) -> None:
        raise NotImplementedError

    def is_in_search(self, search: db.SearchBuilder) -> bool:
        raise NotImplementedError

    def is_accepted(self, _matches: set[str | int]) -> bool:
        return True


T = TypeVar("T")


@attrs.define
class SongValueMatch(SongMatch, Generic[T]):
    """str that can be matched against a specific attribute of a song."""

    val: T
    count: int

    def __str__(self) -> str:
        return f"{self.val} [{self.count}]"

    def search_attr(self, search: db.SearchBuilder) -> list[T]:
        raise NotImplementedError

    def build_search(self, search: db.SearchBuilder) -> None:
        self.search_attr(search).append(self.val)

    def is_in_search(self, search: db.SearchBuilder) -> bool:
        return self.val in self.search_attr(search)

    def is_accepted(self, matches: set[str | int]) -> bool:
        return self.val in matches


class SongArtistMatch(SongValueMatch):
    """str that can be matched against a song's artist."""

    def search_attr(self, search: db.SearchBuilder) -> list[str]:
        return search.artists


class SongTitleMatch(SongValueMatch):
    """str that can be matched against a song's title."""

    def search_attr(self, search: db.SearchBuilder) -> list[str]:
        return search.titles


class SongEditionMatch(SongValueMatch):
    """str that can be matched against a song's edition."""

    def search_attr(self, search: db.SearchBuilder) -> list[str]:
        return search.editions


class SongLanguageMatch(SongValueMatch):
    """str that can be matched against a song's language."""

    def search_attr(self, search: db.SearchBuilder) -> list[str]:
        return search.languages


class SongYearMatch(SongValueMatch):
    """str that can be matched against a song's year."""

    def search_attr(self, search: db.SearchBuilder) -> list[int]:
        return search.years


class SongGenreMatch(SongValueMatch):
    """str that can be matched against a song's genre."""

    def search_attr(self, search: db.SearchBuilder) -> list[str]:
        return search.genres


class SongCreatorMatch(SongValueMatch):
    """str that can be matched against a song's creator."""

    def search_attr(self, search: db.SearchBuilder) -> list[str]:
        return search.creators


@attrs.define(kw_only=True)
class TreeItem:
    """A row in the tree."""

    data: Any
    parent: TreeItem | None
    checkable: bool = False
    row_in_parent: int = attrs.field(default=0, init=False)
    children: tuple[TreeItem, ...] = attrs.field(factory=tuple, init=False)
    checked: bool | None = attrs.field(default=False, init=False)

    def toggle_checked(self, _keep_siblings: bool) -> tuple[TreeItem, ...]:
        """Returns toggled items."""
        return ()

    def decoration(self) -> QIcon | None:
        return None

    def flags(self) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsEnabled

    def is_accepted(self, _matches: dict[Filter, set[str | int]]) -> bool:
        return True


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

    def __attrs_post_init__(self) -> None:
        self.checkable = self.data != Filter.SAVED

    def add_child(self, child: VariantItem) -> None:
        child.parent = self
        child.row_in_parent = len(self.children)
        self.children = (*self.children, child)

    def set_children(self, children: Iterable[VariantItem]) -> None:
        self.children = tuple(children)
        for row, child in enumerate(self.children):
            child.parent = self
            child.row_in_parent = row

    def flags(self) -> Qt.ItemFlag:
        if self.checked_children:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
        return Qt.ItemFlag.ItemIsEnabled

    def toggle_checked(self, _keep_siblings: bool) -> tuple[TreeItem, ...]:
        return self.uncheck_children() if self.checked else ()

    def uncheck_children(self) -> tuple[TreeItem, ...]:
        changed = tuple(self.checked_child_items())
        for child in changed:
            child.checked = False
        self.checked_children.clear()
        self.checked = False
        return (*changed, self)

    def set_child_checked(
        self, child: int, checked: bool, keep_siblings: bool
    ) -> tuple[TreeItem, ...]:
        changed: tuple[TreeItem, ...] = (self, self.children[child])
        if checked:
            if not keep_siblings:
                changed += self.uncheck_children()
            self.checked_children.add(child)
        else:
            self.checked_children.remove(child)
        self.children[child].checked = checked
        self.checked = bool(self.checked_children)
        return changed

    def set_checked_children(self, search: db.SearchBuilder) -> list[TreeItem]:
        changed: list[TreeItem] = []
        for idx, child in enumerate(self.children):
            if child.data.is_in_search(search) == child.checked:
                continue
            changed.append(child)
            child.checked = not child.checked
            if child.checked:
                self.checked_children.add(idx)
            else:
                self.checked_children.remove(idx)
        if self.checked != bool(self.checked_children):
            changed.append(self)
            self.checked = not self.checked
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
    children: tuple[TreeItem, ...] = attrs.field(factory=tuple, init=False)
    _flags: Qt.ItemFlag = attrs.field(init=False)

    def __attrs_post_init__(self) -> None:
        if self.parent.data == Filter.SAVED:
            self.checkable = False
            self._flags = (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemNeverHasChildren
                | Qt.ItemFlag.ItemIsEditable
            )
        else:
            self.checkable = True
            self._flags = (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemNeverHasChildren
            )

    def flags(self) -> Qt.ItemFlag:
        return self._flags

    def toggle_checked(self, keep_siblings: bool) -> tuple[TreeItem, ...]:
        return self.parent.set_child_checked(
            self.row_in_parent, not self.checked, keep_siblings
        )

    def is_accepted(self, matches: dict[Filter, set[str | int]]) -> bool:
        if (parent_matches := matches.get(self.parent.data)) is None:
            return True
        return self.data.is_accepted(parent_matches)


class Filter(enum.Enum):
    """Kinds of filters in the tree."""

    SAVED = 0
    STATUS = enum.auto()
    ARTIST = enum.auto()
    TITLE = enum.auto()
    EDITION = enum.auto()
    LANGUAGE = enum.auto()
    GOLDEN_NOTES = enum.auto()
    RATING = enum.auto()
    VIEWS = enum.auto()
    YEAR = enum.auto()
    GENRE = enum.auto()
    CREATOR = enum.auto()

    def __str__(self) -> str:  # noqa: C901
        match self:
            case Filter.SAVED:
                return "Saved Searches"
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
            case Filter.YEAR:
                return "Year"
            case Filter.GENRE:
                return "Genre"
            case Filter.CREATOR:
                return "Creator"
            case _ as unreachable:
                assert_never(unreachable)

    def variants(self) -> Iterable[SongMatch]:  # noqa: C901
        match self:
            case Filter.SAVED:
                return SavedSearch.load_all()
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
            case Filter.YEAR:
                return (SongYearMatch(v, c) for v, c in db.usdb_song_years())
            case Filter.GENRE:
                return (SongGenreMatch(v, c) for v, c in db.usdb_song_genres())
            case Filter.CREATOR:
                return (SongCreatorMatch(v, c) for v, c in db.usdb_song_creators())
            case _ as unreachable:
                assert_never(unreachable)

    def decoration(self) -> QIcon:  # noqa: C901
        match self:
            case Filter.SAVED:
                icon = Icon.SAVED_SEARCH
            case Filter.STATUS:
                icon = Icon.DOWNLOAD
            case Filter.ARTIST:
                icon = Icon.ARTIST
            case Filter.TITLE:
                icon = Icon.TITLE
            case Filter.EDITION:
                icon = Icon.EDITION
            case Filter.LANGUAGE:
                icon = Icon.LANGUAGE
            case Filter.GOLDEN_NOTES:
                icon = Icon.GOLDEN_NOTES
            case Filter.RATING:
                icon = Icon.RATING
            case Filter.VIEWS:
                icon = Icon.VIEWS
            case Filter.YEAR:
                icon = Icon.CALENDAR
            case Filter.GENRE:
                icon = Icon.GENRE
            case Filter.CREATOR:
                icon = Icon.CREATOR
            case _ as unreachable:
                assert_never(unreachable)
        return icon.icon()


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
                return "Failed"
            case _ as unreachable:
                assert_never(unreachable)

    def build_search(self, search: db.SearchBuilder) -> None:
        match self:
            case StatusVariant.IN_PROGRESS:
                search.statuses.append(db.DownloadStatus.PENDING)
                search.statuses.append(db.DownloadStatus.DOWNLOADING)
            case StatusVariant.FAILED:
                search.statuses.append(db.DownloadStatus.FAILED)
            case StatusVariant.NONE | StatusVariant.DOWNLOADED:
                search.downloaded = (
                    self is StatusVariant.DOWNLOADED
                    if search.downloaded is None
                    else None
                )
            case unreachable:
                assert_never(unreachable)

    def is_in_search(self, search: db.SearchBuilder) -> bool:
        match self:
            case StatusVariant.IN_PROGRESS:
                return (
                    db.DownloadStatus.PENDING in search.statuses
                    and db.DownloadStatus.DOWNLOADING in search.statuses
                )
            case StatusVariant.FAILED:
                return db.DownloadStatus.FAILED in search.statuses
            case StatusVariant.NONE:
                return search.downloaded is False
            case StatusVariant.DOWNLOADED:
                return search.downloaded is True
            case unreachable:
                assert_never(unreachable)


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

    def is_in_search(self, search: db.SearchBuilder) -> bool:
        return (self.value or 0) in search.ratings


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

    def is_in_search(self, search: db.SearchBuilder) -> bool:
        return self.value == search.golden_notes


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

    def is_in_search(self, search: db.SearchBuilder) -> bool:
        return self.value in search.views


@attrs.define
class SavedSearch(SongMatch, db.SavedSearch):
    """A search saved by the user."""

    @classmethod
    def load_all(cls) -> Iterable[SavedSearch]:
        with db.transaction():
            searches = db.SavedSearch.load_saved_searches()
        return (cls(s.name, s.search, s.is_default, s.subscribed) for s in searches)

    def build_search(self, search: db.SearchBuilder) -> None:
        pass

    def __str__(self) -> str:
        return self.name

    def is_in_search(self, search: db.SearchBuilder) -> bool:
        return False
