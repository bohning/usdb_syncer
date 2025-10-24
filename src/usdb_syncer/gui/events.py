"""Signals other components can notify and subscribe to."""

import attrs

from usdb_syncer import db, events
from usdb_syncer.gui import theme
from usdb_syncer.usdb_song import UsdbSong

# table


@attrs.define(slots=False)
class CurrentSongChanged(events.SubscriptableEvent):
    """Sent when the currently selected song changed."""

    song: UsdbSong | None


@attrs.define(slots=False)
class RowCountChanged(events.SubscriptableEvent):
    """Sent when the number of total or selected songs changed."""

    rows: int
    selected: int


# search


@attrs.define(slots=False)
class TreeFilterChanged(events.SubscriptableEvent):
    """Sent when a tree filter row has been selected or deselected."""

    search: db.SearchBuilder


@attrs.define(slots=False)
class TextFilterChanged(events.SubscriptableEvent):
    """Sent when the free text search has been changed."""

    search: str


@attrs.define(slots=False)
class SearchOrderChanged(events.SubscriptableEvent):
    """Sent when the search order has been changed or reversed."""

    order: db.SongOrder
    descending: bool


@attrs.define(slots=False)
class SavedSearchRestored(events.SubscriptableEvent):
    """Sent when the a save search is set."""

    search: db.SearchBuilder


# UI


@attrs.define(slots=False)
class ThemeChanged(events.SubscriptableEvent):
    """Sent when a new theme has been applied."""

    theme: theme.Theme
