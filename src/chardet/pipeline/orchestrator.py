"""Pipeline orchestrator — runs all detection stages in sequence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from chardet.models import infer_language
from chardet.pipeline import DetectionResult
from chardet.pipeline.ascii import detect_ascii
from chardet.pipeline.binary import is_binary
from chardet.pipeline.bom import detect_bom
from chardet.pipeline.confusion import resolve_confusion_groups
from chardet.pipeline.escape import detect_escape_encoding
from chardet.pipeline.markup import detect_markup_charset
from chardet.pipeline.statistical import score_candidates
from chardet.pipeline.structural import (
    clear_analysis_cache,
    compute_lead_byte_diversity,
    compute_multibyte_byte_coverage,
    compute_structural_score,
)
from chardet.pipeline.utf8 import detect_utf8
from chardet.pipeline.utf1632 import detect_utf1632_patterns
from chardet.pipeline.validity import filter_by_validity
from chardet.registry import get_candidates

if TYPE_CHECKING:
    from chardet.enums import EncodingEra
    from chardet.registry import EncodingInfo

# Byte table for fast non-ASCII counting (C-speed via bytes.translate).
_HIGH_BYTES: bytes = bytes(range(0x80, 0x100))

_BINARY_RESULT = DetectionResult(encoding=None, confidence=0.95, language=None)
_EMPTY_RESULT = DetectionResult(encoding="utf-8", confidence=0.10, language=None)
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

# Bytes where iso-8859-14 decodes to a different character than iso-8859-1.
# Computed programmatically via:
#   {b for b in range(0x80, 0x100)
#    if bytes([b]).decode('iso-8859-14') != bytes([b]).decode('iso-8859-1')}
_ISO_8859_14_DISTINGUISHING: frozenset[int] = frozenset(
    {
        0xA1,
        0xA2,
        0xA4,
        0xA5,
        0xA6,
        0xA8,
        0xAA,
        0xAB,
        0xAC,
        0xAF,
        0xB0,
        0xB1,
        0xB2,
        0xB3,
        0xB4,
        0xB5,
        0xB7,
        0xB8,
        0xB9,
        0xBA,
        0xBB,
        0xBC,
        0xBD,
        0xBE,
        0xBF,
        0xD0,
        0xD7,
        0xDE,
        0xF0,
        0xF7,
        0xFE,
    }
)

# Bytes where windows-1254 has Turkish-specific characters that differ from
# windows-1252.  The C1 range (0x80-0x9F) is shared between windows-1252
# and windows-1254 (smart quotes, dashes, etc.), so only the six Turkish
# letter positions matter: 0xD0, 0xDD, 0xDE, 0xF0, 0xFD, 0xFE.
_WINDOWS_1254_DISTINGUISHING: frozenset[int] = frozenset(
    {0xD0, 0xDD, 0xDE, 0xF0, 0xFD, 0xFE}
)

# Encodings that are often false positives when their distinguishing bytes
# are absent.  Keyed by encoding name -> frozenset of byte values where
# that encoding differs from iso-8859-1 (or windows-1252 in the case of
# windows-1254).
_DEMOTION_CANDIDATES: dict[str, frozenset[int]] = {
    "iso-8859-10": _ISO_8859_10_DISTINGUISHING,
    "iso-8859-14": _ISO_8859_14_DISTINGUISHING,
    "windows-1254": _WINDOWS_1254_DISTINGUISHING,
}

# Bytes where KOI8-T maps to Tajik-specific Cyrillic letters but KOI8-R
# maps to box-drawing characters.  Presence of any of these bytes is strong
# evidence for KOI8-T over KOI8-R.
_KOI8_T_DISTINGUISHING: frozenset[int] = frozenset(
    {0x80, 0x81, 0x83, 0x8A, 0x8C, 0x8D, 0x8E, 0x90, 0xA1, 0xA2, 0xA5, 0xB5}
)


def _should_demote(encoding: str, data: bytes) -> bool:
    """Return True if encoding is a demotion candidate with no distinguishing bytes.

    Checks whether any non-ASCII byte in *data* falls in the set of byte
    values that decode differently under the given encoding vs iso-8859-1.
    If none do, the data is equally valid under both encodings and there is
    no byte-level evidence for preferring the candidate encoding.
    """
    distinguishing = _DEMOTION_CANDIDATES.get(encoding)
    if distinguishing is None:
        return False
    return not any(b in distinguishing for b in data if b > 0x7F)


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
# Minimum number of distinct lead byte values for a CJK candidate to
# survive gating.  Genuine CJK text uses a wide range of lead bytes;
# European false positives cluster in a narrow band.  Only applied when
# there are enough non-ASCII bytes to expect diversity (see
# _CJK_DIVERSITY_MIN_NON_ASCII).
_CJK_MIN_LEAD_DIVERSITY = 4
# Minimum non-ASCII byte count before applying the lead diversity gate.
# Very small files (e.g. 8 non-ASCII bytes) may genuinely have low
# diversity even for real CJK text (e.g. repeated katakana).
_CJK_DIVERSITY_MIN_NON_ASCII = 16


def _gate_cjk_candidates(
    data: bytes,
    valid_candidates: tuple[EncodingInfo, ...],
) -> tuple[tuple[EncodingInfo, ...], dict[str, float]]:
    """Eliminate CJK multi-byte candidates that lack genuine multi-byte structure.

    Four checks are applied in order to each multi-byte candidate:

    1. **Structural pair ratio** (valid_pairs / lead_bytes) must be
       >= ``_CJK_MIN_MB_RATIO``.  Catches files with many orphan lead bytes.

    2. **Minimum non-ASCII byte count**: the data must contain at least
       ``_CJK_MIN_NON_ASCII`` bytes > 0x7F.  Tiny files with 1-5 high bytes
       can accidentally form perfect pairs and score 1.0 structurally.

    3. **Byte coverage** (non-ASCII bytes in valid multi-byte sequences /
       total non-ASCII bytes) must be >= ``_CJK_MIN_BYTE_COVERAGE``.  Latin
       text has many high bytes that are NOT consumed by multi-byte pairs;
       genuine CJK text has nearly all high bytes accounted for.

    4. **Lead byte diversity**: the number of distinct lead byte values in
       valid pairs must be >= ``_CJK_MIN_LEAD_DIVERSITY``.  Genuine CJK text
       draws from a wide repertoire of lead bytes; European false positives
       cluster in a narrow band (e.g. 0xC0-0xDF for accented Latin).

    Returns the filtered candidate list and a dict of cached structural
    scores for reuse in Stage 2b.
    """
    non_ascii_count = -1  # Lazy; computed only when needed
    mb_scores: dict[str, float] = {}
    gated: list[EncodingInfo] = []
    for enc in valid_candidates:
        if enc.is_multibyte:
            mb_score = compute_structural_score(data, enc)
            mb_scores[enc.name] = mb_score
            if mb_score < _CJK_MIN_MB_RATIO:
                continue  # No multi-byte structure -> eliminate
            if non_ascii_count < 0:
                non_ascii_count = len(data) - len(data.translate(None, _HIGH_BYTES))
            if non_ascii_count < _CJK_MIN_NON_ASCII:
                continue  # Too few high bytes to trust the score
            byte_coverage = compute_multibyte_byte_coverage(
                data, enc, non_ascii_count=non_ascii_count
            )
            if byte_coverage < _CJK_MIN_BYTE_COVERAGE:
                continue  # Most high bytes are orphans -> not CJK
            if non_ascii_count >= _CJK_DIVERSITY_MIN_NON_ASCII:
                lead_diversity = compute_lead_byte_diversity(data, enc)
                if lead_diversity < _CJK_MIN_LEAD_DIVERSITY:
                    continue  # Too few distinct lead bytes -> not CJK
        gated.append(enc)
    return tuple(gated), mb_scores


def _score_structural_candidates(
    data: bytes,
    structural_scores: list[tuple[str, float]],
    valid_candidates: tuple[EncodingInfo, ...],
) -> list[DetectionResult]:
    """Score structurally-valid CJK candidates using statistical bigrams.

    When multiple CJK encodings score equally high structurally, statistical
    scoring differentiates them (e.g. euc-jp vs big5 for Japanese data).
    Single-byte candidates are also scored and included so that the caller
    can compare CJK vs single-byte confidence.
    """
    enc_lookup = {e.name: e for e in valid_candidates if e.is_multibyte}
    valid_mb = tuple(
        enc_lookup[name] for name, _sc in structural_scores if name in enc_lookup
    )
    single_byte = tuple(e for e in valid_candidates if not e.is_multibyte)
    return list(score_candidates(data, (*valid_mb, *single_byte)))


def _demote_niche_latin(
    data: bytes,
    results: list[DetectionResult],
) -> list[DetectionResult]:
    """Demote niche Latin encodings when no distinguishing bytes are present.

    Some bigram models (e.g. iso-8859-10, iso-8859-14, windows-1254) can win
    on data that contains only bytes shared with common Western Latin
    encodings.  When there is no byte-level evidence for the winning
    encoding, promote the first common Western Latin candidate to the top and
    push the demoted encoding to last.
    """
    if (
        len(results) > 1
        and results[0].encoding is not None
        and _should_demote(results[0].encoding, data)
    ):
        demoted_encoding = results[0].encoding
        for r in results[1:]:
            if r.encoding in _COMMON_LATIN_ENCODINGS:
                others = [
                    x for x in results if x.encoding != demoted_encoding and x is not r
                ]
                demoted_entries = [x for x in results if x.encoding == demoted_encoding]
                return [r, *others, *demoted_entries]
    return results


def _promote_koi8t(
    data: bytes,
    results: list[DetectionResult],
) -> list[DetectionResult]:
    """Promote KOI8-T over KOI8-R when Tajik-specific bytes are present.

    KOI8-T and KOI8-R share the entire 0xC0-0xFF Cyrillic letter block,
    making statistical discrimination difficult.  However, KOI8-T maps 12
    bytes in 0x80-0xBF to Tajik-specific Cyrillic letters where KOI8-R has
    box-drawing characters.  If any of these bytes appear, KOI8-T is the
    better match.
    """
    if not results or results[0].encoding != "koi8-r":
        return results
    # Check if KOI8-T is anywhere in the results
    koi8t_idx = None
    for i, r in enumerate(results):
        if r.encoding == "koi8-t":
            koi8t_idx = i
            break
    if koi8t_idx is None:
        return results
    # Check for Tajik-specific bytes
    if any(b in _KOI8_T_DISTINGUISHING for b in data if b > 0x7F):
        koi8t_result = results[koi8t_idx]
        others = [r for i, r in enumerate(results) if i != koi8t_idx]
        return [koi8t_result, *others]
    return results


def _fill_language(results: list[DetectionResult]) -> list[DetectionResult]:
    """Fill in language for results where encoding implies a single language."""
    filled: list[DetectionResult] = []
    for result in results:
        if result.language is None and result.encoding is not None:
            lang = infer_language(result.encoding)
            if lang is not None:
                filled.append(
                    DetectionResult(
                        encoding=result.encoding,
                        confidence=result.confidence,
                        language=lang,
                    )
                )
                continue
        filled.append(result)
    return filled


def _run_pipeline_core(
    data: bytes,
    encoding_era: EncodingEra,
    max_bytes: int = 200_000,
) -> list[DetectionResult]:
    """Core pipeline logic. Returns list of results sorted by confidence."""
    clear_analysis_cache()
    data = data[:max_bytes]

    if not data:
        return [_EMPTY_RESULT]

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

    # If a multi-byte encoding scored very high, score all candidates
    # (CJK + single-byte) statistically.
    if structural_scores:
        structural_scores.sort(key=lambda x: x[1], reverse=True)
        _, best_score = structural_scores[0]
        if best_score >= _STRUCTURAL_CONFIDENCE_THRESHOLD:
            results = _score_structural_candidates(
                data, structural_scores, valid_candidates
            )
            results = resolve_confusion_groups(data, results)
            results = _demote_niche_latin(data, results)
            return _promote_koi8t(data, results)

    # Stage 3: Statistical scoring for all remaining candidates
    results = list(score_candidates(data, tuple(valid_candidates)))
    if not results:
        return [_FALLBACK_RESULT]

    results = resolve_confusion_groups(data, results)
    results = _demote_niche_latin(data, results)
    return _promote_koi8t(data, results)


def run_pipeline(
    data: bytes,
    encoding_era: EncodingEra,
    max_bytes: int = 200_000,
) -> list[DetectionResult]:
    """Run the full detection pipeline. Returns list of results sorted by confidence."""
    results = _run_pipeline_core(data, encoding_era, max_bytes)
    return _fill_language(results)
