"""Custom theming inspired by Material Design."""

from __future__ import annotations

import enum
from pathlib import Path
from typing import assert_never

import attrs
from PySide6 import QtWidgets
from PySide6.QtGui import QColor, QPalette

from usdb_syncer import settings, utils


def apply_theme(theme: settings.Theme) -> None:
    app = QtWidgets.QApplication.instance()
    assert isinstance(app, QtWidgets.QApplication), "Theming requires a GUI application"
    match theme:
        case settings.Theme.SYSTEM:
            q_palette = QPalette()
            style = ""
        case settings.Theme.DARK:
            palette = Palette(Colors.base_surface, Red.S_200)
            q_palette = palette.q_palette()
            style = DarkTheme(
                utils.AppPaths.stylesheets.joinpath("dark.qss"),
                Palette(Colors.base_surface, Red.S_200),
            ).style
        case unreachable:
            assert_never(unreachable)
    app.setPalette(q_palette)
    app.setStyleSheet(style)


class Surface(enum.Enum):
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


class Text(enum.Enum):
    HIGH = "text_high", 0.87
    MEDIUM = "text_medium", 0.60
    DISABLED = "text_disabled", 0.38

    def __str__(self) -> str:
        return self.value[0]

    def opacity(self) -> float:
        return self.value[1]


class Color(QColor):
    # r: int
    # g: int
    # b: int

    def overlay(self, color: Color, alpha: float) -> Color:
        return Color(
            _weighted_sum(self.red(), color.red(), alpha),
            _weighted_sum(self.green(), color.green(), alpha),
            _weighted_sum(self.blue(), color.blue(), alpha),
        )

    def __str__(self) -> str:
        return f"rgb({self.red()}, {self.green()}, {self.blue()})"


class Colors:
    white = Color(255, 255, 255)
    black = Color(0, 0, 0)
    base_surface = Color(18, 18, 18)


@attrs.define
class Palette:
    base_surface: Color
    primary: Color
    on_primary: Color = Colors.black
    on_secondary: Color = Colors.black
    on_background: Color = Colors.white
    on_surface: Color = Colors.white

    def surface(self, variant: Surface) -> Color:
        return self.base_surface.overlay(Colors.white, variant.overlay_alpha())

    def text(self, variant: Text) -> Color:
        return Color(
            round(self.on_background.red() * variant.opacity()),
            round(self.on_background.green() * variant.opacity()),
            round(self.on_background.blue() * variant.opacity()),
        )

    def q_palette(self) -> QPalette:
        palette = QPalette()
        high_text = self.text(Text.HIGH)
        palette.setColor(QPalette.ColorRole.WindowText, high_text)
        palette.setColor(QPalette.ColorRole.Button, self.surface(Surface.DP_06))
        palette.setColor(QPalette.ColorRole.Text, high_text)
        palette.setColor(QPalette.ColorRole.BrightText, self.primary)
        palette.setColor(QPalette.ColorRole.ButtonText, high_text)
        palette.setColor(QPalette.ColorRole.Base, self.surface(Surface.DP_01))
        palette.setColor(QPalette.ColorRole.Window, self.base_surface)
        palette.setColor(QPalette.ColorRole.Highlight, self.primary)
        palette.setColor(QPalette.ColorRole.HighlightedText, self.on_primary)
        palette.setColor(QPalette.ColorRole.Link, Blue.S_200)
        palette.setColor(QPalette.ColorRole.LinkVisited, Purple.S_200)
        palette.setColor(QPalette.ColorRole.AlternateBase, self.surface(Surface.DP_02))
        palette.setColor(QPalette.ColorRole.ToolTipBase, self.primary)
        palette.setColor(QPalette.ColorRole.ToolTipText, self.on_primary)
        palette.setColor(QPalette.ColorRole.PlaceholderText, self.text(Text.DISABLED))
        palette.setColor(QPalette.ColorRole.Accent, self.primary)
        return palette


class DarkTheme:
    on_primary: Color = Colors.black
    on_secondary: Color = Colors.black
    on_background: Color = Colors.white
    on_surface: Color = Colors.white

    def __init__(self, sheet: Path, palette: Palette) -> None:
        template = sheet.read_text(encoding="utf-8")
        surfaces = {str(s): palette.surface(s) for s in Surface}
        texts = {str(t): palette.text(t) for t in Text}
        self.style = template.format(
            **surfaces,
            **texts,
            primary=palette.primary,
            on_primary=self.on_primary,
            on_secondary=self.on_secondary,
            on_background=self.on_background,
            on_surface=self.on_surface,
        )


