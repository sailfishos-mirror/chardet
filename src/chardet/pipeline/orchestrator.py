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
from chardet.pipeline.mess import compute_mess_score
from chardet.pipeline.statistical import score_candidates
from chardet.pipeline.structural import (
    compute_multibyte_byte_coverage,
    compute_structural_score,
)
from chardet.pipeline.utf8 import detect_utf8
from chardet.pipeline.utf1632 import detect_utf1632_patterns
from chardet.pipeline.validity import filter_by_validity
from chardet.registry import get_candidates

_BINARY_RESULT = DetectionResult(encoding=None, confidence=0.95, language=None)
_FALLBACK_RESULT = DetectionResult(
    encoding="windows-1252", confidence=0.10, language=None
)
_STRUCTURAL_CONFIDENCE_THRESHOLD = 0.85

# Common Western Latin encodings that share the iso-8859-1 character
# repertoire for the byte values where iso-8859-10 is indistinguishable.
# Used as swap targets when demoting iso-8859-10 — we prefer these over
# iso-8859-10, but do not want to accidentally promote an unrelated encoding
# (e.g. windows-1254).
_COMMON_LATIN_ENCODINGS: frozenset[str] = frozenset(
    {
        "iso-8859-1",
        "iso-8859-15",
        "windows-1252",
    }
)

# Bytes where iso-8859-10 decodes to a different character than iso-8859-1.
# Computed programmatically via:
#   {b for b in range(0x80, 0x100)
#    if bytes([b]).decode('iso-8859-10') != bytes([b]).decode('iso-8859-1')}
# If none of these bytes are present in the data, iso-8859-10 is
# indistinguishable from more common Latin encodings, so we demote it.
_ISO_8859_10_DISTINGUISHING: frozenset[int] = frozenset(
    {
        0xA1,
        0xA2,
        0xA3,
        0xA4,
        0xA5,
        0xA6,
        0xA8,
        0xA9,
        0xAA,
        0xAB,
        0xAC,
        0xAE,
        0xAF,
        0xB1,
        0xB2,
        0xB3,
        0xB4,
        0xB5,
        0xB6,
        0xB8,
        0xB9,
        0xBA,
        0xBB,
        0xBC,
        0xBD,
        0xBE,
        0xBF,
        0xC0,
        0xC7,
        0xC8,
        0xCA,
        0xCC,
        0xD1,
        0xD2,
        0xD7,
        0xD9,
        0xE0,
        0xE7,
        0xE8,
        0xEA,
        0xEC,
        0xF1,
        0xF2,
        0xF7,
        0xF9,
        0xFF,
    }
)


def _has_iso_8859_10_evidence(data: bytes) -> bool:
    """Return True if data contains bytes unique to iso-8859-10.

    Checks whether any non-ASCII byte in *data* falls in the set of byte
    values that decode differently under iso-8859-10 vs iso-8859-1.  If none
    do, the data is equally valid under both encodings and there is no
    byte-level evidence for preferring iso-8859-10.
    """
    return any(b in _ISO_8859_10_DISTINGUISHING for b in data if b > 0x7F)


# Minimum structural score (valid multi-byte sequences / lead bytes) required
# to keep a CJK multi-byte candidate.  Below this threshold the encoding is
# eliminated as a false positive (e.g. Shift_JIS matching Latin data where
# scattered high bytes look like lead bytes but rarely form valid pairs).
_CJK_MIN_MB_RATIO = 0.05
# Minimum number of non-ASCII bytes required for a CJK candidate to survive
# gating.  Files with very few high bytes can accidentally form valid
# multi-byte pairs and score 1.0 structurally; requiring a minimum count
# prevents these tiny-sample false positives.  The lowest true-positive CJK
# file in the test suite has 8 non-ASCII bytes (EUC-JP).
_CJK_MIN_NON_ASCII = 6
# Minimum ratio of non-ASCII bytes that must participate in valid multi-byte
# sequences for a CJK candidate to survive gating.  Genuine CJK text has
# nearly all non-ASCII bytes in valid pairs (coverage >= 0.95); Latin text
# with scattered high bytes has many orphan bytes (coverage often < 0.5).
# The lowest true-positive coverage in the test suite is ~0.39 (a CP932 HTML
# file with many half-width katakana).
_CJK_MIN_BYTE_COVERAGE = 0.35


