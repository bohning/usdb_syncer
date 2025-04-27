"""Custom theming inspired by Material Design."""

from __future__ import annotations

import enum
from importlib import resources
from typing import assert_never

import attrs
from PySide6 import QtWidgets
from PySide6.QtGui import QColor, QColorConstants, QPalette

from usdb_syncer import events, settings
from usdb_syncer.gui.resources import styles


def apply_theme(
    theme: settings.Theme, primary_color: settings.Color, colored_background: bool
) -> None:
    app = QtWidgets.QApplication.instance()
    assert isinstance(app, QtWidgets.QApplication), "Theming requires a GUI application"
    match theme:
        case settings.Theme.SYSTEM:
            q_palette = QPalette()
            style = ""
        case settings.Theme.DARK:
            dark_theme = DarkTheme(primary_color, colored_background)
            q_palette = dark_theme.q_palette()
            style = dark_theme.style()
        case unreachable:
            assert_never(unreachable)
    app.setPalette(q_palette)
    app.setStyleSheet(style)
    events.ThemeChanged(theme).post()


class _Surface(enum.Enum):
    """A surface of a certain level."""

    DP_00 = "surface_00dp", 0.0
    DP_01 = "surface_01dp", 0.05
    DP_02 = "surface_02dp", 0.07
    DP_03 = "surface_03dp", 0.08
    DP_04 = "surface_04dp", 0.09
    DP_06 = "surface_06dp", 0.11
    DP_08 = "surface_08dp", 0.12
    DP_12 = "surface_12dp", 0.14
    DP_16 = "surface_16dp", 0.15
    DP_24 = "surface_24dp", 0.16

    def __str__(self) -> str:
        return self.value[0]

    def overlay_alpha(self) -> float:
        return self.value[1]


class _Text(enum.Enum):
    """Text of a certain emphasis."""

    HIGH = "text_high", 0.87
    MEDIUM = "text_medium", 0.60
    DISABLED = "text_disabled", 0.38

    def __str__(self) -> str:
        return self.value[0]

    def opacity(self) -> float:
        return self.value[1]


def _overlay_colors(color_1: QColor, color_2: QColor, alpha: float) -> QColor:
    return QColor(
        _weighted_sum(color_1.red(), color_2.red(), alpha),
        _weighted_sum(color_1.green(), color_2.green(), alpha),
        _weighted_sum(color_1.blue(), color_2.blue(), alpha),
    )


def _weighted_sum(x: int, y: int, y_weight: float) -> int:
    return round((1 - y_weight) * x + y_weight * y)


def _rgb_str(color: QColor) -> str:
    return f"rgb({color.red()}, {color.green()}, {color.blue()})"