def _weighted_sum(x: int, y: int, y_weight: float) -> int:
    return round((1 - y_weight) * x + y_weight * y)


class Swatch:
    S_50: Color
    S_100: Color
    S_200: Color
    S_300: Color
    S_400: Color
    S_500: Color
    S_600: Color
    S_700: Color
    S_800: Color
    S_900: Color


class Red(Swatch):
    """Red swatch."""

    S_50 = Color(255, 235, 238)
    S_100 = Color(255, 205, 210)
    S_200 = Color(239, 154, 154)
    S_300 = Color(229, 115, 115)
    S_400 = Color(239, 83, 80)
    S_500 = Color(244, 67, 54)
    S_600 = Color(229, 57, 53)
    S_700 = Color(211, 47, 47)
    S_800 = Color(198, 40, 40)
    S_900 = Color(183, 28, 28)
    S_A100 = Color(255, 138, 128)
    S_A200 = Color(255, 82, 82)
    S_A400 = Color(255, 23, 68)
    S_A700 = Color(213, 0, 0)


class Pink(Swatch):
    """Pink swatch."""

    S_50 = Color(252, 228, 236)
    S_100 = Color(248, 187, 208)
    S_200 = Color(244, 143, 177)
    S_300 = Color(240, 98, 146)
    S_400 = Color(236, 64, 122)
    S_500 = Color(233, 30, 99)
    S_600 = Color(216, 27, 96)
    S_700 = Color(194, 24, 91)
    S_800 = Color(173, 20, 87)
    S_900 = Color(136, 14, 79)
    S_A100 = Color(255, 128, 171)
    S_A200 = Color(255, 64, 129)
    S_A400 = Color(245, 0, 87)
    S_A700 = Color(197, 17, 98)


class Purple(Swatch):
    """Purple swatch."""

    S_50 = Color(243, 229, 245)
    S_100 = Color(225, 190, 231)
    S_200 = Color(206, 147, 216)
    S_300 = Color(186, 104, 200)
    S_400 = Color(171, 71, 188)
    S_500 = Color(156, 39, 176)
    S_600 = Color(142, 36, 170)
    S_700 = Color(123, 31, 162)
    S_800 = Color(106, 27, 154)
    S_900 = Color(74, 20, 140)
    S_A100 = Color(234, 128, 252)
    S_A200 = Color(224, 64, 251)
    S_A400 = Color(213, 0, 249)
    S_A700 = Color(170, 0, 255)


class DeepPurple(Swatch):
    """DeepPurple swatch."""

    S_50 = Color(237, 231, 246)
    S_100 = Color(209, 196, 233)
    S_200 = Color(179, 157, 219)
    S_300 = Color(149, 117, 205)
    S_400 = Color(126, 87, 194)
    S_500 = Color(103, 58, 183)
    S_600 = Color(94, 53, 177)
    S_700 = Color(81, 45, 168)
    S_800 = Color(69, 39, 160)
    S_900 = Color(49, 27, 146)
    S_A100 = Color(179, 136, 255)
    S_A200 = Color(124, 77, 255)
    S_A400 = Color(101, 31, 255)
    S_A700 = Color(98, 0, 234)


class Indigo(Swatch):
    """Indigo swatch."""

    S_50 = Color(232, 234, 246)
    S_100 = Color(197, 202, 233)
    S_200 = Color(159, 168, 218)
    S_300 = Color(121, 134, 203)
    S_400 = Color(92, 107, 192)
    S_500 = Color(63, 81, 181)
    S_600 = Color(57, 73, 171)
    S_700 = Color(48, 63, 159)
    S_800 = Color(40, 53, 147)
    S_900 = Color(26, 35, 126)
    S_A100 = Color(140, 158, 255)
    S_A200 = Color(83, 109, 254)
    S_A400 = Color(61, 90, 254)
    S_A700 = Color(48, 79, 254)


class Blue(Swatch):
    """Blue swatch."""

    S_50 = Color(227, 242, 253)
    S_100 = Color(187, 222, 251)
    S_200 = Color(144, 202, 249)
    S_300 = Color(100, 181, 246)
    S_400 = Color(66, 165, 245)
    S_500 = Color(33, 150, 243)
    S_600 = Color(30, 136, 229)
    S_700 = Color(25, 118, 210)
    S_800 = Color(21, 101, 192)
    S_900 = Color(13, 71, 161)
    S_A100 = Color(130, 177, 255)
    S_A200 = Color(68, 138, 255)
    S_A400 = Color(41, 121, 255)
    S_A700 = Color(41, 98, 255)


