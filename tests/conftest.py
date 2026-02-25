# tests/conftest.py
"""Shared test fixtures."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

_TEST_DATA_REPO = "https://github.com/chardet/chardet.git"
_TEST_DATA_SUBDIR = "tests"


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
