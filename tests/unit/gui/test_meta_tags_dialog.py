"""Test meta tag creator."""

from usdb_dl.gui.meta_tags_dialog import (
    ImageCropTag,
    TrimPoint,
    UiValues,
    VideoCropTag,
    _video_tag_from_values,
)


def default_values() -> UiValues:
    return UiValues(
        video_url="",
        audio_url="",
        video_trim_start=TrimPoint(mins=0, secs=0, use_frames=False, frames=0),
        video_trim_end=TrimPoint(mins=0, secs=0, use_frames=False, frames=0),
        video_crop=VideoCropTag(left=0, right=0, top=0, bottom=0),
        cover_url="",
        cover_rotation=0,
        cover_resize=0,
        cover_contrast_auto=False,
        cover_contrast=1,
        cover_crop=ImageCropTag(left=0, top=0, width=0, height=0),
        background_url="",
        background_resize_width=0,
        background_resize_height=0,
        background_crop=ImageCropTag(left=0, top=0, width=0, height=0),
        duet=False,
        duet_p1="P1",
        duet_p2="P1",
    )


def test_yt_url_shortening() -> None:
    values = default_values()
    values.video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert _video_tag_from_values(values) == "#VIDEO:v=dQw4w9WgXcQ"


def test_fanart_url_shortening() -> None:
    values = default_values()
    values.cover_url = "https://images.fanart.tv/fanart/the-room-5df4d0ed35191.jpg"
    assert _video_tag_from_values(values) == "#VIDEO:co=the-room-5df4d0ed35191.jpg"


def test_url_shortening_and_escaping() -> None:
    values = default_values()
    values.cover_url = "https://www.discogs.com/de/release/24814589-David-Bowie-Heroes/image/SW1hZ2U6ODU0MzU1NDM="
    assert (
        _video_tag_from_values(values)
        == "#VIDEO:co=www.discogs.com%2Fde%2Frelease%2F24814589-David-Bowie-Heroes%2Fimage%2FSW1hZ2U6ODU0MzU1NDM="
    )
