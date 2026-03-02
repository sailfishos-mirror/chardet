# tests/conftest.py
"""Shared test configuration."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts/ to sys.path so tests can import utils
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
