#!/usr/bin/env python3
"""Training script for chardet bigram models.

Downloads Wikipedia articles via Hugging Face datasets, encodes text into
target encodings, computes byte-pair bigram frequencies, and serialises the
results into models.bin.

Usage:
    uv run python scripts/train.py --max-samples 200
"""

from __future__ import annotations

import argparse
import codecs
import collections
import os
import struct
import time

# ---------------------------------------------------------------------------
# Encoding -> language mapping
# ---------------------------------------------------------------------------

# Map each encoding name to a list of Wikipedia language codes whose text
# should be used to train the bigram model for that encoding.

ENCODING_LANG_MAP: dict[str, list[str]] = {
    # CJK - Japanese
    "shift_jis": ["ja"],
    "cp932": ["ja"],
    "euc-jp": ["ja"],
    "iso-2022-jp": ["ja"],
    # CJK - Korean
    "euc-kr": ["ko"],
    "cp949": ["ko"],
    "iso-2022-kr": ["ko"],
    "johab": ["ko"],
    # CJK - Chinese
    "gb18030": ["zh"],
    "hz-gb-2312": ["zh"],
    "big5": ["zh"],
    # Arabic
    "iso-8859-6": ["ar"],
    "cp720": ["ar"],
    "cp864": ["ar"],
    "windows-1256": ["ar"],
    "cp1006": ["ar"],  # Urdu - use Arabic as closest
    # Hebrew
    "iso-8859-8": ["he"],
    "cp424": ["he"],
    "cp856": ["he"],
    "cp862": ["he"],
    "windows-1255": ["he"],
    # Greek
    "iso-8859-7": ["el"],
    "cp737": ["el"],
    "cp869": ["el"],
    "cp875": ["el"],
    "windows-1253": ["el"],
    "mac-greek": ["el"],
    # Cyrillic - Russian
    "iso-8859-5": ["ru"],
    "koi8-r": ["ru"],
    "windows-1251": ["ru"],
    "cp855": ["ru"],
    "cp866": ["ru"],
    "mac-cyrillic": ["ru"],
    # Cyrillic - Ukrainian
    "koi8-u": ["uk"],
    "cp1125": ["uk"],
    # Cyrillic - Central Asian
    "kz-1048": ["kk"],
    "ptcp154": ["kk"],
    "koi8-t": ["tg"],
    # Thai
    "iso-8859-11": ["th"],
    "cp874": ["th"],
    "tis-620": ["th"],
    # Vietnamese
    "windows-1258": ["vi"],
    # Turkish
    "iso-8859-9": ["tr"],
    "cp857": ["tr"],
    "windows-1254": ["tr"],
    "mac-turkish": ["tr"],
    # Western European (Latin-1 family)
    "iso-8859-1": ["en", "fr", "de", "es"],
    "windows-1252": ["en", "fr", "de", "es"],
    "iso-8859-15": ["en", "fr", "de", "es"],
    "mac-roman": ["en", "fr", "de", "es"],
    "mac-iceland": ["en", "fr", "de"],
    "cp437": ["en", "fr", "de", "es"],
    "cp850": ["en", "fr", "de", "es"],
    "cp858": ["en", "fr", "de", "es"],
    "cp860": ["pt"],
    "cp861": ["en"],  # Icelandic - use English as fallback
    "cp863": ["fr"],
    "cp865": ["en"],  # Nordic - use English as fallback
    # Central European (Latin-2 family)
    "iso-8859-2": ["pl", "cs", "hu"],
    "windows-1250": ["pl", "cs", "hu"],
    "iso-8859-16": ["ro"],
    "mac-latin2": ["pl", "cs", "hu"],
    "cp852": ["pl", "cs", "hu"],
    # Baltic
    "iso-8859-4": ["lt", "lv"],
    "iso-8859-13": ["lt", "lv"],
    "windows-1257": ["lt", "lv"],
    "cp775": ["lt", "lv"],
    # Nordic/Other Latin
    "iso-8859-10": ["fi", "sv"],
    "iso-8859-14": ["en"],  # Celtic - use English
    "iso-8859-3": ["tr"],  # South European - use Turkish as closest
    # EBCDIC
    "cp037": ["en"],
    "cp500": ["en", "fr", "de"],
    "cp1026": ["tr"],
}

# Wikipedia dataset name and version
WIKI_DATASET = "wikimedia/wikipedia"
WIKI_VERSION = "20231101"

# Cache of downloaded text per language
_lang_text_cache: dict[str, list[str]] = {}


