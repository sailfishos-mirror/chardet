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
