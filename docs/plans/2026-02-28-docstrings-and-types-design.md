# Docstrings and Type Annotations Design

## Goal

Add Sphinx-compatible docstrings to all public functions, methods, and classes
in `src/chardet/`, add missing return type annotations, and remove the
corresponding ruff rule exceptions from `pyproject.toml` to enforce these
standards going forward.

## Decisions

- **Docstring style:** Sphinx reST (`:param:`, `:returns:`, `:raises:`)
- **Private functions:** Summary-line docstrings only
- **Scope:** `src/chardet/` only — `tests/` and `scripts/` are exempt via
  per-file-ignores
- **Existing docstrings:** Upgraded to include `:param:`/`:returns:` blocks
  for consistency

## pyproject.toml Changes

Remove from global `[tool.ruff.lint] ignore`:

- `D100` — missing module docstring
- `D101` — missing class docstring
- `D102` — missing public method docstring
- `D103` — missing public function docstring
- `D104` — missing `__init__.py` docstring
- `D107` — missing `__init__` method docstring
- `ANN201` — missing return type for public function
- `ANN202` — missing return type for private function

Add those rules to per-file-ignores for `tests/**`, `scripts/**`, and
`scripts/tests/**`.

Add `[tool.ruff.lint.pydocstyle]` convention = `"pep257"`.

## Docstring Standards

### Public functions/methods

```python
def detect(data: bytes, max_bytes: int = 10000) -> dict[str, Any]:
    """Detect the encoding of the given byte string.

    :param data: The byte string to examine.
    :param max_bytes: Maximum number of bytes to process.
    :returns: A dict with ``'encoding'``, ``'confidence'``, and ``'language'`` keys.
    """
```

### Private functions

```python
def _should_demote(encoding: str, data: bytes) -> bool:
    """Check whether an encoding should be demoted in confidence."""
```

### Modules

```python
"""Byte order mark detection for the chardet pipeline."""
```

### Classes

```python
class UniversalDetector:
    """Streaming character encoding detector.

    Implements the feed/close pattern for incremental detection
    of character encoding from byte streams.
    """
```

### `__init__` methods

Only if they have non-trivial parameters beyond `self`:

```python
def __init__(self, encoding_era: EncodingEra = EncodingEra.ALL) -> None:
    """Initialize the detector.

    :param encoding_era: Filter candidates to a specific era of encodings.
    """
```

## Scope

- 22 files in `src/chardet/`
- ~62 functions + 7 classes to audit
- Most already have docstrings — upgraded to `:param:`/`:returns:` format
- A handful need new docstrings written from scratch
- Existing inline/block comments stay untouched

## Approach

1. Update `pyproject.toml` (remove global ignores, add per-file-ignores, add
   pydocstyle convention)
2. Run `ruff check` to get exact violation list
3. Fix violations file-by-file, upgrading existing docstrings and adding
   missing ones
4. Add any missing return type annotations
5. Run tests and linting to verify
