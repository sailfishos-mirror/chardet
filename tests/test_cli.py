# tests/test_cli.py
import subprocess
import sys
from pathlib import Path


def test_cli_detects_file(tmp_path: Path):
    f = tmp_path / "test.txt"
    f.write_bytes(b"Hello world")
    result = subprocess.run(
        [sys.executable, "-m", "chardet.cli", str(f)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "ascii" in result.stdout.lower()


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
    assert "ascii" in result.stdout.decode().lower()


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
    assert result.stdout.strip() == "ascii"


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
