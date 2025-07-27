from __future__ import annotations

from collections.abc import Iterable

import attrs

from usdb_syncer import db
from usdb_syncer.gui.search_tree.item import (
    CustomDataKeyMatch,
    CustomDataMatch,
    Filter,
    SongArtistMatch,
    SongYearMatch,
    TreeItem,
)


@attrs.define(kw_only=True)
class TestCustomDataTree:
    """Test data structure for custom data tree."""

    root: TreeItem
    artist: TreeItem
    year: TreeItem
    custom_data: TreeItem
    abba: TreeItem
    blur: TreeItem
    y1999: TreeItem
    y2025: TreeItem
    animal: TreeItem
    dance: TreeItem
    bee: TreeItem
    cat: TreeItem
    eisa: TreeItem
    fandango: TreeItem

    @classmethod
    def new(cls) -> TestCustomDataTree:
        root = TreeItem()
        artist = TreeItem(data=Filter.ARTIST, parent=root)
        year = TreeItem(data=Filter.YEAR, parent=root)
        custom_data = TreeItem(data=Filter.CUSTOM_DATA, parent=root)
        root.set_children([artist, year, custom_data])
        abba = TreeItem(data=SongArtistMatch("ABBA", 4), parent=artist)
        blur = TreeItem(data=SongArtistMatch("Blur", 8), parent=artist)
        artist.set_children([abba, blur])
        y1999 = TreeItem(data=SongYearMatch(1999, 15), parent=year)
        y2025 = TreeItem(data=SongYearMatch(2025, 16), parent=year)
        year.set_children([y1999, y2025])
        animal = TreeItem(data=CustomDataKeyMatch("Animal"), parent=custom_data)
        dance = TreeItem(data=CustomDataKeyMatch("Dance"), parent=custom_data)
        custom_data.set_children([animal, dance])
        bee = TreeItem(data=CustomDataMatch("Animal", "Bee"), parent=animal)
        cat = TreeItem(data=CustomDataMatch("Animal", "Cat"), parent=animal)
        animal.set_children([bee, cat])
        eisa = TreeItem(data=CustomDataMatch("Dance", "Eisa"), parent=dance)
        fandango = TreeItem(data=CustomDataMatch("Dance", "Fandango"), parent=dance)
        dance.set_children([eisa, fandango])
        return cls(
            root=root,
            artist=artist,
            year=year,
            custom_data=custom_data,
            abba=abba,
            blur=blur,
            y1999=y1999,
            y2025=y2025,
            animal=animal,
            dance=dance,
            bee=bee,
            cat=cat,
            eisa=eisa,
            fandango=fandango,
        )

    def assert_checked(self, **kwargs: bool) -> None:
        error = self.build_error_msg(**kwargs)
        for attr, checked in kwargs.items():
            assert getattr(self, attr).checked is checked, error
        for field in attrs.fields(TestCustomDataTree):
            if field.name != "root" and field.name not in kwargs:
                assert getattr(self, field.name).checked is False, error

    def iter_item_levels(self) -> Iterable[tuple[TreeItem, int]]:
        def iter_item(item: TreeItem, level: int = 0) -> Iterable[tuple[TreeItem, int]]:
            yield item, level
            for child in item.children:
                yield from iter_item(child, level + 1)

        for item in self.root.children:
            yield from iter_item(item)

    def build_error_msg(self, **kwargs: bool) -> str:
        info = {
            str(item.data): (item.checked, level * 4)
            for item, level in self.iter_item_levels()
        }
        actual = write_checked_tree(**info)
        for attr, checked in kwargs.items():
            key = str(getattr(self, attr).data)
            info[key] = (checked, info[key][1])
        expected = write_checked_tree(**info)
        return "\n".join(("Expected tree:", expected, "Actual tree:", actual))


def write_checked_tree(**kwargs: tuple[bool | None, int]) -> str:
    def line(attr: str, checked: bool | None, indent: int) -> str:
        return f"{' ' * indent}[{'X' if checked else ' '}] {attr}"

    return "\n".join(
        (line(attr, checked, indent) for attr, (checked, indent) in kwargs.items())
    )


def test_toggling_items() -> None:
    tree = TestCustomDataTree.new()

    tree.abba.toggle_checked(keep_siblings=False)
    tree.assert_checked(abba=True, artist=True)

    tree.blur.toggle_checked(keep_siblings=False)
    tree.assert_checked(blur=True, artist=True)

    tree.abba.toggle_checked(keep_siblings=True)
    tree.assert_checked(abba=True, blur=True, artist=True)

    tree.year.toggle_checked(keep_siblings=True)
    tree.assert_checked(artist=True, abba=True, blur=True)

    tree.y1999.toggle_checked(keep_siblings=True)
    tree.assert_checked(artist=True, abba=True, blur=True, year=True, y1999=True)

    tree.artist.toggle_checked(keep_siblings=False)
    tree.assert_checked(year=True, y1999=True)


def test_toggling_custom_data() -> None:
    tree = TestCustomDataTree.new()

    tree.bee.toggle_checked(keep_siblings=False)
    tree.assert_checked(custom_data=True, animal=True, bee=True)

    tree.cat.toggle_checked(keep_siblings=False)
    tree.assert_checked(custom_data=True, animal=True, cat=True)

    tree.fandango.toggle_checked(keep_siblings=False)
    tree.assert_checked(
        custom_data=True, animal=True, cat=True, dance=True, fandango=True
    )

    tree.dance.toggle_checked(keep_siblings=False)
    tree.assert_checked(custom_data=True, animal=True, cat=True)

    tree.dance.toggle_checked(keep_siblings=False)
    tree.assert_checked(custom_data=True, animal=True, cat=True)


def test_restoring_search() -> None:
    tree = TestCustomDataTree.new()
    tree.abba.toggle_checked(keep_siblings=False)
    tree.eisa.toggle_checked(keep_siblings=False)
    search = db.SearchBuilder()
    tree.root.build_search(search)

    tree = TestCustomDataTree.new()
    tree.y1999.toggle_checked(keep_siblings=False)
    tree.bee.toggle_checked(keep_siblings=False)
    tree.root.apply_search(search)
    tree.assert_checked(artist=True, abba=True, custom_data=True, dance=True, eisa=True)
