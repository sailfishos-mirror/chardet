"""Stage 1d: HTML/XML charset declaration extraction."""

from __future__ import annotations

import codecs
import re

from chardet.pipeline import DetectionResult

_SCAN_LIMIT = 4096
_MARKUP_CONFIDENCE = 0.95

_XML_ENCODING_RE = re.compile(
    rb"""<\?xml[^>]+encoding\s*=\s*['"]([^'"]+)['"]""", re.IGNORECASE
)
_HTML5_CHARSET_RE = re.compile(
    rb"""<meta[^>]+charset\s*=\s*['"]?\s*([^\s'">;]+)""", re.IGNORECASE
)
_HTML4_CONTENT_TYPE_RE = re.compile(
    rb"""<meta[^>]+content\s*=\s*['"][^'"]*charset=([^\s'">;]+)""", re.IGNORECASE
)


def _normalize_encoding(name: bytes) -> str | None:
    """Validate encoding name via codecs and return the lowercased original name.

    We use ``codecs.lookup()`` to verify the encoding is recognized by Python,
    but return the original (lowercased) name rather than the codec's canonical
    name so that common aliases like ``iso-8859-1`` and ``windows-1252`` are
    preserved as-is.
    """
    try:
        text = name.decode("ascii").strip().lower()
        codecs.lookup(text)  # validate only
    except (LookupError, UnicodeDecodeError, ValueError):
        return None
    else:
        return text


def detect_markup_charset(data: bytes) -> DetectionResult | None:
    """Scan the first bytes of *data* for an HTML/XML charset declaration.

    Checks for:
    1. ``<?xml ... encoding="..."?>``
    2. ``<meta charset="...">``
    3. ``<meta http-equiv="Content-Type" content="...; charset=...">``

    Returns a `DetectionResult` with confidence 0.95 if a valid encoding is
    found, or ``None`` otherwise.
    """
    if not data:
        return None

    head = data[:_SCAN_LIMIT]

    for pattern in (_XML_ENCODING_RE, _HTML5_CHARSET_RE, _HTML4_CONTENT_TYPE_RE):
        match = pattern.search(head)
        if match:
            encoding = _normalize_encoding(match.group(1))
            if encoding is not None:
                return DetectionResult(
                    encoding=encoding,
                    confidence=_MARKUP_CONFIDENCE,
                    language=None,
                )

    return None
