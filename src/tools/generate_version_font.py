"""Generate a minimal font from Kozuka Gothic Pro ExtraLight for splash screen version string.

Requires fontTools to be installed (pip install fonttools).
"""

import tempfile
from pathlib import Path

import requests
from fontTools import subset
from fontTools.ttLib import TTFont

BASE_FONT = "KozGoPro-ExtraLight.otf"
URL = f"https://www.wfonts.com/download/data/2014/12/30/kozuka-gothic-pro/{BASE_FONT}"
NEW_FONT_NAME = "Kozuka Gothic Pro Version String"
OUTPUT_DIR = (
    Path(__file__).parent.parent / "usdb_syncer" / "gui" / "resources" / "fonts"
)
OUTPUT_PATH = OUTPUT_DIR / "KozukaGothicProVersion.otf"
DIGITS = "U+0030-0039"
LETTERS = "U+0061-007A"
PUNCTUATION = "U+002E,U+002B"
UNICODES = f"{DIGITS},{LETTERS},{PUNCTUATION}"


def download_font(tmp_path: Path) -> None:
    print(f"Downloading {BASE_FONT} into a temporary file...")
    r = requests.get(URL, timeout=30)
    r.raise_for_status()
    tmp_path.write_bytes(r.content)


def create_subset(original_path: Path, output_path: Path) -> None:
    print(f"Creating temporary subset font with glyphs {UNICODES} ...")
    subset.main(
        [str(original_path), f"--unicodes={UNICODES}", f"--output-file={output_path!s}"]
    )


def fix_metrics(font: TTFont) -> None:
    print("Adjusting metrics for subset font ...")
    glyf_table = font["glyf"]

    all_y_min: list[int] = []
    all_y_max: list[int] = []
    for glyph_name in font.getGlyphOrder():
        if glyph_name in glyf_table:
            glyph = glyf_table[glyph_name]
            if hasattr(glyph, "yMin"):
                all_y_min.append(glyph.yMin)
                all_y_max.append(glyph.yMax)

    if not all_y_min:
        print("No glyph metrics found, skipping metric adjustment.")
        return

    y_min = min(all_y_min)
    y_max = max(all_y_max)
    padding = int((y_max - y_min) * 0.1)

    font["OS/2"].usWinAscent = y_max + padding
    font["OS/2"].usWinDescent = abs(y_min) + padding
    font["OS/2"].sTypoAscender = y_max
    font["OS/2"].sTypoDescender = y_min
    font["OS/2"].sTypoLineGap = 0

    font["hhea"].ascent = y_max
    font["hhea"].descent = y_min
    font["hhea"].lineGap = 0


def fix_names(font: TTFont) -> None:
    print("Adjusting font name table ...")
    name_table = font["name"]
    for record in name_table.names:
        if record.nameID in {1, 3, 4, 6}:
            new_name = (
                NEW_FONT_NAME.replace(" ", "") if record.nameID == 6 else NEW_FONT_NAME
            )
            record.string = new_name.encode(record.getEncoding())


def save_font(font: TTFont, output_path: Path) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    font.save(str(output_path))
    print(f"Successfully saved Rating Symbols font as '{output_path}'.")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        original_tmp = tmp / "original.ttf"
        subset_tmp = tmp / "subset.ttf"

        download_font(original_tmp)
        create_subset(original_tmp, subset_tmp)

        font = TTFont(str(subset_tmp))
        try:
            # fix_metrics(font)
            fix_names(font)
            save_font(font, OUTPUT_PATH)
        finally:
            font.close()


if __name__ == "__main__":
    main()
