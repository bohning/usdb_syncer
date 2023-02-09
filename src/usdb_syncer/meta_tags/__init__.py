"""Utilities to parse and write meta tags."""

# Characters that have special meaning for the meta tag syntax and therefore
# must be escaped. Escaping is done with percent encoding.
META_TAG_ESCAPES = (("=", "%3D"), (",", "%2C"))


def encode_meta_tag_value(meta_tag: str) -> str:
    """Escape special characters inside the value part of a meta tag."""
    for char, escape in META_TAG_ESCAPES:
        meta_tag = meta_tag.replace(char, escape)
    return meta_tag


def decode_meta_tag_value(meta_tag: str) -> str:
    """Unescape special characters inside the value part of a meta tag."""

    for char, escape in META_TAG_ESCAPES:
        meta_tag = meta_tag.replace(escape, char)
    return meta_tag
