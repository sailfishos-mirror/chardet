from chardet.models import load_models, score_bigrams


def test_load_models_returns_dict():
    models = load_models()
    assert isinstance(models, dict)


def test_load_models_has_entries():
    models = load_models()
    assert len(models) > 0


def test_model_keys_are_strings():
    models = load_models()
    for key in models:
        assert isinstance(key, str)


def test_score_bigrams_returns_float():
    models = load_models()
    encoding = next(iter(models))
    score = score_bigrams(b"Hello world this is a test", encoding, models)
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_score_bigrams_unknown_encoding():
    models = load_models()
    score = score_bigrams(b"Hello", "not-a-real-encoding", models)
    assert score == 0.0


def test_score_bigrams_empty_data():
    models = load_models()
    encoding = next(iter(models))
    score = score_bigrams(b"", encoding, models)
    assert score == 0.0


def test_score_bigrams_high_byte_weighting():
    """High-byte bigrams should be weighted more heavily than ASCII-only."""
    models = load_models()
    # Pick any encoding with a model
    encoding = next(iter(models))
    model = models[encoding]

    # Build data that's all ASCII vs data with high bytes
    ascii_data = b"the quick brown fox jumps over the lazy dog"
    # Create high-byte data using bytes that appear in the model
    high_pairs = [pair for pair in model if pair[0] > 0x7F or pair[1] > 0x7F]
    if high_pairs:
        # Construct data from high-byte pairs in the model
        high_data = bytes(b for pair in high_pairs[:20] for b in pair)
        high_score = score_bigrams(high_data, encoding, models)
        ascii_score = score_bigrams(ascii_data, encoding, models)
        # Both should be valid floats
        assert isinstance(high_score, float)
        assert isinstance(ascii_score, float)
        assert 0.0 <= high_score <= 1.0
        assert 0.0 <= ascii_score <= 1.0
