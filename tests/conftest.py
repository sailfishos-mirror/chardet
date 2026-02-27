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


@pytest.fixture(scope="session")
def chardet_test_data_dir() -> Path:
    """Resolve chardet test data directory.

    1. If tests/data/ exists in repo, use it (post-merge scenario).
    2. Otherwise, clone from GitHub and cache locally.
    """
    repo_root = Path(__file__).parent.parent
    local_data = repo_root / "tests" / "data"
    if local_data.is_dir() and any(local_data.iterdir()):
        if _cache_is_stale(local_data):
            shutil.rmtree(local_data)
            _clone_test_data(local_data)
        return local_data

    _clone_test_data(local_data)
    return local_data


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


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize accuracy tests dynamically from test data on disk."""
    if "expected_encoding" in metafunc.fixturenames:
        data_dir = _get_data_dir()
        test_files = collect_test_files(data_dir)
        ids = [f"{enc}-{lang}/{fp.name}" for enc, lang, fp in test_files]
        metafunc.parametrize(
            ("expected_encoding", "language", "test_file_path"),
            test_files,
            ids=ids,
        )
