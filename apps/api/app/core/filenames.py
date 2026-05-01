import re
import unicodedata

_RESERVED = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
_WHITESPACE = re.compile(r"\s+")
_REPEATED_UNDERSCORE = re.compile(r"_+")


def safe_filename(name: str, *, max_len: int = 100, fallback: str = "model") -> str:
    """Sanitize a string for use as a download filename.

    - Normalize unicode to NFKC, strip non-printable / control chars.
    - Replace path separators and Windows-reserved chars with `_`.
    - Collapse runs of whitespace into a single `_`.
    - Trim leading/trailing dots, spaces, dashes, underscores.
    - Truncate to ``max_len`` (no extension considered — pass the bare stem).
    - Fall back to ``fallback`` if the result is empty.
    """
    name = unicodedata.normalize("NFKC", name)
    name = "".join(ch for ch in name if ch.isprintable())
    name = _RESERVED.sub("_", name)
    name = _WHITESPACE.sub("_", name)
    name = _REPEATED_UNDERSCORE.sub("_", name)
    name = name.strip("._- ")
    if len(name) > max_len:
        name = name[:max_len].rstrip("._- ")
    return name or fallback
