"""Detection pipeline stages and shared types."""

from __future__ import annotations

import dataclasses
from dataclasses import field


@dataclasses.dataclass(frozen=True, slots=True)
class DetectionResult:
    """A single encoding detection result.

    Frozen dataclass holding the encoding name, confidence score, and
    optional language identifier returned by the detection pipeline.
    """

    encoding: str | None
    confidence: float
    language: str | None

    def to_dict(self) -> dict[str, str | float | None]:
        """Convert this result to a plain dict.

        :returns: A dict with ``'encoding'``, ``'confidence'``, and ``'language'`` keys.
        """
        return {
            "encoding": self.encoding,
            "confidence": self.confidence,
            "language": self.language,
        }


@dataclasses.dataclass(slots=True)
class PipelineContext:
    """Per-run mutable state for a single pipeline invocation.

    Created once at the start of ``run_pipeline()`` and threaded through
    the call chain via function parameters.  Each concurrent ``detect()``
    call gets its own context, eliminating the need for module-level
    mutable caches.
    """

    analysis_cache: dict[tuple[int, int, str], tuple[float, int, int]] = field(
        default_factory=dict
    )
    non_ascii_count: int = -1
    mb_scores: dict[str, float] = field(default_factory=dict)
    mb_coverage: dict[str, float] = field(default_factory=dict)
