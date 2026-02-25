"""Detection pipeline stages and shared types."""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class DetectionResult:
    encoding: str | None
    confidence: float
    language: str | None

    def to_dict(self) -> dict[str, str | float | None]:
        return {
            "encoding": self.encoding,
            "confidence": self.confidence,
            "language": self.language,
        }
