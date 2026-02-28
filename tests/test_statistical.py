# tests/test_statistical.py
from __future__ import annotations

from chardet.enums import EncodingEra
from chardet.pipeline import DetectionResult
from chardet.pipeline.statistical import score_candidates
from chardet.registry import get_candidates


def test_score_candidates_returns_sorted_results():
    data = "Héllo wörld".encode("windows-1252")
    candidates = get_candidates(EncodingEra.MODERN_WEB)
    results = score_candidates(data, candidates)
    confidences = [r.confidence for r in results]
    assert confidences == sorted(confidences, reverse=True)


def test_score_candidates_returns_detection_results():
    data = b"Hello world"
    candidates = get_candidates(EncodingEra.MODERN_WEB)
    results = score_candidates(data, candidates)
    for r in results:
        assert isinstance(r, DetectionResult)


def test_score_candidates_empty_data():
    candidates = get_candidates(EncodingEra.MODERN_WEB)
    results = score_candidates(b"", candidates)
    assert len(results) == 0


def test_score_candidates_empty_candidates():
    results = score_candidates(b"Hello", ())
    assert len(results) == 0


def test_score_candidates_small_set_no_pool():
    candidates = tuple(
        e for e in get_candidates(EncodingEra.MODERN_WEB) if e.name == "utf-8"
    )
    results = score_candidates(b"Hello", candidates)
    assert len(results) <= len(candidates)


def test_correct_encoding_scores_highest():
    text = "Привет мир, как дела? Это тестовый текст на русском языке.".encode(
        "windows-1251"
    )
    candidates = get_candidates(EncodingEra.MODERN_WEB)
    results = score_candidates(text, candidates)
    assert len(results) > 0
    # windows-1251 should be among the top results
    top_names = [r.encoding for r in results[:3]]
    assert "windows-1251" in top_names


from chardet.models import BigramProfile, score_best_language  # noqa: E402


def test_bigram_profile_empty():
    p = BigramProfile(b"")
    assert p.weight_sum == 0
    assert len(p.weighted_freq) == 0


def test_bigram_profile_single_byte():
    p = BigramProfile(b"A")
    assert p.weight_sum == 0


def test_bigram_profile_ascii_weight():
    p = BigramProfile(b"AB")
    assert p.weight_sum == 1


def test_bigram_profile_high_byte_weight():
    p = BigramProfile(b"\xc3\xa9")
    assert p.weight_sum == 8


def test_score_best_language_returns_language():
    data = "Привет мир, это тест".encode("windows-1251")
    score, lang = score_best_language(data, "windows-1251")
    assert score > 0.0
    assert lang is not None
