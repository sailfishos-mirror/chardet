# tests/conftest.py
"""Shared test fixtures."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_TEST_DATA_REPO = "https://github.com/chardet/chardet.git"
_TEST_DATA_SUBDIR = "tests"

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
        return local_data

    # Sparse checkout just the tests directory
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth=1",
                "--filter=blob:none",
                "--sparse",
                _TEST_DATA_REPO,
                tmp,
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "sparse-checkout", "set", _TEST_DATA_SUBDIR],
            cwd=tmp,
            check=True,
            capture_output=True,
        )
        src = Path(tmp) / _TEST_DATA_SUBDIR
        local_data.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            if item.name in ("__pycache__", ".git"):
                continue
            dest = local_data / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

    return local_data


def _get_data_dir() -> Path:
    """Get the test data directory (for use at collection time, outside fixtures)."""
    repo_root = Path(__file__).parent.parent
    local_data = repo_root / "tests" / "data"
    if local_data.is_dir() and any(local_data.iterdir()):
        return local_data
    pytest.skip("No test data found — run accuracy tests once to clone data")
    return local_data  # unreachable, satisfies type checker


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