class LightBlue(Swatch):
    """LightBlue swatch."""

    S_50 = Color(225, 245, 254)
    S_100 = Color(179, 229, 252)
    S_200 = Color(129, 212, 250)
    S_300 = Color(79, 195, 247)
    S_400 = Color(41, 182, 246)
    S_500 = Color(3, 169, 244)
    S_600 = Color(3, 155, 229)
    S_700 = Color(2, 136, 209)
    S_800 = Color(2, 119, 189)
    S_900 = Color(1, 87, 155)
    S_A100 = Color(128, 216, 255)
    S_A200 = Color(64, 196, 255)
    S_A400 = Color(0, 176, 255)
    S_A700 = Color(0, 145, 234)


class Cyan(Swatch):
    """Cyan swatch."""

    S_50 = Color(224, 247, 250)
    S_100 = Color(178, 235, 242)
    S_200 = Color(128, 222, 234)
    S_300 = Color(77, 208, 225)
    S_400 = Color(38, 198, 218)
    S_500 = Color(0, 188, 212)
    S_600 = Color(0, 172, 193)
    S_700 = Color(0, 151, 167)
    S_800 = Color(0, 131, 143)
    S_900 = Color(0, 96, 100)
    S_A100 = Color(132, 255, 255)
    S_A200 = Color(24, 255, 255)
    S_A400 = Color(0, 229, 255)
    S_A700 = Color(0, 184, 212)


class Teal(Swatch):
    """Teal swatch."""

    S_50 = Color(224, 242, 241)
    S_100 = Color(178, 223, 219)
    S_200 = Color(128, 203, 196)
    S_300 = Color(77, 182, 172)
    S_400 = Color(38, 166, 154)
    S_500 = Color(0, 150, 136)
    S_600 = Color(0, 137, 123)
    S_700 = Color(0, 121, 107)
    S_800 = Color(0, 105, 92)
    S_900 = Color(0, 77, 64)
    S_A100 = Color(167, 255, 235)
    S_A200 = Color(100, 255, 218)
    S_A400 = Color(29, 233, 182)
    S_A700 = Color(0, 191, 165)


class Green(Swatch):
    """Green swatch."""

    S_50 = Color(232, 245, 233)
    S_100 = Color(200, 230, 201)
    S_200 = Color(165, 214, 167)
    S_300 = Color(129, 199, 132)
    S_400 = Color(102, 187, 106)
    S_500 = Color(76, 175, 80)
    S_600 = Color(67, 160, 71)
    S_700 = Color(56, 142, 60)
    S_800 = Color(46, 125, 50)
    S_900 = Color(27, 94, 32)
    S_A100 = Color(185, 246, 202)
    S_A200 = Color(105, 240, 174)
    S_A400 = Color(0, 230, 118)
    S_A700 = Color(0, 200, 83)


class LightGreen(Swatch):
    """LightGreen swatch."""

    S_50 = Color(241, 248, 233)
    S_100 = Color(220, 237, 200)
    S_200 = Color(197, 225, 165)
    S_300 = Color(174, 213, 129)
    S_400 = Color(156, 204, 101)
    S_500 = Color(139, 195, 74)
    S_600 = Color(124, 179, 66)
    S_700 = Color(104, 159, 56)
    S_800 = Color(85, 139, 47)
    S_900 = Color(51, 105, 30)
    S_A100 = Color(204, 255, 144)
    S_A200 = Color(178, 255, 89)
    S_A400 = Color(118, 255, 3)
    S_A700 = Color(100, 221, 23)


class Lime(Swatch):
    """Lime swatch."""

    S_50 = Color(249, 251, 231)
    S_100 = Color(240, 244, 195)
    S_200 = Color(230, 238, 156)
    S_300 = Color(220, 231, 117)
    S_400 = Color(212, 225, 87)
    S_500 = Color(205, 220, 57)
    S_600 = Color(192, 202, 51)
    S_700 = Color(175, 180, 43)
    S_800 = Color(158, 157, 36)
    S_900 = Color(130, 119, 23)
    S_A100 = Color(244, 255, 129)
    S_A200 = Color(238, 255, 65)
    S_A400 = Color(198, 255, 0)
    S_A700 = Color(174, 234, 0)


