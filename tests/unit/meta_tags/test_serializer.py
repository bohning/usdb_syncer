"""Test meta tag creator."""

from usdb_syncer.meta_tags.serializer import (
    ImageCropTag,
    MetaValues,
    VideoCropTag,
    video_tag_from_values,
)


def default_values() -> MetaValues:
    return MetaValues(
        video_url="",
        audio_url="",
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
        duet_p2="P2",
        preview_start=0,
        medley_start=0,
        medley_end=0,
    )


def test_yt_url_shortening() -> None:
    values = default_values()
    values.video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert video_tag_from_values(values) == "#VIDEO:v=dQw4w9WgXcQ"


def test_fanart_url_shortening() -> None:
    values = default_values()
    values.cover_url = "https://images.fanart.tv/fanart/the-room-5df4d0ed35191.jpg"
    assert video_tag_from_values(values) == "#VIDEO:co=the-room-5df4d0ed35191.jpg"


def test_url_shortening_and_escaping() -> None:
    values = default_values()
    values.cover_url = "https://www.website-with-strange-url.com/=,"
    assert (
        video_tag_from_values(values)
        == "#VIDEO:co=www.website-with-strange-url.com/%3D%2C"
    )