def get_wikipedia_texts(
    lang: str,
    max_samples: int,
    cache_dir: str,
) -> list[str]:
    """Download and cache Wikipedia article texts for a language."""
    if lang in _lang_text_cache:
        return _lang_text_cache[lang][:max_samples]

    cache_file = os.path.join(cache_dir, f"wiki_{lang}.txt")

    # Try loading from local cache file first
    if os.path.exists(cache_file):
        print(f"  Loading cached {lang} text from {cache_file}")
        texts = []
        with open(cache_file, encoding="utf-8") as f:
            current = []
            for line in f:
                if line.strip() == "---ARTICLE_SEPARATOR---":
                    if current:
                        texts.append("".join(current))
                        current = []
                else:
                    current.append(line)
            if current:
                texts.append("".join(current))
        _lang_text_cache[lang] = texts
        return texts[:max_samples]

    # Download from Hugging Face
    print(f"  Downloading Wikipedia ({lang})...")
    from datasets import load_dataset

    config = f"{WIKI_VERSION}.{lang}"
    try:
        ds = load_dataset(WIKI_DATASET, config, split="train", streaming=True)
    except Exception as e:
        print(f"  WARNING: Could not load Wikipedia for '{lang}': {e}")
        _lang_text_cache[lang] = []
        return []

    texts: list[str] = []
    try:
        for i, example in enumerate(ds):
            if i >= max_samples:
                break
            text = example.get("text", "")
            if text and len(text) > 100:
                texts.append(text)
    except Exception as e:
        print(f"  WARNING: Error streaming Wikipedia for '{lang}': {e}")

    if not texts:
        print(f"  WARNING: No articles found for '{lang}'")
        _lang_text_cache[lang] = []
        return []

    # Save to local cache
    os.makedirs(cache_dir, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        for j, text in enumerate(texts):
            f.write(text)
            if j < len(texts) - 1:
                f.write("\n---ARTICLE_SEPARATOR---\n")
    print(f"  Cached {len(texts)} articles for '{lang}'")

    _lang_text_cache[lang] = texts
    return texts[:max_samples]


def add_html_samples(texts: list[str], count: int = 20) -> list[str]:
    """Wrap some text samples in HTML to train on markup patterns."""
    html_samples = []
    for i, text in enumerate(texts[:count]):
        # Truncate to reasonable size
        snippet = text[:500]
        html = (
            f'<!DOCTYPE html>\n<html lang="en">\n<head>\n'
            f'<meta charset="utf-8">\n<title>Article {i}</title>\n'
            f"</head>\n<body>\n<h1>Article {i}</h1>\n"
            f"<p>{snippet}</p>\n</body>\n</html>"
        )
        html_samples.append(html)
    return html_samples


def encode_text(text: str, codec_name: str) -> bytes | None:
    """Encode a UTF-8 string into the target encoding, ignoring errors."""
    try:
        return text.encode(codec_name, errors="ignore")
    except (LookupError, UnicodeEncodeError, UnicodeDecodeError):
        return None


def compute_bigram_frequencies(
    encoded_samples: list[bytes],
) -> dict[tuple[int, int], int]:
    """Count byte bigram frequencies across all samples."""
    counts: dict[tuple[int, int], int] = collections.Counter()
    for data in encoded_samples:
        for i in range(len(data) - 1):
            counts[(data[i], data[i + 1])] += 1
    return dict(counts)


def normalize_and_prune(
    freqs: dict[tuple[int, int], int],
    min_weight: int,
) -> dict[tuple[int, int], int]:
    """Normalize frequency counts to 0-255 and prune low weights."""
    if not freqs:
        return {}

    max_count = max(freqs.values())
    if max_count == 0:
        return {}

    result: dict[tuple[int, int], int] = {}
    for pair, count in freqs.items():
        weight = int(round(count / max_count * 255))
        if weight >= min_weight:
            result[pair] = weight
    return result


def serialize_models(
    models: dict[str, dict[tuple[int, int], int]],
    output_path: str,
) -> int:
    """Serialize all models to binary format. Returns file size."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "wb") as f:
        # Number of encodings
        f.write(struct.pack("!I", len(models)))

        for name, bigrams in sorted(models.items()):
            name_bytes = name.encode("utf-8")
            f.write(struct.pack("!I", len(name_bytes)))
            f.write(name_bytes)
            f.write(struct.pack("!I", len(bigrams)))
            for (b1, b2), weight in bigrams.items():
                f.write(struct.pack("!BBB", b1, b2, weight))

    return os.path.getsize(output_path)


def verify_codec(codec_name: str) -> bool:
    """Verify a Python codec exists and can encode."""
    try:
        codecs.lookup(codec_name)
        return True
    except LookupError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Train chardet bigram models")
    parser.add_argument(
        "--output",
        default="src/chardet/models/models.bin",
        help="Output path for models.bin",
    )
    parser.add_argument(
        "--cache-dir",
        default="data/",
        help="Directory to cache downloaded data",
    )
    parser.add_argument(
        "--min-weight",
        type=int,
        default=1,
        help="Minimum weight threshold for pruning",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=1000,
        help="Maximum number of Wikipedia articles per language",
    )
    args = parser.parse_args()

    start_time = time.time()

    # Collect all unique languages needed
    all_langs: set[str] = set()
    for langs in ENCODING_LANG_MAP.values():
        all_langs.update(langs)

    print(f"Training bigram models for {len(ENCODING_LANG_MAP)} encodings")
    print(f"Languages needed: {sorted(all_langs)}")
    print(f"Max samples per language: {args.max_samples}")
    print()

    # Pre-download all language texts
    print("=== Downloading Wikipedia texts ===")
    for lang in sorted(all_langs):
        texts = get_wikipedia_texts(lang, args.max_samples, args.cache_dir)
        print(f"  {lang}: {len(texts)} articles")
    print()

    # Build models for each encoding
    print("=== Building bigram models ===")
    models: dict[str, dict[tuple[int, int], int]] = {}
    skipped = []

    for enc_name, langs in sorted(ENCODING_LANG_MAP.items()):
        # Look up the Python codec name from the registry mapping
        # For the training script, we try the encoding name directly,
        # then common variations
        codec = None
        codec_candidates = [enc_name]
        # Normalize common patterns
        normalized = enc_name.replace("-", "").replace("_", "").lower()
        codec_candidates.append(normalized)

        for candidate in codec_candidates:
            if verify_codec(candidate):
                codec = candidate
                break

        if codec is None:
            print(f"  SKIP {enc_name}: codec not found")
            skipped.append(enc_name)
            continue

        # Gather text from all mapped languages
        all_texts: list[str] = []
        for lang in langs:
            all_texts.extend(
                get_wikipedia_texts(lang, args.max_samples, args.cache_dir)
            )

        if not all_texts:
            print(f"  SKIP {enc_name}: no text available")
            skipped.append(enc_name)
            continue

        # Add HTML-wrapped samples
        html_samples = add_html_samples(all_texts)
        all_texts.extend(html_samples)

        # Encode all texts into the target encoding
        encoded: list[bytes] = []
        for text in all_texts:
            result = encode_text(text, codec)
            if result and len(result) > 10:
                encoded.append(result)

        if not encoded:
            print(f"  SKIP {enc_name}: no encodable text")
            skipped.append(enc_name)
            continue

        # Compute bigram frequencies
        freqs = compute_bigram_frequencies(encoded)
        bigrams = normalize_and_prune(freqs, args.min_weight)

        if not bigrams:
            print(f"  SKIP {enc_name}: no bigrams above threshold")
            skipped.append(enc_name)
            continue

        models[enc_name] = bigrams
        total_bytes = sum(len(e) for e in encoded)
        print(
            f"  {enc_name}: {len(bigrams)} bigrams from "
            f"{len(encoded)} samples ({total_bytes:,} bytes)"
        )

    print()

    # Serialize
    print("=== Serializing models ===")
    file_size = serialize_models(models, args.output)

    elapsed = time.time() - start_time

    # Print summary
    print()
    print("=" * 60)
    print(f"Models trained: {len(models)}")
    print(f"Models skipped: {len(skipped)}")
    if skipped:
        print(f"  Skipped: {', '.join(skipped)}")
    print(f"Output file:    {args.output}")
    print(f"File size:      {file_size:,} bytes ({file_size / 1024:.1f} KB)")
    print(f"Elapsed time:   {elapsed:.1f}s")
    print()

    # Per-model stats
    print("Per-model sizes:")
    for name in sorted(models):
        n = len(models[name])
        # 4 (name_len) + len(name) + 4 (num_entries) + 3*n (entries)
        model_bytes = 4 + len(name.encode("utf-8")) + 4 + 3 * n
        print(f"  {name:20s}: {n:6d} bigrams ({model_bytes:,} bytes)")


if __name__ == "__main__":
    main()