class Yellow(Swatch):
    """Yellow swatch."""

    S_50 = Color(255, 253, 231)
    S_100 = Color(255, 249, 196)
    S_200 = Color(255, 245, 157)
    S_300 = Color(255, 241, 118)
    S_400 = Color(255, 238, 88)
    S_500 = Color(255, 235, 59)
    S_600 = Color(253, 216, 53)
    S_700 = Color(251, 192, 45)
    S_800 = Color(249, 168, 37)
    S_900 = Color(245, 127, 23)
    S_A100 = Color(255, 255, 141)
    S_A200 = Color(255, 255, 0)
    S_A400 = Color(255, 234, 0)
    S_A700 = Color(255, 214, 0)


class Amber(Swatch):
    """Amber swatch."""

    S_50 = Color(255, 248, 225)
    S_100 = Color(255, 236, 179)
    S_200 = Color(255, 224, 130)
    S_300 = Color(255, 213, 79)
    S_400 = Color(255, 202, 40)
    S_500 = Color(255, 193, 7)
    S_600 = Color(255, 179, 0)
    S_700 = Color(255, 160, 0)
    S_800 = Color(255, 143, 0)
    S_900 = Color(255, 111, 0)
    S_A100 = Color(255, 229, 127)
    S_A200 = Color(255, 215, 64)
    S_A400 = Color(255, 196, 0)
    S_A700 = Color(255, 171, 0)


class Orange(Swatch):
    """Orange swatch."""

    S_50 = Color(255, 243, 224)
    S_100 = Color(255, 224, 178)
    S_200 = Color(255, 204, 128)
    S_300 = Color(255, 183, 77)
    S_400 = Color(255, 167, 38)
    S_500 = Color(255, 152, 0)
    S_600 = Color(251, 140, 0)
    S_700 = Color(245, 124, 0)
    S_800 = Color(239, 108, 0)
    S_900 = Color(230, 81, 0)
    S_A100 = Color(255, 209, 128)
    S_A200 = Color(255, 171, 64)
    S_A400 = Color(255, 145, 0)
    S_A700 = Color(255, 109, 0)


class DeepOrange(Swatch):
    """DeepOrange swatch."""

    S_50 = Color(251, 233, 231)
    S_100 = Color(255, 204, 188)
    S_200 = Color(255, 171, 145)
    S_300 = Color(255, 138, 101)
    S_400 = Color(255, 112, 67)
    S_500 = Color(255, 87, 34)
    S_600 = Color(244, 81, 30)
    S_700 = Color(230, 74, 25)
    S_800 = Color(216, 67, 21)
    S_900 = Color(191, 54, 12)
    S_A100 = Color(255, 158, 128)
    S_A200 = Color(255, 110, 64)
    S_A400 = Color(255, 61, 0)
    S_A700 = Color(221, 44, 0)


class Brown(Swatch):
    """Brown swatch."""

    S_50 = Color(239, 235, 233)
    S_100 = Color(215, 204, 200)
    S_200 = Color(188, 170, 164)
    S_300 = Color(161, 136, 127)
    S_400 = Color(141, 110, 99)
    S_500 = Color(121, 85, 72)
    S_600 = Color(109, 76, 65)
    S_700 = Color(93, 64, 55)
    S_800 = Color(78, 52, 46)
    S_900 = Color(62, 39, 35)


class Gray(Swatch):
    """Gray swatch."""

    S_50 = Color(250, 250, 250)
    S_100 = Color(245, 245, 245)
    S_200 = Color(238, 238, 238)
    S_300 = Color(224, 224, 224)
    S_400 = Color(189, 189, 189)
    S_500 = Color(158, 158, 158)
    S_600 = Color(117, 117, 117)
    S_700 = Color(97, 97, 97)
    S_800 = Color(66, 66, 66)
    S_900 = Color(33, 33, 33)


class BlueGray(Swatch):
    """BlueGray swatch."""

    S_50 = Color(236, 239, 241)
    S_100 = Color(207, 216, 220)
    S_200 = Color(176, 190, 197)
    S_300 = Color(144, 164, 174)
    S_400 = Color(120, 144, 156)
    S_500 = Color(96, 125, 139)
    S_600 = Color(84, 110, 122)
    S_700 = Color(69, 90, 100)
    S_800 = Color(55, 71, 79)
    S_900 = Color(38, 50, 56)
