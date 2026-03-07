"""Tests for scripts/utils.py test-data ref logic."""

from __future__ import annotations

from unittest.mock import patch

from utils import _get_test_data_ref


class TestGetTestDataRef:
    """Tests for _get_test_data_ref()."""

    def test_release_version(self) -> None:
        with patch("utils.chardet") as mock_chardet:
            mock_chardet.__version__ = "7.0.1"
            assert _get_test_data_ref() == "v7.0.1"

    def test_dev_version(self) -> None:
        with patch("utils.chardet") as mock_chardet:
            mock_chardet.__version__ = "7.0.2.dev5+g91df78e"
            assert _get_test_data_ref() is None

    def test_post_version(self) -> None:
        with patch("utils.chardet") as mock_chardet:
            mock_chardet.__version__ = "6.0.0.post1"
            assert _get_test_data_ref() == "v6.0.0.post1"

    def test_rc_version(self) -> None:
        with patch("utils.chardet") as mock_chardet:
            mock_chardet.__version__ = "7.0.0rc4"
            assert _get_test_data_ref() == "v7.0.0rc4"
