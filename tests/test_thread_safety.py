"""Thread-safety integration tests for concurrent detect() calls."""

from __future__ import annotations

import threading

import pytest

from chardet import detect
from chardet.enums import EncodingEra

# Acceptable encoding sets for each test sample.
_JAPANESE_ENCODINGS = frozenset({"shift_jis", "cp932"})
_GERMAN_ENCODINGS = frozenset(
    {"windows-1252", "iso-8859-1", "iso-8859-15", "iso-8859-9", "windows-1254"}
)
_CHINESE_ENCODINGS = frozenset({"gb18030", "gb2312"})

# Test data shared across tests.
_JAPANESE = "これはテストです。日本語のテキスト。".encode("shift_jis")
_GERMAN = (
    "Die Größe des Gebäudes überraschte die Besucher. Natürlich können wir das ändern."
).encode("windows-1252")
_CHINESE = "这是中文测试文本，用于并发检测。".encode("gb18030")

_SAMPLES: list[tuple[bytes, frozenset[str]]] = [
    (_JAPANESE, _JAPANESE_ENCODINGS),
    (_GERMAN, _GERMAN_ENCODINGS),
    (_CHINESE, _CHINESE_ENCODINGS),
]


def _run_concurrent_detect(
    n_workers: int,
    iterations: int,
) -> list[str]:
    """Spawn *n_workers* threads per sample, each calling detect() *iterations* times.

    Returns a list of error strings (empty = success).
    """
    errors: list[str] = []
    barrier = threading.Barrier(n_workers * len(_SAMPLES))

    def worker(data: bytes, expected: frozenset[str]) -> None:
        barrier.wait()
        for _ in range(iterations):
            result = detect(data, encoding_era=EncodingEra.ALL)
            enc = result["encoding"]
            if enc is not None:
                enc = enc.lower()
            if enc not in expected:
                errors.append(f"Expected one of {expected}, got {enc!r}")

    threads = []
    for _ in range(n_workers):
        for data, expected in _SAMPLES:
            t = threading.Thread(target=worker, args=(data, expected))
            threads.append(t)
            t.start()

    for t in threads:
        t.join()

    return errors


def test_concurrent_detect_no_corruption():
    """Multiple threads calling detect() simultaneously must not corrupt results."""
    errors = _run_concurrent_detect(n_workers=3, iterations=20)
    assert not errors, "Thread-safety violations:\n" + "\n".join(errors[:10])


def test_concurrent_detect_high_concurrency():
    """Stress test with higher thread count to surface free-threading races."""
    errors = _run_concurrent_detect(n_workers=8, iterations=10)
    assert not errors, "Thread-safety violations:\n" + "\n".join(errors[:10])


@pytest.mark.serial
def test_cold_cache_concurrent_init():
    """Race on first-call cache initialization from a cold state.

    Clears all functools.cache-backed caches, then has many threads
    simultaneously call detect().  This stresses the cache population
    path — the most dangerous codepath for thread safety.

    Marked ``serial`` because the global cache mutations are not safe to
    run concurrently with other tests that call ``detect()``.
    """
    import chardet.models as _models
    import chardet.pipeline.confusion as _confusion
    import chardet.registry as _registry

    try:
        # Clear all caches to cold state.
        _models._load_models_data.cache_clear()
        _models.get_enc_index.cache_clear()
        _confusion.load_confusion_data.cache_clear()
        _registry.lookup_encoding.cache_clear()
        _registry.get_candidates.cache_clear()

        errors = _run_concurrent_detect(n_workers=6, iterations=5)
        assert not errors, "Cold-cache race violations:\n" + "\n".join(errors[:10])
    finally:
        # Clear and let caches re-populate naturally on next use.
        _models._load_models_data.cache_clear()
        _models.get_enc_index.cache_clear()
        _confusion.load_confusion_data.cache_clear()
        _registry.lookup_encoding.cache_clear()
        _registry.get_candidates.cache_clear()
