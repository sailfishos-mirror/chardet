"""Pipeline orchestrator — runs all detection stages in sequence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from chardet.pipeline import DetectionResult

if TYPE_CHECKING:
    from chardet.enums import EncodingEra
from chardet.pipeline.ascii import detect_ascii
from chardet.pipeline.binary import is_binary
from chardet.pipeline.bom import detect_bom
from chardet.pipeline.escape import detect_escape_encoding
from chardet.pipeline.markup import detect_markup_charset
from chardet.pipeline.statistical import score_candidates
from chardet.pipeline.structural import compute_structural_score
from chardet.pipeline.utf8 import detect_utf8
from chardet.pipeline.utf1632 import detect_utf1632_patterns
from chardet.pipeline.validity import filter_by_validity
from chardet.registry import get_candidates

_NONE_RESULT = DetectionResult(encoding=None, confidence=0.0, language=None)
_STRUCTURAL_CONFIDENCE_THRESHOLD = 0.85


def run_pipeline(
    data: bytes,
    encoding_era: EncodingEra,
    max_bytes: int = 200_000,
) -> list[DetectionResult]:
    """Run the full detection pipeline. Returns list of results sorted by confidence."""
    data = data[:max_bytes]

    if not data:
        return [_NONE_RESULT]

    # Stage 1a: BOM detection (runs first — BOMs are definitive and
    # UTF-16/32 data looks binary due to null bytes)
    bom_result = detect_bom(data)
    if bom_result is not None:
        return [bom_result]

    # Stage 1a+: UTF-16/32 null-byte pattern detection (for files without
    # BOMs — must run before binary detection since these encodings contain
    # many null bytes that would trigger the binary check)
    utf1632_result = detect_utf1632_patterns(data)
    if utf1632_result is not None:
        return [utf1632_result]

    # Escape-sequence encodings (ISO-2022, HZ-GB-2312): must run before
    # binary detection (ESC is a control byte) and before ASCII detection
    # (HZ-GB-2312 uses only printable ASCII plus tildes).
    escape_result = detect_escape_encoding(data)
    if escape_result is not None:
        return [escape_result]

    # Stage 0: Binary detection
    if is_binary(data, max_bytes=max_bytes):
        return [_NONE_RESULT]

    # Stage 1b: Markup charset extraction (before ASCII/UTF-8 so explicit
    # declarations like <?xml encoding="iso-8859-1"?> are honoured even
    # when the bytes happen to be pure ASCII or valid UTF-8).
    markup_result = detect_markup_charset(data)
    if markup_result is not None:
        return [markup_result]

    # Stage 1c: ASCII
    ascii_result = detect_ascii(data)
    if ascii_result is not None:
        return [ascii_result]

    # Stage 1d: UTF-8 structural validation
    utf8_result = detect_utf8(data)
    if utf8_result is not None:
        return [utf8_result]

    # Stage 2a: Byte validity filtering
    candidates = get_candidates(encoding_era)
    valid_candidates = filter_by_validity(data, candidates)

    if not valid_candidates:
        return [_NONE_RESULT]

    # Stage 2b: Structural probing for multi-byte encodings
    structural_scores: list[tuple[str, float]] = []
    for enc in valid_candidates:
        if enc.is_multibyte:
            score = compute_structural_score(data, enc)
            if score > 0.0:
                structural_scores.append((enc.name, score))

    # If a multi-byte encoding scored very high, include it prominently
    if structural_scores:
        structural_scores.sort(key=lambda x: x[1], reverse=True)
        _best_name, best_score = structural_scores[0]
        if best_score >= _STRUCTURAL_CONFIDENCE_THRESHOLD:
            results = [
                DetectionResult(encoding=name, confidence=score, language=None)
                for name, score in structural_scores
            ]
            # Also score remaining single-byte candidates
            single_byte = tuple(e for e in valid_candidates if not e.is_multibyte)
            if single_byte:
                stat_results = score_candidates(data, single_byte)
                results.extend(stat_results)
            results.sort(key=lambda r: r.confidence, reverse=True)
            return results

    # Stage 3: Statistical scoring for all remaining candidates
    results = score_candidates(data, tuple(valid_candidates))

    if not results:
        return [_NONE_RESULT]

    return results
