"""Tests for era-based tiebreaking."""

from chardet.enums import ERA_PRIORITY, EncodingEra
from chardet.pipeline import DetectionResult
from chardet.pipeline.orchestrator import _apply_era_tiebreak
from chardet.registry import EncodingInfo


def _make_enc(name: str, era: EncodingEra) -> EncodingInfo:
    """Create a minimal EncodingInfo for testing."""
    return EncodingInfo(
        name=name,
        aliases=(),
        era=era,
        is_multibyte=False,
        python_codec=name,
    )


def test_era_priority_exists():
    """ERA_PRIORITY mapping should exist and cover all non-ALL eras."""
    assert EncodingEra.MODERN_WEB in ERA_PRIORITY
    assert EncodingEra.LEGACY_ISO in ERA_PRIORITY
    assert EncodingEra.LEGACY_MAC in ERA_PRIORITY
    assert EncodingEra.LEGACY_REGIONAL in ERA_PRIORITY
    assert EncodingEra.DOS in ERA_PRIORITY
    assert EncodingEra.MAINFRAME in ERA_PRIORITY
    # MODERN_WEB should have highest priority (lowest number)
    assert ERA_PRIORITY[EncodingEra.MODERN_WEB] < ERA_PRIORITY[EncodingEra.LEGACY_MAC]


def test_tiebreak_prefers_modern_web_over_legacy_mac():
    """When scores are within 10%, prefer MODERN_WEB over LEGACY_MAC."""
    candidates = (
        _make_enc("mac-latin2", EncodingEra.LEGACY_MAC),
        _make_enc("windows-1250", EncodingEra.MODERN_WEB),
    )
    results = [
        DetectionResult(encoding="mac-latin2", confidence=0.95, language=None),
        DetectionResult(encoding="windows-1250", confidence=0.90, language=None),
    ]
    reordered = _apply_era_tiebreak(results, candidates, EncodingEra.ALL)
    assert reordered[0].encoding == "windows-1250"


def test_tiebreak_no_swap_when_gap_too_large():
    """When scores differ by more than 10%, do NOT swap."""
    candidates = (
        _make_enc("mac-latin2", EncodingEra.LEGACY_MAC),
        _make_enc("windows-1250", EncodingEra.MODERN_WEB),
    )
    results = [
        DetectionResult(encoding="mac-latin2", confidence=0.95, language=None),
        DetectionResult(encoding="windows-1250", confidence=0.80, language=None),
    ]
    reordered = _apply_era_tiebreak(results, candidates, EncodingEra.ALL)
    assert reordered[0].encoding == "mac-latin2"


def test_tiebreak_prefers_legacy_iso_over_dos():
    """Among close scores, prefer LEGACY_ISO over DOS."""
    candidates = (
        _make_enc("cp852", EncodingEra.DOS),
        _make_enc("iso-8859-2", EncodingEra.LEGACY_ISO),
    )
    results = [
        DetectionResult(encoding="cp852", confidence=0.90, language=None),
        DetectionResult(encoding="iso-8859-2", confidence=0.88, language=None),
    ]
    reordered = _apply_era_tiebreak(results, candidates, EncodingEra.ALL)
    assert reordered[0].encoding == "iso-8859-2"


def test_tiebreak_single_result_unchanged():
    """A single result should be returned unchanged."""
    candidates = (_make_enc("windows-1252", EncodingEra.MODERN_WEB),)
    results = [
        DetectionResult(encoding="windows-1252", confidence=0.95, language=None),
    ]
    reordered = _apply_era_tiebreak(results, candidates, EncodingEra.ALL)
    assert len(reordered) == 1
    assert reordered[0].encoding == "windows-1252"


def test_tiebreak_empty_results():
    """Empty results should be returned as-is."""
    reordered = _apply_era_tiebreak([], (), EncodingEra.ALL)
    assert reordered == []


def test_tiebreak_zero_confidence_unchanged():
    """Results with zero confidence should not be reordered."""
    candidates = (
        _make_enc("mac-latin2", EncodingEra.LEGACY_MAC),
        _make_enc("windows-1250", EncodingEra.MODERN_WEB),
    )
    results = [
        DetectionResult(encoding="mac-latin2", confidence=0.0, language=None),
        DetectionResult(encoding="windows-1250", confidence=0.0, language=None),
    ]
    reordered = _apply_era_tiebreak(results, candidates, EncodingEra.ALL)
    assert reordered[0].encoding == "mac-latin2"


def test_tiebreak_same_era_no_swap():
    """When all candidates are in the same era, order should be preserved."""
    candidates = (
        _make_enc("windows-1252", EncodingEra.MODERN_WEB),
        _make_enc("windows-1251", EncodingEra.MODERN_WEB),
    )
    results = [
        DetectionResult(encoding="windows-1252", confidence=0.92, language=None),
        DetectionResult(encoding="windows-1251", confidence=0.90, language=None),
    ]
    reordered = _apply_era_tiebreak(results, candidates, EncodingEra.ALL)
    assert reordered[0].encoding == "windows-1252"


def test_modern_web_preferred_over_mac_integration():
    """Integration test: era tiebreaking should work through run_pipeline."""
    from chardet.pipeline.orchestrator import run_pipeline

    # Central European text that could match both iso-8859-2 and mac-latin2
    data = "Příliš žluťoučký kůň úpěl ďábelské ódy.".encode("iso-8859-2")
    result = run_pipeline(data, EncodingEra.ALL)
    # mac-latin2 (LEGACY_MAC) should not beat MODERN_WEB or LEGACY_ISO encodings
    assert result[0].encoding != "mac-latin2", (
        f"Expected a non-LEGACY_MAC encoding, got {result[0].encoding}"
    )