def _gate_cjk_candidates(
    data: bytes,
    valid_candidates: list,
) -> tuple[list, dict[str, float]]:
    """Eliminate CJK multi-byte candidates that lack genuine multi-byte structure.

    Three checks are applied in order to each multi-byte candidate:

    1. **Structural pair ratio** (valid_pairs / lead_bytes) must be
       >= ``_CJK_MIN_MB_RATIO``.  Catches files with many orphan lead bytes.

    2. **Minimum non-ASCII byte count**: the data must contain at least
       ``_CJK_MIN_NON_ASCII`` bytes > 0x7F.  Tiny files with 1-5 high bytes
       can accidentally form perfect pairs and score 1.0 structurally.

    3. **Byte coverage** (non-ASCII bytes in valid multi-byte sequences /
       total non-ASCII bytes) must be >= ``_CJK_MIN_BYTE_COVERAGE``.  Latin
       text has many high bytes that are NOT consumed by multi-byte pairs;
       genuine CJK text has nearly all high bytes accounted for.

    Returns the filtered candidate list and a dict of cached structural
    scores for reuse in Stage 2b.
    """
    non_ascii_count = sum(1 for b in data if b > 0x7F)
    mb_scores: dict[str, float] = {}
    gated: list = []
    for enc in valid_candidates:
        if enc.is_multibyte:
            mb_score = compute_structural_score(data, enc)
            mb_scores[enc.name] = mb_score
            if mb_score < _CJK_MIN_MB_RATIO:
                continue  # No multi-byte structure -> eliminate
            if non_ascii_count < _CJK_MIN_NON_ASCII:
                continue  # Too few high bytes to trust the score
            byte_coverage = compute_multibyte_byte_coverage(data, enc)
            if byte_coverage < _CJK_MIN_BYTE_COVERAGE:
                continue  # Most high bytes are orphans -> not CJK
        gated.append(enc)
    return gated, mb_scores


def _apply_mess_penalty(
    data: bytes, results: list[DetectionResult]
) -> list[DetectionResult]:
    """Penalize candidates that produce messy Unicode when decoded.

    Decodes *data* with each candidate encoding and computes a mess score.
    Confidence is reduced proportionally to the mess score.  Results are
    re-sorted by adjusted confidence.
    """
    if len(results) <= 1:
        return results

    scored_results: list[DetectionResult] = []
    for r in results:
        if r.encoding is None:
            scored_results.append(r)
            continue
        try:
            decoded = data.decode(r.encoding)
            mess = compute_mess_score(decoded)
        except (UnicodeDecodeError, LookupError):
            mess = 1.0
        adjusted_confidence = r.confidence * (1.0 - mess)
        scored_results.append(
            DetectionResult(
                encoding=r.encoding,
                confidence=max(adjusted_confidence, 0.01),
                language=r.language,
            )
        )
    scored_results.sort(key=lambda r: r.confidence, reverse=True)
    return scored_results


def run_pipeline(
    data: bytes,
    encoding_era: EncodingEra,
    max_bytes: int = 200_000,
) -> list[DetectionResult]:
    """Run the full detection pipeline. Returns list of results sorted by confidence."""
    data = data[:max_bytes]

    if not data:
        return [_FALLBACK_RESULT]

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
        return [_BINARY_RESULT]

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
        return [_FALLBACK_RESULT]

    # Gate: eliminate CJK multi-byte candidates that lack genuine
    # multi-byte structure.  Cache structural scores for Stage 2b.
    valid_candidates, mb_scores = _gate_cjk_candidates(data, valid_candidates)

    if not valid_candidates:
        return [_FALLBACK_RESULT]

    # Stage 2b: Structural probing for multi-byte encodings
    # Reuse scores already computed during the CJK gate above.
    structural_scores: list[tuple[str, float]] = []
    for enc in valid_candidates:
        if enc.is_multibyte:
            score = mb_scores.get(enc.name)
            if score is None:
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
        return [_FALLBACK_RESULT]

    # Post-decode mess detection: penalize candidates that produce messy Unicode
    results = _apply_mess_penalty(data, results)

    # Demote iso-8859-10 if no distinguishing bytes present.
    # The iso-8859-10 bigram model can win on data that contains only bytes
    # shared with iso-8859-1 / iso-8859-15 / windows-1252.  When there is no
    # byte-level evidence for iso-8859-10, promote the first common Western
    # Latin candidate to the top, keep all other results in their original
    # confidence order, and push iso-8859-10 to last.  We restrict the
    # promotion target to common Latin encodings to avoid accidentally
    # promoting unrelated encodings like windows-1254.
    #
    # Note: this only applies to the statistical scoring path (Stage 3).
    # The structural early-return path (Stage 2b) is unaffected because
    # iso-8859-10 is a single-byte encoding and cannot win that path.
    if (
        len(results) > 1
        and results[0].encoding == "iso-8859-10"
        and not _has_iso_8859_10_evidence(data)
    ):
        for r in results[1:]:
            if r.encoding in _COMMON_LATIN_ENCODINGS:
                others = [
                    x for x in results if x.encoding != "iso-8859-10" and x is not r
                ]
                iso_entries = [x for x in results if x.encoding == "iso-8859-10"]
                results = [r, *others, *iso_entries]
                break

    return results