@attrs.define
class DarkTheme:
    """Style and palette builder for a dark theme."""

    primary_color: settings.Color
    colored_background: bool
    on_primary: QColor = QColorConstants.Svg.black
    on_secondary: QColor = QColorConstants.Svg.black
    on_background: QColor = QColorConstants.Svg.white
    on_surface: QColor = QColorConstants.Svg.white
    _style_template = resources.files(styles).joinpath("dark.qss")
    primary_swatch: Swatch = attrs.field(init=False)
    primary: QColor = attrs.field(init=False)
    base_surface: QColor = attrs.field(init=False)
    default_surface: QColor = attrs.field(init=False, default=QColor(18, 18, 18))

    def __attrs_post_init__(self) -> None:
        self.primary_swatch = Swatch.get(self.primary_color)
        self.primary = self.primary_swatch.s_200
        if self.colored_background:
            self.base_surface = _overlay_colors(
                self.default_surface, self.primary_swatch.s_900, 0.08
            )
        else:
            self.base_surface = self.default_surface

    def surface(self, variant: _Surface) -> QColor:
        return _overlay_colors(
            self.base_surface, QColorConstants.Svg.white, variant.overlay_alpha()
        )

    def text(self, variant: _Text) -> QColor:
        return QColor(
            round(self.on_background.red() * variant.opacity()),
            round(self.on_background.green() * variant.opacity()),
            round(self.on_background.blue() * variant.opacity()),
        )

    def q_palette(self) -> QPalette:
        palette = QPalette()
        high_text = self.text(_Text.HIGH)
        palette.setColor(QPalette.ColorRole.WindowText, high_text)
        palette.setColor(QPalette.ColorRole.Button, self.surface(_Surface.DP_06))
        palette.setColor(QPalette.ColorRole.Text, high_text)
        palette.setColor(QPalette.ColorRole.BrightText, self.primary)
        palette.setColor(QPalette.ColorRole.ButtonText, high_text)
        palette.setColor(QPalette.ColorRole.Base, self.surface(_Surface.DP_01))
        palette.setColor(QPalette.ColorRole.Window, self.base_surface)
        palette.setColor(QPalette.ColorRole.Highlight, self.primary)
        palette.setColor(QPalette.ColorRole.HighlightedText, self.on_primary)
        palette.setColor(QPalette.ColorRole.Link, Swatch.get(settings.Color.BLUE).s_200)
        palette.setColor(
            QPalette.ColorRole.LinkVisited, Swatch.get(settings.Color.PURPLE).s_200
        )
        palette.setColor(QPalette.ColorRole.AlternateBase, self.surface(_Surface.DP_02))
        palette.setColor(QPalette.ColorRole.ToolTipBase, self.primary)
        palette.setColor(QPalette.ColorRole.ToolTipText, self.on_primary)
        palette.setColor(QPalette.ColorRole.PlaceholderText, self.text(_Text.DISABLED))
        palette.setColor(QPalette.ColorRole.Accent, self.primary)
        return palette

    def style(self) -> str:
        surfaces = {str(s): _rgb_str(self.surface(s)) for s in _Surface}
        texts = {str(t): _rgb_str(self.text(t)) for t in _Text}
        return self._style_template.read_text(encoding="utf-8").format(
            **surfaces,
            **texts,
            primary=_rgb_str(self.primary_swatch.s_200),
            on_primary=_rgb_str(self.on_primary),
            on_secondary=_rgb_str(self.on_secondary),
            on_background=_rgb_str(self.on_background),
            on_surface=_rgb_str(self.on_surface),
        )


