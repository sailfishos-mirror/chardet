"""UniversalDetector — streaming encoding detection."""

from __future__ import annotations

import warnings
from typing import ClassVar

from chardet.enums import EncodingEra, LanguageFilter
from chardet.equivalences import PREFERRED_SUPERSET, apply_legacy_rename
from chardet.pipeline import DetectionResult
from chardet.pipeline.ascii import detect_ascii
from chardet.pipeline.bom import detect_bom
from chardet.pipeline.escape import detect_escape_encoding
from chardet.pipeline.orchestrator import run_pipeline
from chardet.pipeline.utf8 import detect_utf8

_NONE_RESULT = DetectionResult(encoding=None, confidence=0.0, language=None)

# Minimum bytes before running deterministic checks (avoids repeated work
# on tiny feed() calls).
_MIN_INCREMENTAL_CHECK = 64


class UniversalDetector:
    MINIMUM_THRESHOLD = 0.20
    LEGACY_MAP: ClassVar[dict[str, str]] = dict(PREFERRED_SUPERSET)

    def __init__(
        self,
        lang_filter: LanguageFilter = LanguageFilter.ALL,
        should_rename_legacy: bool | None = None,
        encoding_era: EncodingEra = EncodingEra.MODERN_WEB,
        max_bytes: int = 200_000,
    ) -> None:
        if lang_filter != LanguageFilter.ALL:
            warnings.warn(
                "lang_filter is not implemented in this version of chardet "
                "and will be ignored",
                DeprecationWarning,
                stacklevel=2,
            )
        if should_rename_legacy is None:
            self._rename_legacy = encoding_era == EncodingEra.MODERN_WEB
        else:
            self._rename_legacy = should_rename_legacy
        self._encoding_era = encoding_era
        self._max_bytes = max_bytes
        self._buffer = bytearray()
        self._done = False
        self._closed = False
        self._result: dict[str, str | float | None] | None = None
        self._has_non_ascii = False
        self._last_checked: int = 0

    def feed(self, byte_str: bytes | bytearray) -> None:
        if self._closed:
            msg = "feed() called after close() without reset()"
            raise ValueError(msg)
        if self._done:
            return
        remaining = self._max_bytes - len(self._buffer)
        if remaining > 0:
            self._buffer.extend(byte_str[:remaining])
        self._try_incremental_detect()

    def _try_incremental_detect(self) -> None:
        """Run fast deterministic checks on the buffer to enable early done."""
        buf_len = len(self._buffer)
        if self._result is not None or buf_len < 4:
            return

        buf = bytes(self._buffer)

        # BOM detection (definitive)
        bom_result = detect_bom(buf)
        if bom_result is not None:
            self._result = bom_result.to_dict()
            self._done = True
            return

        # Avoid re-checking on every tiny feed; only recheck after enough new
        # data has arrived.
        if buf_len - self._last_checked < _MIN_INCREMENTAL_CHECK:
            return
        prev_checked = self._last_checked
        self._last_checked = buf_len

        # Track whether any non-ASCII byte has been seen (only scan new bytes)
        if not self._has_non_ascii:
            self._has_non_ascii = any(b > 0x7F for b in self._buffer[prev_checked:])

        # Escape-sequence encodings (ISO-2022, HZ-GB-2312)
        escape_result = detect_escape_encoding(buf)
        if escape_result is not None:
            self._result = escape_result.to_dict()
            self._done = True
            return

        # Pure ASCII (only confident if we haven't seen non-ASCII and have
        # enough data)
        if not self._has_non_ascii and buf_len >= _MIN_INCREMENTAL_CHECK:
            ascii_result = detect_ascii(buf)
            if ascii_result is not None:
                self._result = ascii_result.to_dict()
                self._done = True
                return

        # UTF-8 structural validation
        if self._has_non_ascii:
            utf8_result = detect_utf8(buf)
            if utf8_result is not None:
                self._result = utf8_result.to_dict()
                self._done = True
                return

    def close(self) -> dict[str, str | float | None]:
        if not self._closed:
            self._closed = True
            if self._result is None:
                data = bytes(self._buffer)
                results = run_pipeline(
                    data, self._encoding_era, max_bytes=self._max_bytes
                )
                self._result = results[0].to_dict()
                self._done = True
            if self._rename_legacy and self._result is not None:
                apply_legacy_rename(self._result)
        return self.result

    def reset(self) -> None:
        self._buffer = bytearray()
        self._done = False
        self._closed = False
        self._result = None
        self._has_non_ascii = False
        self._last_checked = 0

    @property
    def done(self) -> bool:
        return self._done

    @property
    def result(self) -> dict[str, str | float | None]:
        if self._result is not None:
            return self._result
        return _NONE_RESULT.to_dict()
