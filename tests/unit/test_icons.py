from importlib import resources
from xml.etree import ElementTree

from usdb_syncer.gui.icons import Icon

ICONS_FILES = [
    file.name for file in resources.files("usdb_syncer.gui.resources.qt").iterdir()
]


EXCEPTIONS = ["tick-white.svg"]  # used in dark.qss


def _get_icon_used_names() -> set[str]:
    names = set()
    for icon in Icon:
        for file in icon.value:
            if file is not None:
                names.add(file)
    return names


def _get_qrc_icon_names() -> set[str]:
    names = set()
    with resources.open_text("usdb_syncer.gui.resources.qt", "resources.qrc") as f:
        tree = ElementTree.parse(f)  # noqa: S314
    icons = tree.getroot().find("./qresource[@prefix='icons']")
    if icons is not None:
        for file in icons.findall("file"):
            names.add(file.text)
    return names


def test_icons_missing():
    file_names = _get_icon_used_names()
    qrc_names = _get_qrc_icon_names()
    for name in file_names:
        assert name in qrc_names, f"Icon file not listed in resources.qrc: {name}"
        assert name in ICONS_FILES, f"Icon file not found: {name}"


def test_icons_used():
    names = _get_icon_used_names()
    for file in _get_qrc_icon_names():
        assert file in names or file in EXCEPTIONS, f"Icon file not used: {file}"
        assert file in ICONS_FILES, f"Icon file not found: {file}"
