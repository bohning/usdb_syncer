"""Representations of rows of the filter tree."""

from __future__ import annotations

import enum
from collections.abc import Iterable
from typing import Generic, TypeVar, assert_never

import attrs
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from usdb_syncer import db
from usdb_syncer.custom_data import CustomData
from usdb_syncer.gui.icons import Icon


# not an ABC so enums can inherit it (otherwise there's a metaclass conflict)
class TreeItemData:
    """Interface for objects to be rendered as a tree node."""

    def decoration(self) -> QIcon | None:
        raise NotImplementedError

    def is_checkable(self, has_checked_children: bool) -> bool:
        raise NotImplementedError

    def is_editable(self) -> bool:
        raise NotImplementedError

    def is_parent(self) -> bool:
        raise NotImplementedError

    def is_accepted(self, _matches: set[str | int]) -> bool:
        raise NotImplementedError

    def build_search(self, search: db.SearchBuilder) -> None:
        raise NotImplementedError

    def is_in_search(self, search: db.SearchBuilder) -> bool:
        raise NotImplementedError

    def child_data(self) -> Iterable[TreeItemData]:
        raise NotImplementedError


class RootItemData(TreeItemData):
    """Implementation of the tree root."""

    def decoration(self) -> QIcon | None:
        return None

    def is_checkable(self, has_checked_children: bool) -> bool:
        return False

    def is_editable(self) -> bool:
        return False

    def is_parent(self) -> bool:
        return True

    def is_accepted(self, _matches: set[str | int]) -> bool:
        return True

    def build_search(self, search: db.SearchBuilder) -> None:
        pass

    def is_in_search(self, search: db.SearchBuilder) -> bool:
        return True

    def child_data(self) -> Iterable[TreeItemData]:
        return Filter


@attrs.define(kw_only=True)
class TreeItem:
    """A row in the tree."""

    data: TreeItemData = attrs.field(factory=RootItemData)
    parent: TreeItem | None = None
    row_in_parent: int = attrs.field(default=0, init=False)
    children: list[TreeItem] = attrs.field(factory=list, init=False)
    checked: bool | None = attrs.field(default=False, init=False)
    checked_children: set[int] = attrs.field(factory=set, init=False)
    flags: Qt.ItemFlag = attrs.field(default=Qt.ItemFlag.ItemIsEnabled, init=False)

    def __attrs_post_init__(self) -> None:
        if self.data.is_checkable(True):
            self.flags |= Qt.ItemFlag.ItemIsUserCheckable
        else:
            self.checked = None
        if self.data.is_editable():
            self.flags |= Qt.ItemFlag.ItemIsEditable
        if not self.data.is_parent():
            self.flags |= Qt.ItemFlag.ItemNeverHasChildren

    def populate(self) -> None:
        self.set_children(TreeItem(data=d, parent=self) for d in self.data.child_data())
        for child in self.children:
            child.populate()

    def set_children(self, children: Iterable[TreeItem]) -> None:
        self.children = list(children)
        for row, child in enumerate(self.children):
            child.parent = self
            child.row_in_parent = row

    def add_child(self, child: TreeItem) -> None:
        child.parent = self
        child.row_in_parent = len(self.children)
        self.children.append(child)

    def remove_child(self, child: TreeItem) -> None:
        self.children.remove(child)
        self.checked_children.discard(child.row_in_parent)
        if self.checked is not None:
            self.checked = bool(self.checked_children)
        for later_child in self.children[child.row_in_parent :]:
            if later_child.row_in_parent in self.checked_children:
                self.checked_children.remove(later_child.row_in_parent)
                self.checked_children.add(later_child.row_in_parent - 1)
            later_child.row_in_parent -= 1

    def toggle_checked(self, keep_siblings: bool) -> list[TreeItem]:
        if not self.is_checkable():
            return []
        if self.checked:
            changed: list[TreeItem] = self._uncheck_children()
        else:
            changed = [self]
            self.checked = True
        if self.parent and self.parent.data.is_checkable(True):
            changed += self.parent._update_after_child_toggled(self, keep_siblings)
        return changed

    def is_checkable(self) -> bool:
        return self.data.is_checkable(bool(self.checked_children))

    def _uncheck_children(self) -> list[TreeItem]:
        changed: list[TreeItem] = [self]
        for child in self._checked_child_items():
            changed += child._uncheck_children()
        self.checked_children.clear()
        self.checked = False
        return changed

    def _update_after_child_toggled(
        self, child: TreeItem, keep_siblings: bool
    ) -> list[TreeItem]:
        checked_before = self.checked
        changed: list[TreeItem] = []
        if child.checked:
            if not keep_siblings:
                # `child` is not yet in children, so this is fine
                changed = self._uncheck_children()
            self.checked_children.add(child.row_in_parent)
        else:
            self.checked_children.remove(child.row_in_parent)
        self.checked = bool(self.checked_children)
        if self.checked != checked_before:
            changed.append(self)
            if self.parent and self.parent.data.is_checkable(True):
                changed += self.parent._update_after_child_toggled(
                    self, keep_siblings=True
                )
        return changed

    def apply_search(self, search: db.SearchBuilder) -> list[TreeItem]:
        changed = []
        if self.children:
            for child in self.children:
                before = child.checked
                changed.extend(child.apply_search(search))
                if self.checked is not None and child.checked != before:
                    if child.checked:
                        self.checked_children.add(child.row_in_parent)
                    else:
                        self.checked_children.remove(child.row_in_parent)
            if self.checked is not None and self.checked != bool(self.checked_children):
                changed.append(self)
                self.checked = not self.checked
        elif (
            self.checked is not None and self.data.is_in_search(search) != self.checked
        ):
            self.checked = not self.checked
            changed.append(self)
        return changed

    def _checked_child_items(self) -> Iterable[TreeItem]:
        return (self.children[row] for row in self.checked_children)

    def build_search(self, search: db.SearchBuilder) -> None:
        if self.checked is None:
            for child in self.children:
                child.build_search(search)
        elif self.checked:
            self.data.build_search(search)
            for child in self._checked_child_items():
                child.build_search(search)

    def filter_accepts_child(
        self, child_row: int, filters: dict[Filter, set[str | int]]
    ) -> bool:
        if (
            not isinstance(self.data, Filter)
            or (matches := filters.get(self.data)) is None
        ):
            return True
        return self.children[child_row].data.is_accepted(matches)


