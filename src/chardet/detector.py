"""UniversalDetector — streaming encoding detection."""

from __future__ import annotations

from chardet.enums import EncodingEra
from chardet.pipeline.bom import detect_bom
from chardet.pipeline.orchestrator import run_pipeline

_NONE_RESULT: dict[str, str | float | None] = {
    "encoding": None,
    "confidence": 0.0,
    "language": None,
}


class UniversalDetector:
    def __init__(
        self,
        encoding_era: EncodingEra = EncodingEra.MODERN_WEB,
        max_bytes: int = 200_000,
    ) -> None:
        self._encoding_era = encoding_era
        self._max_bytes = max_bytes
        self._buffer = bytearray()
        self._done = False
        self._closed = False
        self._result: dict[str, str | float | None] | None = None

    def feed(self, data: bytes) -> None:
        if self._closed:
            msg = "feed() called after close() without reset()"
            raise ValueError(msg)
        if self._done:
            return
        remaining = self._max_bytes - len(self._buffer)
        if remaining > 0:
            self._buffer.extend(data[:remaining])
        if len(self._buffer) >= 4 and self._result is None:
            bom_result = detect_bom(bytes(self._buffer))
            if bom_result is not None:
                self._result = bom_result.to_dict()
                self._done = True

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._result is not None:
            return
        data = bytes(self._buffer)
        results = run_pipeline(data, self._encoding_era, max_bytes=self._max_bytes)
        self._result = results[0].to_dict()
        self._done = True

    def reset(self) -> None:
        self._buffer = bytearray()
        self._done = False
        self._closed = False
        self._result = None

    @property
    def done(self) -> bool:
        return self._done

    @property
    def result(self) -> dict[str, str | float | None]:
        if self._result is not None:
            return self._result
        return dict(_NONE_RESULT)
