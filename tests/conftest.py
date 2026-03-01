# tests/conftest.py
"""Shared test fixtures."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_TEST_DATA_REPO = "https://github.com/chardet/test-data.git"
_COMMIT_HASH_FILE = ".commit-hash"

# Add scripts/ to sys.path so we can import utils
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from utils import collect_test_files  # noqa: E402


def _cache_is_stale(local_data: Path) -> bool:
    """Return True if the cached test data is outdated.

    Compares the stored commit hash against the remote HEAD.  Returns False
    (not stale) if the hash file is missing or the network check fails, so
    tests can still run offline.
    """
    hash_file = local_data / _COMMIT_HASH_FILE
    if not hash_file.is_file():
        return False
    local_hash = hash_file.read_text().strip()
    try:
        result = subprocess.run(
            ["git", "ls-remote", _TEST_DATA_REPO, "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False
    remote_hash = result.stdout.split()[0] if result.stdout.strip() else ""
    return local_hash != remote_hash


def _clone_test_data(local_data: Path) -> None:
    """Shallow-clone the test-data repo into *local_data* and record the commit hash."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["git", "clone", "--depth=1", _TEST_DATA_REPO, tmp],
            check=True,
            capture_output=True,
        )
        # Record the commit hash so we can tell if the cache is stale
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=tmp,
            check=True,
            capture_output=True,
            text=True,
        )
        src = Path(tmp)
        local_data.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            if not item.is_dir() or item.name.startswith("."):
                continue
            dest = local_data / item.name
            shutil.copytree(item, dest, dirs_exist_ok=True)
        (local_data / _COMMIT_HASH_FILE).write_text(head.stdout.strip() + "\n")


def _get_data_dir() -> Path:
    """Get the test data directory, cloning from GitHub if needed."""
    repo_root = Path(__file__).parent.parent
    local_data = repo_root / "tests" / "data"
    if local_data.is_dir() and any(local_data.iterdir()):
        if _cache_is_stale(local_data):
            shutil.rmtree(local_data)
            _clone_test_data(local_data)
        return local_data
    _clone_test_data(local_data)
    return local_data


