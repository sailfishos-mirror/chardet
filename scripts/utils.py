"""Shared utilities for scripts and tests."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import chardet

_TEST_DATA_REPO = "https://github.com/chardet/test-data.git"
_REF_FILE = ".test-data-ref"


def _get_test_data_ref() -> str | None:
    """Derive the test-data git ref from the installed chardet version.

    Returns a tag like ``"7.0.1"`` for release versions, or ``None`` for
    dev builds (which will clone the default branch instead).
    """
    version = chardet.__version__
    if ".dev" in version:
        return None
    return version


def _clone_test_data(local_data: Path, *, ref: str | None) -> None:
    """Shallow-clone the test-data repo into *local_data*.

    If *ref* is not ``None``, clone the specific tag/branch. Falls back to
    the default branch if the ref does not exist.
    """
    with tempfile.TemporaryDirectory() as tmp:
        if ref is not None:
            try:
                subprocess.run(
                    [
                        "git",
                        "clone",
                        f"--branch={ref}",
                        "--depth=1",
                        _TEST_DATA_REPO,
                        tmp,
                    ],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError:
                print(
                    f"WARNING: test-data ref '{ref}' not found, "
                    f"falling back to default branch",
                    file=sys.stderr,
                )
                subprocess.run(
                    ["git", "clone", "--depth=1", _TEST_DATA_REPO, tmp],
                    check=True,
                    capture_output=True,
                )
                ref = None
        else:
            subprocess.run(
                ["git", "clone", "--depth=1", _TEST_DATA_REPO, tmp],
                check=True,
                capture_output=True,
            )

        src = Path(tmp)
        local_data.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            if not item.is_dir() or item.name.startswith("."):
                continue
            dest = local_data / item.name
            shutil.copytree(item, dest, dirs_exist_ok=True)
        ref_label = ref if ref is not None else "main"
        (local_data / _REF_FILE).write_text(ref_label + "\n")


def get_data_dir() -> Path:
    """Get the test data directory, cloning from GitHub if needed.

    If ``tests/data`` is a symlink (e.g. to a local ``chardet/test-data``
    checkout), it is used as-is — no staleness check or clone is performed.

    Otherwise, the desired ref is derived from the installed chardet version.
    If the cached data's ``.test-data-ref`` matches the desired ref, it is
    reused; otherwise the cache is cleared and re-cloned.
    """
    repo_root = Path(__file__).parent.parent
    local_data = repo_root / "tests" / "data"
    if local_data.is_symlink():
        return local_data.resolve()

    ref = _get_test_data_ref()
    desired_label = ref if ref is not None else "main"

    if local_data.is_dir() and any(local_data.iterdir()):
        ref_file = local_data / _REF_FILE
        if ref_file.is_file() and ref_file.read_text().strip() == desired_label:
            return local_data
        shutil.rmtree(local_data)

    _clone_test_data(local_data, ref=ref)
    return local_data


def find_chardet_so_files() -> list[Path]:
    """Return any mypyc .so/.pyd files under the chardet package directory.

    Uses ``importlib.util.find_spec`` to locate the package directory without
    triggering a full ``import chardet``, which would make subsequent import
    timing measurements inaccurate.
    """
    import importlib.util

    spec = importlib.util.find_spec("chardet")
    if spec is None or spec.origin is None:
        return []
    pkg_dir = Path(spec.origin).parent
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


ISO_TO_LANGUAGE: dict[str, str] = {
    "ar": "arabic",
    "be": "belarusian",
    "bg": "bulgarian",
    "br": "breton",
    "cs": "czech",
    "cy": "welsh",
    "da": "danish",
    "de": "german",
    "el": "greek",
    "en": "english",
    "eo": "esperanto",
    "es": "spanish",
    "et": "estonian",
    "fa": "farsi",
    "fi": "finnish",
    "fr": "french",
    "ga": "irish",
    "gd": "gaelic",
    "he": "hebrew",
    "hr": "croatian",
    "hu": "hungarian",
    "id": "indonesian",
    "is": "icelandic",
    "it": "italian",
    "ja": "japanese",
    "kk": "kazakh",
    "ko": "korean",
    "lt": "lithuanian",
    "lv": "latvian",
    "mk": "macedonian",
    "ms": "malay",
    "mt": "maltese",
    "nl": "dutch",
    "no": "norwegian",
    "pl": "polish",
    "pt": "portuguese",
    "ro": "romanian",
    "ru": "russian",
    "sk": "slovak",
    "sl": "slovene",
    "sr": "serbian",
    "sv": "swedish",
    "tg": "tajik",
    "th": "thai",
    "tr": "turkish",
    "uk": "ukrainian",
    "ur": "urdu",
    "vi": "vietnamese",
    "zh": "chinese",
}


# Mapping from English language names (as returned by chardet ≤6 and
# charset-normalizer) to ISO 639-1 codes (used by chardet 7+ and test dirs).
_LANGUAGE_NAME_TO_ISO: dict[str, str] = {
    "arabic": "ar",
    "belarusian": "be",
    "breton": "br",
    "bulgarian": "bg",
    "chinese": "zh",
    "croatian": "hr",
    "czech": "cs",
    "danish": "da",
    "dutch": "nl",
    "english": "en",
    "esperanto": "eo",
    "estonian": "et",
    "farsi": "fa",
    "finnish": "fi",
    "french": "fr",
    "german": "de",
    "greek": "el",
    "hebrew": "he",
    "hungarian": "hu",
    "icelandic": "is",
    "indonesian": "id",
    "irish": "ga",
    "italian": "it",
    "japanese": "ja",
    "kazakh": "kk",
    "korean": "ko",
    "latvian": "lv",
    "lithuanian": "lt",
    "macedonian": "mk",
    "malay": "ms",
    "maltese": "mt",
    "norwegian": "no",
    "polish": "pl",
    "portuguese": "pt",
    "romanian": "ro",
    "russian": "ru",
    "scottish gaelic": "gd",
    "serbian": "sr",
    "slovak": "sk",
    "slovene": "sl",
    "spanish": "es",
    "swedish": "sv",
    "tajik": "tg",
    "thai": "th",
    "turkish": "tr",
    "ukrainian": "uk",
    "vietnamese": "vi",
    "welsh": "cy",
}


def normalize_language(detected_language: str | None) -> str | None:
    """Normalize a detected language to its ISO 639-1 code for comparison.

    Handles both ISO codes (chardet 7+) and English names (chardet ≤6,
    charset-normalizer).
    """
    if not detected_language:
        return None
    lowered = detected_language.lower().rstrip("—")  # charset-normalizer quirk
    return _LANGUAGE_NAME_TO_ISO.get(lowered, lowered)


def collect_test_files(
    data_dir: Path,
) -> list[tuple[str | None, str | None, Path]]:
    """Collect (encoding, language, filepath) tuples from test data.

    Directory name format: "{encoding}-{lang_iso}" e.g. "utf-8-en",
    "iso-8859-1-fr", "hz-gb-2312-zh".

    Since all ISO 639-1 codes are two letters (no hyphens), we can reliably
    split on the last hyphen to separate encoding from language.

    The binary test directory is named "None-None"; its encoding and language
    are returned as Python ``None`` rather than the string ``"None"``.
    """
    test_files: list[tuple[str | None, str | None, Path]] = []
    for encoding_dir in sorted(data_dir.iterdir()):
        if not encoding_dir.is_dir():
            continue
        parts = encoding_dir.name.rsplit("-", 1)
        if len(parts) != 2:
            continue
        encoding_name: str | None = parts[0]
        language: str | None = parts[1]
        if encoding_name == "None":
            encoding_name = None
        if language == "None":
            language = None
        test_files.extend(
            (encoding_name, language, filepath)
            for filepath in sorted(encoding_dir.iterdir())
            if filepath.is_file()
        )
    return test_files
