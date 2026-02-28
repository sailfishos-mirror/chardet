"""Shared utilities for scripts and tests."""

from __future__ import annotations

import sys
from pathlib import Path


def find_chardet_so_files() -> list[Path]:
    """Return any mypyc .so/.pyd files under the chardet package directory."""
    import chardet

    pkg_dir = Path(chardet.__file__).parent
    return sorted(
        p for p in pkg_dir.rglob("*") if p.suffix in (".so", ".pyd") and p.is_file()
    )


def abort_if_mypyc_compiled() -> None:
    """Exit with an error if chardet has mypyc .so/.pyd files present.

    Called when ``--pure`` is passed to ensure benchmarks measure
    pure-Python performance only.
    """
    so_files = find_chardet_so_files()
    if so_files:
        print(
            "ERROR: --pure flag set but mypyc compiled extensions detected:",
            file=sys.stderr,
        )
        for p in so_files:
            print(f"  {p}", file=sys.stderr)
        print(
            "\nRemove these .so/.pyd files before benchmarking pure Python.",
            file=sys.stderr,
        )
        sys.exit(1)


def format_bytes(n: int) -> str:
    """Format byte count as human-readable string."""
    if n >= 1 << 20:
        return f"{n / (1 << 20):.1f} MiB"
    if n >= 1 << 10:
        return f"{n / (1 << 10):.1f} KiB"
    return f"{n} B"


def collect_test_files(data_dir: Path) -> list[tuple[str, str, Path]]:
    """Collect (encoding, language, filepath) tuples from test data.

    Directory name format: "{encoding}-{language}" e.g. "utf-8-english",
    "iso-8859-1-french", "hz-gb-2312-chinese".

    Since all language names are single words (no hyphens), we can reliably
    split on the last hyphen to separate encoding from language.
    """
    test_files: list[tuple[str, str, Path]] = []
    for encoding_dir in sorted(data_dir.iterdir()):
        if not encoding_dir.is_dir():
            continue
        parts = encoding_dir.name.rsplit("-", 1)
        if len(parts) != 2:
            continue
        encoding_name, language = parts
        test_files.extend(
            (encoding_name, language, filepath)
            for filepath in sorted(encoding_dir.iterdir())
            if filepath.is_file()
        )
    return test_files
