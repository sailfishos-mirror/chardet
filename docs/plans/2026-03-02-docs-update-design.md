# Documentation Update Design

**Date:** 2026-03-02
**Approach:** Surgical fix of existing pages + new contributing.rst + new changelog.rst

## Goals

- Fix stale/inconsistent data across docs
- Fill parameter coverage gaps in usage.rst
- Add contributor documentation
- Add a comprehensive changelog covering all releases

## Changes by File

### 1. `index.rst` — Richer landing page

Add MIT license, Python 3.10+, PyPy, zero-dependency mentions to the intro paragraph. Add `contributing` and `changelog` to the toctree.

### 2. `usage.rst` — Fill parameter gaps

- Document `should_rename_legacy` parameter (what it does, when to set False)
- Document `max_bytes` on `UniversalDetector.__init__()`
- Document deprecated `chunk_size` (accepted but ignored)
- Document deprecated `LanguageFilter` (accepted but ignored)

### 3. `faq.rst` — Fix stale data

- Fix chardet 5.2.0 accuracy: 68.0% -> 68.2%
- Fix charset-normalizer GitHub link: Ousret -> jawah

### 4. `performance.rst` — Reconcile with rewrite_performance.md

Use `rewrite_performance.md` as the source of truth for all benchmark numbers. Ensure consistency within the docs pages (don't worry about README which has its own marketing numbers).

### 5. New `contributing.rst`

Content from CLAUDE.md: dev setup, testing, linting, training, benchmarks, docs building, architecture overview, mypyc notes, conventions.

### 6. New `changelog.rst`

Comprehensive changelog from GitHub releases:
- 7.0.0 (unreleased) — the rewrite
- 6.0.0 — encoding era system, 38 new languages, EBCDIC
- 5.2.0 — `python -m chardet` CLI
- 5.1.0 — `should_rename_legacy`, MacRoman prober, `--minimal` CLI
- 5.0.0 — Johab, UTF-16/32 BE/LE probers, dropped Python < 3.6
- 4.0.0 — `detect_all()`, performance improvements
- 3.0.x — Python 3 modernization, Turkish ISO-8859-9
- 2.x — merger with charade, CP932 detection

## Non-goals

- No structural reorganization of existing pages
- No changes to api/index.rst (autodoc-driven, already complete)
- No changes to supported-encodings.rst (auto-generated)
- No changes to README.md (has its own marketing numbers)
