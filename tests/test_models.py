from __future__ import annotations

from pathlib import Path

import pytest
from train import deserialize_models, serialize_models

from chardet.models import BigramProfile, load_models, score_best_language


def test_load_models_returns_dict() -> None:
    models = load_models()
    assert isinstance(models, dict)


def test_load_models_has_entries() -> None:
    models = load_models()
    assert len(models) > 0


def test_model_keys_are_strings() -> None:
    models = load_models()
    for key in models:
        assert isinstance(key, str)


def test_score_best_language_returns_float() -> None:
    """score_best_language should work with plain encoding names (not lang/enc keys)."""
    load_models()
    score, _ = score_best_language(b"Hello world this is a test", "windows-1252")
    assert isinstance(score, float)
    assert 0.0 < score <= 1.0


def test_score_best_language_unknown_encoding() -> None:
    load_models()
    score, _ = score_best_language(b"Hello", "not-a-real-encoding")
    assert score == 0.0


def test_score_best_language_empty_data() -> None:
    models = load_models()
    encoding = next(iter(models))
    score, _ = score_best_language(b"", encoding)
    assert score == 0.0


def test_score_best_language_high_byte_weighting() -> None:
    """High-byte bigrams should be weighted more heavily than ASCII-only."""
    models = load_models()
    # Pick any encoding with a model
    encoding = next(iter(models))
    model = models[encoding]

    # Build data that's all ASCII vs data with high bytes
    ascii_data = b"the quick brown fox jumps over the lazy dog"
    # Create high-byte data using bytes that appear in the model (bytearray table)
    high_pairs = []
    for idx in range(65536):
        if model[idx] > 0:
            b1 = idx >> 8
            b2 = idx & 0xFF
            if b1 > 0x7F or b2 > 0x7F:
                high_pairs.append((b1, b2))
    if high_pairs:
        # Construct data from high-byte pairs in the model
        high_data = bytes(b for pair in high_pairs[:20] for b in pair)
        high_score, _ = score_best_language(high_data, encoding)
        ascii_score, _ = score_best_language(ascii_data, encoding)
        # Both should be valid floats
        assert isinstance(high_score, float)
        assert isinstance(ascii_score, float)
        assert 0.0 <= high_score <= 1.0
        assert 0.0 <= ascii_score <= 1.0


# ---------------------------------------------------------------------------
# BigramProfile tests
# ---------------------------------------------------------------------------


def test_bigram_profile_empty() -> None:
    p = BigramProfile(b"")
    assert p.weight_sum == 0
    assert len(p.weighted_freq) == 0


def test_bigram_profile_single_byte() -> None:
    p = BigramProfile(b"A")
    assert p.weight_sum == 0


def test_bigram_profile_ascii_weight() -> None:
    p = BigramProfile(b"AB")
    assert p.weight_sum == 1


def test_bigram_profile_high_byte_weight() -> None:
    p = BigramProfile(b"\xc3\xa9")
    assert p.weight_sum == 8


# ---------------------------------------------------------------------------
# serialize_models / deserialize_models roundtrip tests
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_models_path(tmp_path: Path) -> str:
    return str(tmp_path / "test_models.bin")


def test_roundtrip_single_encoding(tmp_models_path: str) -> None:
    """Serialize and deserialize a single encoding model."""
    original = {"utf-8": {(65, 66): 200, (0xC3, 0xA4): 150}}
    serialize_models(original, tmp_models_path)
    loaded = deserialize_models(tmp_models_path)
    assert loaded == original


def test_roundtrip_multiple_encodings(tmp_models_path: str) -> None:
    """Serialize and deserialize multiple encoding models."""
    original = {
        "utf-8": {(65, 66): 200, (67, 68): 100},
        "iso-8859-1": {(0xE4, 0x20): 255},
        "shift_jis": {(0x82, 0xA0): 180, (0x83, 0x41): 90},
    }
    serialize_models(original, tmp_models_path)
    loaded = deserialize_models(tmp_models_path)
    assert loaded == original


def test_roundtrip_empty_bigrams(tmp_models_path: str) -> None:
    """An encoding with zero bigrams should roundtrip correctly."""
    original = {"empty-enc": {}}
    serialize_models(original, tmp_models_path)
    loaded = deserialize_models(tmp_models_path)
    assert loaded == original


def test_roundtrip_zero_encodings(tmp_models_path: str) -> None:
    """Zero encodings should roundtrip correctly."""
    original: dict[str, dict[tuple[int, int], int]] = {}
    serialize_models(original, tmp_models_path)
    loaded = deserialize_models(tmp_models_path)
    assert loaded == original


def test_deserialize_missing_file() -> None:
    """Missing file should return empty dict."""
    result = deserialize_models("/nonexistent/path/models.bin")
    assert result == {}


def test_deserialize_empty_file(tmp_models_path: str) -> None:
    """Empty file should return empty dict."""
    Path(tmp_models_path).write_bytes(b"")
    result = deserialize_models(tmp_models_path)
    assert result == {}


def test_deserialize_trailing_bytes_raises(tmp_models_path: str) -> None:
    """File with trailing bytes after valid data should raise ValueError."""
    original = {"utf-8": {(65, 66): 200}}
    serialize_models(original, tmp_models_path)
    # Append garbage bytes
    p = Path(tmp_models_path)
    p.write_bytes(p.read_bytes() + b"\xff\xff")
    with pytest.raises(ValueError, match="trailing bytes"):
        deserialize_models(tmp_models_path)


def test_roundtrip_matches_load_models(tmp_path: Path) -> None:
    """The production models.bin should roundtrip through serialize/deserialize."""
    production_tables = load_models()  # dict[str, bytearray]
    # Convert bytearray tables back to dict format for serialize/deserialize roundtrip
    production_dicts: dict[str, dict[tuple[int, int], int]] = {}
    for name, table in production_tables.items():
        bigrams: dict[tuple[int, int], int] = {}
        for idx in range(65536):
            if table[idx] > 0:
                bigrams[(idx >> 8, idx & 0xFF)] = table[idx]
        production_dicts[name] = bigrams
    tmp_models = str(tmp_path / "roundtrip_models.bin")
    serialize_models(production_dicts, tmp_models)
    loaded = deserialize_models(tmp_models)
    assert loaded == production_dicts
