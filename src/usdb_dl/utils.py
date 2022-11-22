"""General-purpose utilities."""

import re


def extract_youtube_id(url: str) -> str | None:
    """Extracts the YouTube id from one of the following formats:
    `https://youtube.com/watch?v={id}`
    `https://youtube.com/embed/{id}`
    `https://youtu.be/{id}`

    Partially taken from `pytube.extract.video_id`.
    """

    pattern = r"""
        (?:https?://)?
        (?:www\.)?
        (?:
            youtube\.com/watch\?v=
            |
            youtube\.com/embed/
            |
            youtu\.be/
        )
        ([0-9A-Za-z_-]{11})         # the actual id
        .*                          # URL may contain additonal parameters
        """
    if match := re.search(pattern, url, re.X):
        return match.group(1)
    return None
