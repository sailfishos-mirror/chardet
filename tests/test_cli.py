# tests/test_cli.py
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from chardet.cli import main


def test_cli_detects_file(tmp_path: Path):
    f = tmp_path / "test.txt"
    f.write_bytes(b"Hello world")
    result = subprocess.run(
        [sys.executable, "-m", "chardet.cli", str(f)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # Default era is MODERN_WEB, which renames ascii to Windows-1252
    assert "windows-1252" in result.stdout.lower()


def test_cli_detects_utf8_file(tmp_path: Path):
    f = tmp_path / "test.txt"
    f.write_bytes("Héllo wörld".encode())
    result = subprocess.run(
        [sys.executable, "-m", "chardet.cli", str(f)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "utf-8" in result.stdout.lower()


def test_cli_stdin():
    result = subprocess.run(
        [sys.executable, "-m", "chardet.cli"],
        input=b"Hello world",
        capture_output=True,
    )
    assert result.returncode == 0
    # Default era is MODERN_WEB, which renames ascii to Windows-1252
    assert "windows-1252" in result.stdout.decode().lower()


def test_cli_version():
    result = subprocess.run(
        [sys.executable, "-m", "chardet.cli", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "6.1.0" in result.stdout


def test_cli_minimal_flag(tmp_path: Path):
    f = tmp_path / "test.txt"
    f.write_bytes(b"Hello world")
    result = subprocess.run(
        [sys.executable, "-m", "chardet.cli", "--minimal", str(f)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # Default era is MODERN_WEB, which renames ascii to Windows-1252
    assert result.stdout.strip() == "Windows-1252"


def test_cli_multiple_files(tmp_path: Path):
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_bytes(b"Hello")
    f2.write_bytes("Héllo".encode())
    result = subprocess.run(
        [sys.executable, "-m", "chardet.cli", str(f1), str(f2)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    lines = result.stdout.strip().split("\n")
    assert len(lines) == 2


def test_cli_nonexistent_file(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit, match="1"):
        main(["nonexistent_file_xyz.txt"])
    captured = capsys.readouterr()
    assert "nonexistent_file_xyz.txt" in captured.err


def test_cli_legacy_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    f = tmp_path / "test.txt"
    f.write_bytes(b"Hello world, enough text for detection. " * 3)
    main(["--legacy", str(f)])
    captured = capsys.readouterr()
    assert "with confidence" in captured.out


def test_cli_encoding_era_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    f = tmp_path / "test.txt"
    f.write_bytes(b"Hello world, enough text for detection. " * 3)
    main(["-e", "modern_web", str(f)])
    captured = capsys.readouterr()
    assert "with confidence" in captured.out