@attrs.define
class Swatch:
    """A Material Design swatch."""

    s_50: QColor
    s_100: QColor
    s_200: QColor
    s_300: QColor
    s_400: QColor
    s_500: QColor
    s_600: QColor
    s_700: QColor
    s_800: QColor
    s_900: QColor
    s_a100: QColor | None = None
    s_a200: QColor | None = None
    s_a400: QColor | None = None
    s_a700: QColor | None = None

    @classmethod
    def get(cls, color: settings.Color) -> Swatch:  # noqa: C901
        match color:
            case settings.Color.RED:
                return Swatch(
                    s_50=QColor(255, 235, 238),
                    s_100=QColor(255, 205, 210),
                    s_200=QColor(239, 154, 154),
                    s_300=QColor(229, 115, 115),
                    s_400=QColor(239, 83, 80),
                    s_500=QColor(244, 67, 54),
                    s_600=QColor(229, 57, 53),
                    s_700=QColor(211, 47, 47),
                    s_800=QColor(198, 40, 40),
                    s_900=QColor(183, 28, 28),
                    s_a100=QColor(255, 138, 128),
                    s_a200=QColor(255, 82, 82),
                    s_a400=QColor(255, 23, 68),
                    s_a700=QColor(213, 0, 0),
                )
            case settings.Color.PINK:
                return Swatch(
                    s_50=QColor(252, 228, 236),
                    s_100=QColor(248, 187, 208),
                    s_200=QColor(244, 143, 177),
                    s_300=QColor(240, 98, 146),
                    s_400=QColor(236, 64, 122),
                    s_500=QColor(233, 30, 99),
                    s_600=QColor(216, 27, 96),
                    s_700=QColor(194, 24, 91),
                    s_800=QColor(173, 20, 87),
                    s_900=QColor(136, 14, 79),
                    s_a100=QColor(255, 128, 171),
                    s_a200=QColor(255, 64, 129),
                    s_a400=QColor(245, 0, 87),
                    s_a700=QColor(197, 17, 98),
                )
            case settings.Color.PURPLE:
                return Swatch(
                    s_50=QColor(243, 229, 245),
                    s_100=QColor(225, 190, 231),
                    s_200=QColor(206, 147, 216),
                    s_300=QColor(186, 104, 200),
                    s_400=QColor(171, 71, 188),
                    s_500=QColor(156, 39, 176),
                    s_600=QColor(142, 36, 170),
                    s_700=QColor(123, 31, 162),
                    s_800=QColor(106, 27, 154),
                    s_900=QColor(74, 20, 140),
                    s_a100=QColor(234, 128, 252),
                    s_a200=QColor(224, 64, 251),
                    s_a400=QColor(213, 0, 249),
                    s_a700=QColor(170, 0, 255),
                )
            case settings.Color.DEEPPURPLE:
                return Swatch(
                    s_50=QColor(237, 231, 246),
                    s_100=QColor(209, 196, 233),
                    s_200=QColor(179, 157, 219),
                    s_300=QColor(149, 117, 205),
                    s_400=QColor(126, 87, 194),
                    s_500=QColor(103, 58, 183),
                    s_600=QColor(94, 53, 177),
                    s_700=QColor(81, 45, 168),
                    s_800=QColor(69, 39, 160),
                    s_900=QColor(49, 27, 146),
                    s_a100=QColor(179, 136, 255),
                    s_a200=QColor(124, 77, 255),
                    s_a400=QColor(101, 31, 255),
                    s_a700=QColor(98, 0, 234),
                )
            case settings.Color.INDIGO:
                return Swatch(
                    s_50=QColor(232, 234, 246),
                    s_100=QColor(197, 202, 233),
                    s_200=QColor(159, 168, 218),
                    s_300=QColor(121, 134, 203),
                    s_400=QColor(92, 107, 192),
                    s_500=QColor(63, 81, 181),
                    s_600=QColor(57, 73, 171),
                    s_700=QColor(48, 63, 159),
                    s_800=QColor(40, 53, 147),
                    s_900=QColor(26, 35, 126),
                    s_a100=QColor(140, 158, 255),
                    s_a200=QColor(83, 109, 254),
                    s_a400=QColor(61, 90, 254),
                    s_a700=QColor(48, 79, 254),
                )
            case settings.Color.BLUE:
                return Swatch(
                    s_50=QColor(227, 242, 253),
                    s_100=QColor(187, 222, 251),
                    s_200=QColor(144, 202, 249),
                    s_300=QColor(100, 181, 246),
                    s_400=QColor(66, 165, 245),
                    s_500=QColor(33, 150, 243),
                    s_600=QColor(30, 136, 229),
                    s_700=QColor(25, 118, 210),
                    s_800=QColor(21, 101, 192),
                    s_900=QColor(13, 71, 161),
                    s_a100=QColor(130, 177, 255),
                    s_a200=QColor(68, 138, 255),
                    s_a400=QColor(41, 121, 255),
                    s_a700=QColor(41, 98, 255),
                )
            case settings.Color.LIGHTBLUE:
                return Swatch(
                    s_50=QColor(225, 245, 254),
                    s_100=QColor(179, 229, 252),
                    s_200=QColor(129, 212, 250),
                    s_300=QColor(79, 195, 247),
                    s_400=QColor(41, 182, 246),
                    s_500=QColor(3, 169, 244),
                    s_600=QColor(3, 155, 229),
                    s_700=QColor(2, 136, 209),
                    s_800=QColor(2, 119, 189),
                    s_900=QColor(1, 87, 155),
                    s_a100=QColor(128, 216, 255),
                    s_a200=QColor(64, 196, 255),
                    s_a400=QColor(0, 176, 255),
                    s_a700=QColor(0, 145, 234),
                )
            case settings.Color.CYAN:
                return Swatch(
                    s_50=QColor(224, 247, 250),
                    s_100=QColor(178, 235, 242),
                    s_200=QColor(128, 222, 234),
                    s_300=QColor(77, 208, 225),
                    s_400=QColor(38, 198, 218),
                    s_500=QColor(0, 188, 212),
                    s_600=QColor(0, 172, 193),
                    s_700=QColor(0, 151, 167),
                    s_800=QColor(0, 131, 143),
                    s_900=QColor(0, 96, 100),
                    s_a100=QColor(132, 255, 255),
                    s_a200=QColor(24, 255, 255),
                    s_a400=QColor(0, 229, 255),
                    s_a700=QColor(0, 184, 212),
                )
            case settings.Color.TEAL:
                return Swatch(
                    s_50=QColor(224, 242, 241),
                    s_100=QColor(178, 223, 219),
                    s_200=QColor(128, 203, 196),
                    s_300=QColor(77, 182, 172),
                    s_400=QColor(38, 166, 154),
                    s_500=QColor(0, 150, 136),
                    s_600=QColor(0, 137, 123),
                    s_700=QColor(0, 121, 107),
                    s_800=QColor(0, 105, 92),
                    s_900=QColor(0, 77, 64),
                    s_a100=QColor(167, 255, 235),
                    s_a200=QColor(100, 255, 218),
                    s_a400=QColor(29, 233, 182),
                    s_a700=QColor(0, 191, 165),
                )
            case settings.Color.GREEN:
                return Swatch(
                    s_50=QColor(232, 245, 233),
                    s_100=QColor(200, 230, 201),
                    s_200=QColor(165, 214, 167),
                    s_300=QColor(129, 199, 132),
                    s_400=QColor(102, 187, 106),
                    s_500=QColor(76, 175, 80),
                    s_600=QColor(67, 160, 71),
                    s_700=QColor(56, 142, 60),
                    s_800=QColor(46, 125, 50),
                    s_900=QColor(27, 94, 32),
                    s_a100=QColor(185, 246, 202),
                    s_a200=QColor(105, 240, 174),
                    s_a400=QColor(0, 230, 118),
                    s_a700=QColor(0, 200, 83),
                )
            case settings.Color.LIGHTGREEN:
                return Swatch(
                    s_50=QColor(241, 248, 233),
                    s_100=QColor(220, 237, 200),
                    s_200=QColor(197, 225, 165),
                    s_300=QColor(174, 213, 129),
                    s_400=QColor(156, 204, 101),
                    s_500=QColor(139, 195, 74),
                    s_600=QColor(124, 179, 66),
                    s_700=QColor(104, 159, 56),
                    s_800=QColor(85, 139, 47),
                    s_900=QColor(51, 105, 30),
                    s_a100=QColor(204, 255, 144),
                    s_a200=QColor(178, 255, 89),
                    s_a400=QColor(118, 255, 3),
                    s_a700=QColor(100, 221, 23),
                )
            case settings.Color.LIME:
                return Swatch(
                    s_50=QColor(249, 251, 231),
                    s_100=QColor(240, 244, 195),
                    s_200=QColor(230, 238, 156),
                    s_300=QColor(220, 231, 117),
                    s_400=QColor(212, 225, 87),
                    s_500=QColor(205, 220, 57),
                    s_600=QColor(192, 202, 51),
                    s_700=QColor(175, 180, 43),
                    s_800=QColor(158, 157, 36),
                    s_900=QColor(130, 119, 23),
                    s_a100=QColor(244, 255, 129),
                    s_a200=QColor(238, 255, 65),
                    s_a400=QColor(198, 255, 0),
                    s_a700=QColor(174, 234, 0),
                )
            case settings.Color.YELLOW:
                return Swatch(
                    s_50=QColor(255, 253, 231),
                    s_100=QColor(255, 249, 196),
                    s_200=QColor(255, 245, 157),
                    s_300=QColor(255, 241, 118),
                    s_400=QColor(255, 238, 88),
                    s_500=QColor(255, 235, 59),
                    s_600=QColor(253, 216, 53),
                    s_700=QColor(251, 192, 45),
                    s_800=QColor(249, 168, 37),
                    s_900=QColor(245, 127, 23),
                    s_a100=QColor(255, 255, 141),
                    s_a200=QColor(255, 255, 0),
                    s_a400=QColor(255, 234, 0),
                    s_a700=QColor(255, 214, 0),
                )
            case settings.Color.AMBER:
                return Swatch(
                    s_50=QColor(255, 248, 225),
                    s_100=QColor(255, 236, 179),
                    s_200=QColor(255, 224, 130),
                    s_300=QColor(255, 213, 79),
                    s_400=QColor(255, 202, 40),
                    s_500=QColor(255, 193, 7),
                    s_600=QColor(255, 179, 0),
                    s_700=QColor(255, 160, 0),
                    s_800=QColor(255, 143, 0),
                    s_900=QColor(255, 111, 0),
                    s_a100=QColor(255, 229, 127),
                    s_a200=QColor(255, 215, 64),
                    s_a400=QColor(255, 196, 0),
                    s_a700=QColor(255, 171, 0),
                )
            case settings.Color.ORANGE:
                return Swatch(
                    s_50=QColor(255, 243, 224),
                    s_100=QColor(255, 224, 178),
                    s_200=QColor(255, 204, 128),
                    s_300=QColor(255, 183, 77),
                    s_400=QColor(255, 167, 38),
                    s_500=QColor(255, 152, 0),
                    s_600=QColor(251, 140, 0),
                    s_700=QColor(245, 124, 0),
                    s_800=QColor(239, 108, 0),
                    s_900=QColor(230, 81, 0),
                    s_a100=QColor(255, 209, 128),
                    s_a200=QColor(255, 171, 64),
                    s_a400=QColor(255, 145, 0),
                    s_a700=QColor(255, 109, 0),
                )

            case settings.Color.DEEPORANGE:
                return Swatch(
                    s_50=QColor(251, 233, 231),
                    s_100=QColor(255, 204, 188),
                    s_200=QColor(255, 171, 145),
                    s_300=QColor(255, 138, 101),
                    s_400=QColor(255, 112, 67),
                    s_500=QColor(255, 87, 34),
                    s_600=QColor(244, 81, 30),
                    s_700=QColor(230, 74, 25),
                    s_800=QColor(216, 67, 21),
                    s_900=QColor(191, 54, 12),
                    s_a100=QColor(255, 158, 128),
                    s_a200=QColor(255, 110, 64),
                    s_a400=QColor(255, 61, 0),
                    s_a700=QColor(221, 44, 0),
                )

            case settings.Color.BROWN:
                return Swatch(
                    s_50=QColor(239, 235, 233),
                    s_100=QColor(215, 204, 200),
                    s_200=QColor(188, 170, 164),
                    s_300=QColor(161, 136, 127),
                    s_400=QColor(141, 110, 99),
                    s_500=QColor(121, 85, 72),
                    s_600=QColor(109, 76, 65),
                    s_700=QColor(93, 64, 55),
                    s_800=QColor(78, 52, 46),
                    s_900=QColor(62, 39, 35),
                )
            case settings.Color.GRAY:
                return Swatch(
                    s_50=QColor(250, 250, 250),
                    s_100=QColor(245, 245, 245),
                    s_200=QColor(238, 238, 238),
                    s_300=QColor(224, 224, 224),
                    s_400=QColor(189, 189, 189),
                    s_500=QColor(158, 158, 158),
                    s_600=QColor(117, 117, 117),
                    s_700=QColor(97, 97, 97),
                    s_800=QColor(66, 66, 66),
                    s_900=QColor(33, 33, 33),
                )
            case settings.Color.BLUEGRAY:
                return Swatch(
                    s_50=QColor(236, 239, 241),
                    s_100=QColor(207, 216, 220),
                    s_200=QColor(176, 190, 197),
                    s_300=QColor(144, 164, 174),
                    s_400=QColor(120, 144, 156),
                    s_500=QColor(96, 125, 139),
                    s_600=QColor(84, 110, 122),
                    s_700=QColor(69, 90, 100),
                    s_800=QColor(55, 71, 79),
                    s_900=QColor(38, 50, 56),
                )
