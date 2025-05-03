"""Signals other components can notify and subscribe to."""

import attrs

from usdb_syncer import db, events
from usdb_syncer.gui import theme

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
