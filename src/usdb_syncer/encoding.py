"""Utilities for different encodings."""

from __future__ import annotations

from enum import Enum


class CodePage(Enum):
    """Common code pages for languages on USDB."""

    EASTERN_EUROPEAN = "cp1250"
    CYRILLIC = "cp1251"
    WESTERN_EUROPEAN = "cp1252"
    GREEK = "cp1253"
    TURKISH = "cp1254"
    HEBREW = "cp1255"
    ARABIC = "cp1256"
    BALTIC = "cp1257"
    VIETNAMESE = "cp1258"

    @classmethod
    def from_language(cls, language: str) -> CodePage:
        match language:
            case "Czech" | "Polish" | "Slovak" | "Hungarian" | "Slovene" | \
                "Serbo-Croatian" | "Romanian" | "Rotokas" | "Albanian":  # fmt:skip
                return cls.EASTERN_EUROPEAN
            case "Bulgarian" | "Byelorussian" | "Macedonian" | "Russian" | \
                "Serbian" | "Urkainian":  # fmt:skip
                return cls.CYRILLIC
            case "Greek":
                return cls.GREEK
            case "Turkish":
                return cls.TURKISH
            case "Hebrew":
                return cls.HEBREW
            case "Arabic" | "Persian" | "Urdu":
                return cls.ARABIC
            case "Estonian" | "Latvian" | "Lithuanian":
                return cls.BALTIC
            case _:
                return cls.WESTERN_EUROPEAN

    def restore_text_from_cp1252(self, text: str) -> str:
        """Returns `text` with CP1252 symbols replaced with their counterparts in this
        code page.

        This is necessary if text encoded with some other codec was decoded using
        CP1252, like USDB does.
        """
        if self == CodePage.WESTERN_EUROPEAN:
            return text
        ansi_bytes = text.encode(CodePage.WESTERN_EUROPEAN.value, errors="replace")
        return str(ansi_bytes, encoding=self.value, errors="replace")