class Filter(TreeItemData, enum.Enum):
    """Kinds of filters in the tree."""

    SAVED = 0
    STATUS = enum.auto()
    ARTIST = enum.auto()
    EDITION = enum.auto()
    LANGUAGE = enum.auto()
    GOLDEN_NOTES = enum.auto()
    RATING = enum.auto()
    VIEWS = enum.auto()
    YEAR = enum.auto()
    GENRE = enum.auto()
    CREATOR = enum.auto()
    CUSTOM_DATA = enum.auto()

    def __str__(self) -> str:  # noqa: C901
        match self:
            case Filter.SAVED:
                return "Saved Searches"
            case Filter.STATUS:
                return "Status"
            case Filter.ARTIST:
                return "Artist"
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
            case Filter.CUSTOM_DATA:
                return "Custom Data"
            case _ as unreachable:
                assert_never(unreachable)

    def child_data(self) -> Iterable[TreeItemData]:  # noqa: C901
        match self:
            case Filter.SAVED:
                return SavedSearch.load_all()
            case Filter.ARTIST:
                return (SongArtistMatch(v, c) for v, c in db.usdb_song_artists())
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
            case Filter.CUSTOM_DATA:
                return (CustomDataKeyMatch(k) for k in sorted(CustomData.key_options()))
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
            case Filter.CUSTOM_DATA:
                icon = Icon.CUSTOM_DATA
            case _ as unreachable:
                assert_never(unreachable)
        return icon.icon()

    def is_checkable(self, has_checked_children: bool) -> bool:
        return self != Filter.SAVED and has_checked_children

    def is_editable(self) -> bool:
        return False

    def is_parent(self) -> bool:
        return True

    def is_accepted(self, _matches: set[str | int]) -> bool:
        return True

    def build_search(self, search: db.SearchBuilder) -> None:
        pass

    def is_in_search(self, search: db.SearchBuilder) -> bool:
        return True


class NodeItemData(TreeItemData):
    """Base implementation for a child of a filter item."""

    def decoration(self) -> QIcon | None:
        return None

    def is_checkable(self, has_checked_children: bool) -> bool:
        return True

    def is_editable(self) -> bool:
        return False

    def is_parent(self) -> bool:
        return False

    def is_accepted(self, _matches: set[str | int]) -> bool:
        return True

    def child_data(self) -> Iterable[TreeItemData]:
        return ()


T = TypeVar("T")


@attrs.define
class SongValueMatch(NodeItemData, Generic[T]):
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


class StatusVariant(NodeItemData, enum.Enum):
    """Variants of the status of a song."""

    NONE = db.DownloadStatus.NONE
    SYNCHRONIZED = db.DownloadStatus.SYNCHRONIZED
    OUTDATED = db.DownloadStatus.OUTDATED
    PENDING = db.DownloadStatus.PENDING
    DOWNLOADING = db.DownloadStatus.DOWNLOADING
    FAILED = db.DownloadStatus.FAILED

    def __str__(self) -> str:
        return "None" if self == StatusVariant.NONE else str(self.value)

    def build_search(self, search: db.SearchBuilder) -> None:
        search.statuses.append(self.value)

    def is_in_search(self, search: db.SearchBuilder) -> bool:
        return self.value in search.statuses


class RatingVariant(NodeItemData, enum.Enum):
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


class GoldenNotesVariant(NodeItemData, enum.Enum):
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


class ViewsVariant(NodeItemData, enum.Enum):
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
class SavedSearch(NodeItemData, db.SavedSearch):
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

    def is_checkable(self, has_checked_children: bool) -> bool:
        return False

    def is_editable(self) -> bool:
        return True


@attrs.define
class CustomDataKeyMatch(NodeItemData):
    """Key-value pair that can be matched against a song's custom data."""

    key: str

    def __str__(self) -> str:
        return self.key

    def build_search(self, search: db.SearchBuilder) -> None:
        pass

    def is_in_search(self, search: db.SearchBuilder) -> bool:
        return True

    def is_accepted(self, matches: set[str | int]) -> bool:
        return True

    def child_data(self) -> Iterable[TreeItemData]:
        return (
            CustomDataMatch(self.key, v)
            for v in sorted(CustomData.value_options(self.key))
        )

    def is_parent(self) -> bool:
        return True

    def is_checkable(self, has_checked_children: bool) -> bool:
        return has_checked_children


@attrs.define
class CustomDataMatch(NodeItemData):
    """Key-value pair that can be matched against a song's custom data."""

    key: str
    value: str

    def __str__(self) -> str:
        return self.value

    def build_search(self, search: db.SearchBuilder) -> None:
        search.custom_data[self.key].append(self.value)

    def is_in_search(self, search: db.SearchBuilder) -> bool:
        return self.value in search.custom_data.get(self.key, [])

    def is_accepted(self, _matches: set[str | int]) -> bool:
        return True
