# Documentation Setup Design

**Date:** 2026-03-01

## Goal

Set up Sphinx documentation for chardet 7.0, auto-published to ReadTheDocs
on tag push. Provide Usage, Supported Encodings, How It Works, Performance,
FAQ, and API Reference sections.

## Tooling

- **Sphinx** with **Furo** theme
- **autodoc + autosummary** for API reference auto-generation from existing
  Sphinx-style (`:param:` / `:returns:`) docstrings
- **sphinx-copybutton** for code block copy buttons
- Docs dependencies in a `docs` dependency group in `pyproject.toml`

## ReadTheDocs Configuration

- `.readthedocs.yaml` v2 format
- Build on tag push only (no dev builds from main)
- Python 3.12 build environment
- Install project with `uv` so autodoc imports work

## File Structure

```
docs/
  conf.py                    # Sphinx configuration
  index.rst                  # Landing page with toctree
  usage.rst                  # Installation + usage guide
  supported-encodings.rst    # Table of all supported encodings
  how-it-works.rst           # High-level pipeline overview
  performance.rst            # Benchmarks vs other detectors
  faq.rst                    # Frequently asked questions
  api/
    index.rst                # API reference entry (autosummary-generated)
.readthedocs.yaml            # RTD build config
```

## Content Sections

### Usage

Installation (`pip install chardet`), basic `detect()` / `detect_all()`,
`UniversalDetector` streaming interface, CLI (`chardetect`), `EncodingEra`
filtering.

### Supported Encodings

Static RST table generated from `REGISTRY` showing encoding name, aliases,
era, and whether it's multibyte. Static rather than a custom Sphinx
extension — the registry rarely changes.

### How It Works

High-level pipeline overview: BOM check, UTF-16/32 patterns, escape
sequences, binary detection, markup charset, ASCII, UTF-8 validation,
byte validity filtering, structural probing, statistical bigram scoring.
Explains what confidence scores mean. No deep implementation details.

### Performance

Adapted from `docs/rewrite_performance.md` for a public audience:

- **Overall Accuracy** — comparison table (chardet vs charset-normalizer
  vs cchardet)
- **Speed** — total time + latency distribution (mean/median/p95)
- **Memory** — import time, peak memory, RSS
- **Language Detection** — the 90.9% differentiator
- **Thread Safety & Free-Threading** — scaling results on 3.13t/3.14t
- **mypyc Compilation** — optional speedup numbers

Drops internal pairwise per-encoding breakdowns (too granular for users).
Written to be updated over time as versions evolve.

### FAQ

Common questions:

- "Why does detect() return None?"
- "How do I increase accuracy?"
- "What changed from chardet 5.x / 6.x?"
- "How is this different from charset-normalizer / cchardet?"
- "Is chardet thread-safe?"
- "Does chardet work on PyPy?"

### API Reference

autosummary-driven pages for the public API:

- `chardet.detect`
- `chardet.detect_all`
- `chardet.UniversalDetector`
- `chardet.EncodingEra`
- `chardet.LanguageFilter`

Generated from existing Sphinx-style docstrings already present in
source code.

## Decisions

- **Theme**: Furo — clean, modern, good dark mode, widely used
- **API autodoc**: Built-in autodoc + autosummary (no extra deps beyond
  Sphinx)
- **Versioning**: Tags only, no dev builds from main
- **Supported encodings**: Static RST table, not a custom extension
- **Performance detail level**: Headline numbers, not per-encoding
  breakdowns
- **How It Works detail level**: High-level pipeline overview, not
  internals guide