# Known accuracy failures — marked xfail so they don't block CI but are
# tracked for future improvement.  Kept sorted for easy diffing.
_KNOWN_FAILURES: frozenset[str] = frozenset(
    {
        "cp037-dutch/culturax_mC4_107675.txt",
        "cp037-english/_ude_1.txt",
        "cp437-breton/culturax_OSCAR-2019_43764.txt",
        "cp437-english/culturax_mC4_84512.txt",
        "cp437-finnish/culturax_mC4_80361.txt",
        "cp437-finnish/culturax_mC4_80363.txt",
        "cp437-finnish/culturax_mC4_80364.txt",
        "cp437-indonesian/culturax_mC4_114889.txt",
        "cp437-irish/culturax_mC4_63471.txt",
        "cp437-irish/culturax_mC4_63473.txt",
        "cp437-welsh/culturax_mC4_78727.txt",
        "cp437-welsh/culturax_mC4_78729.txt",
        "cp500-spanish/culturax_mC4_87070.txt",
        "cp850-breton/culturax_OSCAR-2019_43764.txt",
        "cp850-english/culturax_mC4_84512.txt",
        "cp850-finnish/culturax_mC4_80361.txt",
        "cp850-finnish/culturax_mC4_80363.txt",
        "cp850-finnish/culturax_mC4_80364.txt",
        "cp850-icelandic/culturax_mC4_77487.txt",
        "cp850-icelandic/culturax_mC4_77488.txt",
        "cp850-icelandic/culturax_mC4_77489.txt",
        "cp850-indonesian/culturax_mC4_114889.txt",
        "cp850-irish/culturax_mC4_63468.txt",
        "cp850-irish/culturax_mC4_63470.txt",
        "cp850-irish/culturax_mC4_63471.txt",
        "cp850-spanish/culturax_mC4_87070.txt",
        "cp850-welsh/culturax_mC4_78727.txt",
        "cp850-welsh/culturax_mC4_78729.txt",
        "cp852-romanian/culturax_mC4_78976.txt",
        "cp852-romanian/culturax_mC4_78978.txt",
        "cp852-romanian/culturax_mC4_78979.txt",
        "cp852-romanian/culturax_OSCAR-2019_78977.txt",
        "cp858-breton/culturax_OSCAR-2019_43764.txt",
        "cp858-english/culturax_mC4_84512.txt",
        "cp858-finnish/culturax_mC4_80361.txt",
        "cp858-finnish/culturax_mC4_80362.txt",
        "cp858-finnish/culturax_mC4_80363.txt",
        "cp858-icelandic/culturax_mC4_77487.txt",
        "cp858-icelandic/culturax_mC4_77488.txt",
        "cp858-icelandic/culturax_mC4_77489.txt",
        "cp858-indonesian/culturax_mC4_114889.txt",
        "cp858-irish/culturax_mC4_63468.txt",
        "cp858-irish/culturax_mC4_63469.txt",
        "cp858-irish/culturax_mC4_63470.txt",
        "cp858-spanish/culturax_mC4_87070.txt",
        "cp858-welsh/culturax_mC4_78727.txt",
        "cp858-welsh/culturax_mC4_78729.txt",
        "cp866-ukrainian/culturax_mC4_95020.txt",
        "cp866-ukrainian/culturax_mC4_95021.txt",
        "cp874-thai/pharmacy.kku.ac.th.centerlab.xml",
        "cp874-thai/pharmacy.kku.ac.th.healthinfo-ne.xml",
        "cp932-japanese/hardsoft.at.webry.info.xml",
        "cp932-japanese/y-moto.com.xml",
        "cp949-korean/ricanet.com.xml",
        "gb2312-chinese/_mozilla_bug171813_text.html",
        "iso-8859-1-english/_mozilla_bug421271_text.html",
        "iso-8859-1-english/culturax_mC4_84512.txt",
        "iso-8859-1-english/ioreg_output.txt",
        "iso-8859-1-welsh/culturax_mC4_78727.txt",
        "iso-8859-15-english/culturax_mC4_84512.txt",
        "iso-8859-15-irish/culturax_mC4_63469.txt",
        "iso-8859-15-welsh/culturax_mC4_78727.txt",
        "iso-8859-16-romanian/_ude_1.txt",
        "maclatin2-slovene/culturax_mC4_66688.txt",
        "maclatin2-slovene/culturax_mC4_66690.txt",
        "macroman-breton/culturax_OSCAR-2019_43764.txt",
        "macroman-english/culturax_mC4_84512.txt",
        "macroman-indonesian/culturax_mC4_114889.txt",
        "macroman-irish/culturax_mC4_63468.txt",
        "macroman-irish/culturax_mC4_63469.txt",
        "macroman-irish/culturax_mC4_63470.txt",
        "macroman-welsh/culturax_mC4_78727.txt",
        "macroman-welsh/culturax_mC4_78729.txt",
        "utf-8-english/finnish-utf-8-latin-1-confusion.html",
        "windows-1252-english/culturax_mC4_84512.txt",
        "windows-1252-english/github_bug_9.txt",
        "windows-1252-welsh/culturax_mC4_78727.txt",
        "windows-1255-hebrew/_chromium_windows-1255_with_no_encoding_specified.html",
    }
)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize accuracy tests dynamically from test data on disk."""
    if "expected_encoding" in metafunc.fixturenames:
        data_dir = _get_data_dir()
        test_files = collect_test_files(data_dir)
        ids = [f"{enc}-{lang}/{fp.name}" for enc, lang, fp in test_files]
        params = []
        for test_id, (enc, lang, fp) in zip(ids, test_files, strict=True):
            marks = []
            if test_id in _KNOWN_FAILURES:
                marks.append(pytest.mark.xfail(reason="known accuracy gap"))
            params.append(pytest.param(enc, lang, fp, marks=marks, id=test_id))
        metafunc.parametrize(
            ("expected_encoding", "language", "test_file_path"),
            params,
        )
