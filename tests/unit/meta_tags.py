"""Tests for functions from the note_utils module."""

from usdb_syncer import SongId
from usdb_syncer.gui.meta_tags_dialog import _sanitize_video_url
from usdb_syncer.logger import get_logger
from usdb_syncer.meta_tags import ImageMetaTags, MetaTags

_logger = get_logger(__file__, SongId(1))


def test_video_meta_tags() -> None:
    """Test that a video URL / YouTube id is parsed. Trim and crop are currently not
    supported, but should not cause an error.
    """
    tag = "v=xPU8OAjjS4k,v-trim=24-5610,v-crop=244-244-0-0"
    meta = MetaTags.parse(tag, _logger)
    assert meta.video == "xPU8OAjjS4k"


def test_audio_meta_tags() -> None:
    """Test that an audio URL / YouTube id is parsed."""
    tag = "a=1oKKwuIZzr8"
    meta = MetaTags.parse(tag, _logger)
    assert meta.audio == "1oKKwuIZzr8"


def test_cover_meta_tags() -> None:
    """Test that a cover URL, rotation, crop, contrast and resize values are
    parsed. Resizes should be quadratic, but we use different values to check parse
    order anyway.
    """
    tag = (
        "co=m.media-amazon.com/images/I/91UzQS12wXL._SL1500_.jpg,co-rotate=0.8,"
        "co-crop=30-22-1468-1468,co-contrast=1.5,co-resize=1920-1921"
    )
    meta = MetaTags.parse(tag, _logger)
    assert meta.cover
    assert meta.cover.source == "m.media-amazon.com/images/I/91UzQS12wXL._SL1500_.jpg"
    assert meta.cover.rotate == 0.8
    assert meta.cover.crop
    assert meta.cover.crop.left == 30
    assert meta.cover.crop.upper == 22
    assert meta.cover.crop.right == 30 + 1468
    assert meta.cover.crop.lower == 22 + 1468
    assert meta.cover.contrast == 1.5
    assert meta.cover.resize
    assert meta.cover.resize.width == 1920
    assert meta.cover.resize.height == 1921


def test_background_meta_tags() -> None:
    """Test that a background URL, rotation, crop, contrast and resize values
    are parsed.
    """
    tag = (
        "bg=static.universal-music.de/asset_new/403774/195/view/Jon-Bellion-2016.jpg,"
        "bg-resize=1920-1280,bg-crop=0-80-1920-1160"
    )
    meta = MetaTags.parse(tag, _logger)
    assert meta.background
    assert (
        meta.background.source
        == "static.universal-music.de/asset_new/403774/195/view/Jon-Bellion-2016.jpg"
    )
    assert meta.background.crop
    assert meta.background.crop.left == 0
    assert meta.background.crop.upper == 80
    assert meta.background.crop.right == 1920
    assert meta.background.crop.lower == 80 + 1160
    assert meta.background.resize
    assert meta.background.resize.width == 1920
    assert meta.background.resize.height == 1280


def test_player_meta_tags() -> None:
    """Test that player information is parsed."""
    tag = "p1=Freddie Mercury,p2=Backing"
    meta = MetaTags.parse(tag, _logger)
    assert meta.player1 == "Freddie Mercury"
    assert meta.player2 == "Backing"


def test_yt_url_shortening() -> None:
    tags = MetaTags(video="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert str(tags) == "v=dQw4w9WgXcQ"


def test_fanart_url_shortening() -> None:
    tags = MetaTags(
        cover=ImageMetaTags(
            "https://images.fanart.tv/fanart/the-room-5df4d0ed35191.jpg"
        )
    )
    assert str(tags) == "co=the-room-5df4d0ed35191.jpg"


def test_url_shortening_and_escaping() -> None:
    assert (
        _sanitize_video_url(
            "https://www.url-containing-commas.com/this,url,has,commas.jpg"
        )
        == "www.url-containing-commas.com/this%2Curl%2Chas%2Ccommas.jpg"
    )
