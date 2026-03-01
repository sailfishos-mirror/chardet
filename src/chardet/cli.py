"""Command-line interface for chardet."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chardet
from chardet.enums import EncodingEra

_ERA_NAMES = [e.name.lower() for e in EncodingEra if e.bit_count() == 1] + ["all"]
_DEFAULT_MAX_BYTES = 200_000


def main(argv: list[str] | None = None) -> None:
    """Run the ``chardetect`` command-line tool.

    :param argv: Command-line arguments.  Defaults to ``sys.argv[1:]``.
    """
    parser = argparse.ArgumentParser(description="Detect character encoding of files.")
    parser.add_argument("files", nargs="*", help="Files to detect encoding of")
    parser.add_argument(
        "--minimal", action="store_true", help="Output only the encoding name"
    )
    parser.add_argument(
        "--legacy", action="store_true", help="Include legacy encodings"
    )
    parser.add_argument(
        "-e",
        "--encoding-era",
        default=None,
        choices=_ERA_NAMES,
        help="Encoding era filter",
    )
    parser.add_argument(
        "--version", action="version", version=f"chardet {chardet.__version__}"
    )

    args = parser.parse_args(argv)

    if args.encoding_era:
        era = EncodingEra[args.encoding_era.upper()]
    elif args.legacy:
        era = EncodingEra.ALL
    else:
        era = EncodingEra.MODERN_WEB

    if args.files:
        for filepath in args.files:
            try:
                with Path(filepath).open("rb") as f:
                    data = f.read(_DEFAULT_MAX_BYTES)
            except OSError as e:
                print(f"chardetect: {filepath}: {e}", file=sys.stderr)
                continue
            result = chardet.detect(data, encoding_era=era)
            if args.minimal:
                print(result["encoding"])
            else:
                print(
                    f"{filepath}: {result['encoding']} with confidence {result['confidence']}"
                )
    else:
        data = sys.stdin.buffer.read(_DEFAULT_MAX_BYTES)
        result = chardet.detect(data, encoding_era=era)
        if args.minimal:
            print(result["encoding"])
        else:
            print(f"stdin: {result['encoding']} with confidence {result['confidence']}")


if __name__ == "__main__":
    main()
