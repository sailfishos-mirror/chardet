"""Tests for Stage 2b: Multi-byte structural probing."""

from chardet.pipeline.structural import compute_structural_score
from chardet.registry import REGISTRY


def _get_encoding(name: str):
    return next(e for e in REGISTRY if e.name == name)


def test_shift_jis_scores_high_on_shift_jis_data():
    data = "こんにちは世界".encode("shift_jis")
    score = compute_structural_score(data, _get_encoding("shift_jis"))
    assert score > 0.7


def test_euc_jp_scores_high_on_euc_jp_data():
    data = "こんにちは世界".encode("euc-jp")
    score = compute_structural_score(data, _get_encoding("euc-jp"))
    assert score > 0.7


def test_shift_jis_scores_low_on_euc_jp_data():
    data = "こんにちは世界".encode("euc-jp")
    euc_score = compute_structural_score(data, _get_encoding("euc-jp"))
    sjis_score = compute_structural_score(data, _get_encoding("shift_jis"))
    assert euc_score > sjis_score


def test_euc_kr_scores_high_on_korean_data():
    data = "안녕하세요".encode("euc-kr")
    score = compute_structural_score(data, _get_encoding("euc-kr"))
    assert score > 0.7


def test_gb18030_scores_high_on_chinese_data():
    data = "你好世界".encode("gb18030")
    score = compute_structural_score(data, _get_encoding("gb18030"))
    assert score > 0.7


def test_big5_scores_high_on_big5_data():
    data = "你好世界".encode("big5")
    score = compute_structural_score(data, _get_encoding("big5"))
    assert score > 0.7


def test_single_byte_encoding_returns_zero():
    data = b"Hello world"
    enc = _get_encoding("iso-8859-1")
    score = compute_structural_score(data, enc)
    assert score == 0.0


def test_empty_data_returns_zero():
    score = compute_structural_score(b"", _get_encoding("shift_jis"))
    assert score == 0.0
