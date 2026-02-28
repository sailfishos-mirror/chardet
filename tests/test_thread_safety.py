"""Thread-safety integration tests for concurrent detect() calls."""

from __future__ import annotations

import threading

from chardet import detect
from chardet.enums import EncodingEra


def test_concurrent_detect_no_corruption():
    """Multiple threads calling detect() simultaneously must not corrupt results."""
    japanese = "これはテストです。日本語のテキスト。".encode("shift_jis")
    german = (
        "Die Größe des Gebäudes überraschte die Besucher. "
        "Natürlich können wir das ändern."
    ).encode("windows-1252")
    chinese = "这是中文测试文本，用于并发检测。".encode("gb18030")  # noqa: RUF001
    samples = [japanese, german, chinese]

    errors: list[str] = []
    barrier = threading.Barrier(len(samples) * 3)

    def worker(data: bytes, expected_encodings: frozenset[str]) -> None:
        barrier.wait()
        for _ in range(20):
            result = detect(data, encoding_era=EncodingEra.ALL)
            enc = result["encoding"]
            if enc is not None:
                enc = enc.lower()
            if enc not in expected_encodings:
                errors.append(f"Expected one of {expected_encodings}, got {enc!r}")

    threads = []
    expectations = [
        frozenset({"shift_jis", "cp932"}),
        frozenset(
            {"windows-1252", "iso-8859-1", "iso-8859-15", "iso-8859-9", "windows-1254"}
        ),
        frozenset({"gb18030", "gb2312"}),
    ]
    for _ in range(3):
        for data, expected in zip(samples, expectations, strict=True):
            t = threading.Thread(target=worker, args=(data, expected))
            threads.append(t)
            t.start()

    for t in threads:
        t.join()

    assert not errors, "Thread-safety violations:\n" + "\n".join(errors[:10])
