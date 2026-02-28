"""Thread-safety integration tests for concurrent detect() calls."""

from __future__ import annotations

import sys
import threading

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
_CHINESE = "这是中文测试文本，用于并发检测。".encode("gb18030")  # noqa: RUF001

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


def test_cold_cache_concurrent_init():
    """Race on first-call cache initialization from a cold state.

    Resets all five load-once caches to their initial empty state, then
    has many threads simultaneously call detect().  This stresses the
    locking on the cache population path — the most dangerous codepath
    for thread safety.
    """
    import chardet.models as _models
    import chardet.pipeline.confusion as _confusion
    import chardet.registry as _registry

    # Save originals.
    saved = (
        _models._MODEL_CACHE,
        _models._ENC_INDEX,
        _models._MODEL_NORMS,
        _confusion._CONFUSION_CACHE,
        _registry._CANDIDATES_CACHE.copy(),
    )

    try:
        # Reset all caches to cold state.
        _models._MODEL_CACHE = None
        _models._ENC_INDEX = None
        _models._MODEL_NORMS = None
        _confusion._CONFUSION_CACHE = None
        _registry._CANDIDATES_CACHE.clear()

        errors = _run_concurrent_detect(n_workers=6, iterations=5)
        assert not errors, "Cold-cache race violations:\n" + "\n".join(errors[:10])
    finally:
        # Restore caches so subsequent tests aren't affected.
        _models._MODEL_CACHE = saved[0]
        _models._ENC_INDEX = saved[1]
        _models._MODEL_NORMS = saved[2]
        _confusion._CONFUSION_CACHE = saved[3]
        _registry._CANDIDATES_CACHE.clear()
        _registry._CANDIDATES_CACHE.update(saved[4])


def test_gil_status_diagnostic() -> None:
    """Report GIL status for visibility in CI logs.

    Not a correctness test — prints a diagnostic line so developers can
    see whether the test run exercised free-threaded or GIL-protected
    execution.
    """
    if hasattr(sys, "_is_gil_enabled"):
        enabled = sys._is_gil_enabled()
        status = "DISABLED (free-threaded)" if not enabled else "enabled"
        print(f"\nPython {sys.version.split()[0]} — GIL {status}")
    else:
        print(f"\nPython {sys.version.split()[0]} — GIL always enabled (< 3.13)")
