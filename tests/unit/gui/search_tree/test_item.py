from usdb_syncer.gui.search_tree.item import (
    Filter,
    SongArtistMatch,
    SongYearMatch,
    TreeItem,
)


def test_toggling_items() -> None:
    root = TreeItem()
    item_artist = TreeItem(data=Filter.ARTIST, parent=root)
    item_year = TreeItem(data=Filter.YEAR, parent=root)
    root.set_children([item_artist, item_year])
    item_abba = TreeItem(data=SongArtistMatch("ABBA", 4), parent=item_artist)
    item_blur = TreeItem(data=SongArtistMatch("Blur", 8), parent=item_artist)
    item_artist.set_children([item_abba, item_blur])
    item_1999 = TreeItem(data=SongYearMatch(1999, 15), parent=item_year)
    item_2025 = TreeItem(data=SongYearMatch(2025, 16), parent=item_year)
    item_year.set_children([item_1999, item_2025])

    item_abba.toggle_checked(keep_siblings=False)
    assert item_abba.checked is True
    assert item_blur.checked is False
    assert item_artist.checked is True

    item_blur.toggle_checked(keep_siblings=False)
    assert item_abba.checked is False
    assert item_blur.checked is True
    assert item_artist.checked is True

    item_abba.toggle_checked(keep_siblings=True)
    assert item_abba.checked is True
    assert item_blur.checked is True
    assert item_artist.checked is True

    item_artist.toggle_checked(keep_siblings=False)
    assert item_abba.checked is False
    assert item_blur.checked is False
    assert item_artist.checked is False
