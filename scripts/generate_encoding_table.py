#!/usr/bin/env python
"""Generate the supported encodings RST table from the registry."""

from __future__ import annotations

from chardet.enums import EncodingEra
from chardet.registry import REGISTRY

ERA_DISPLAY = {
    EncodingEra.MODERN_WEB: "Modern Web",
    EncodingEra.LEGACY_ISO: "Legacy ISO",
    EncodingEra.LEGACY_MAC: "Legacy Mac",
    EncodingEra.LEGACY_REGIONAL: "Legacy Regional",
    EncodingEra.DOS: "DOS",
    EncodingEra.MAINFRAME: "Mainframe (EBCDIC)",
}

ERA_ORDER = list(ERA_DISPLAY)


def main() -> None:
    """Print the supported encodings RST table to stdout."""
    total = len(REGISTRY)
    print("Supported Encodings")
    print("===================")
    print()
    print(f"chardet supports **{total} encodings** across six encoding eras.")
    print("The default :attr:`~chardet.EncodingEra.MODERN_WEB` era covers the")
    print("encodings most commonly found on the web today. Use")
    print(":attr:`~chardet.EncodingEra.ALL` to enable detection of all encodings.")
    print()

    for era in ERA_ORDER:
        entries = sorted(
            [e for e in REGISTRY if e.era == era],
            key=lambda e: e.name,
        )
        title = ERA_DISPLAY[era]
        print(title)
        print("-" * len(title))
        print()
        print(".. list-table::")
        print("   :header-rows: 1")
        print("   :widths: 25 50 15")
        print()
        print("   * - Encoding")
        print("     - Aliases")
        print("     - Multi-byte")
        for e in entries:
            aliases = ", ".join(e.aliases) if e.aliases else "\u2014"
            mb = "Yes" if e.is_multibyte else "No"
            print(f"   * - {e.name}")
            print(f"     - {aliases}")
            print(f"     - {mb}")
        print()


if __name__ == "__main__":
    main()
