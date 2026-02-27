# Parallel Training Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Parallelize the model building phase of `train.py` using ProcessPoolExecutor for ~7x speedup.

**Architecture:** Extract per-model build logic into a standalone picklable function, dispatch to ProcessPoolExecutor with cpu_count() workers, lazy per-worker text caching from disk.

**Tech Stack:** Python `concurrent.futures.ProcessPoolExecutor`, existing `train.py` infrastructure.

---

### Task 1: Add `--build-workers` CLI argument

**Files:**
- Modify: `scripts/train.py:755-768`

**Step 1: Add the argument after `--download-workers`**

In `main()`, after the `--download-workers` argument block (line 760), add:

```python
    parser.add_argument(
        "--build-workers",
        type=int,
        default=os.cpu_count(),
        help="Number of parallel processes for building models (default: all CPUs)",
    )
```

**Step 2: Verify script still runs**

Run: `uv run python scripts/train.py --help`
Expected: New `--build-workers` argument shown in help output.

**Step 3: Commit**

```bash
git add scripts/train.py
git commit -m "feat(train): add --build-workers CLI argument"
```

---

### Task 2: Extract `_build_one_model()` function

**Files:**
- Modify: `scripts/train.py`

This is the core refactor. Extract the inline build loop body (lines 844-884) into a top-level function, and add the per-worker text cache.

**Step 1: Write a test that imports and calls the function**

Create `tests/test_train_build.py`:

```python
"""Test the extracted _build_one_model function."""
from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path so we can import train
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from train import _build_one_model, _worker_text_cache


def test_build_one_model_returns_tuple():
    """_build_one_model returns a 4-tuple even with no cached texts."""
    _worker_text_cache.clear()
    result = _build_one_model(
        lang="xx",  # non-existent language
        enc_name="utf-8",
        codec="utf-8",
        cache_dir="/tmp/nonexistent_cache",
        max_samples=10,
        min_weight=1,
    )
    assert isinstance(result, tuple)
    assert len(result) == 4
    key, bigrams, samples, total_bytes = result
    assert key == "xx/utf-8"
    # No cached texts for "xx", so bigrams should be None
    assert bigrams is None


def test_build_one_model_with_real_texts(tmp_path):
    """_build_one_model produces bigrams from actual text."""
    _worker_text_cache.clear()
    # Create a fake cache directory with some text files
    lang_dir = tmp_path / "culturax_cache" / "fr"
    lang_dir.mkdir(parents=True)
    for i in range(50):
        (lang_dir / f"{i}.txt").write_text(
            "Le président de la République française a prononcé un discours "
            "devant l'Assemblée nationale sur les questions économiques.",
            encoding="utf-8",
        )

    result = _build_one_model(
        lang="fr",
        enc_name="iso-8859-1",
        codec="iso-8859-1",
        cache_dir=str(tmp_path),
        max_samples=100,
        min_weight=1,
    )
    key, bigrams, samples, total_bytes = result
    assert key == "fr/iso-8859-1"
    assert bigrams is not None
    assert len(bigrams) > 0
    assert samples > 0
    assert total_bytes > 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_train_build.py -v`
Expected: ImportError — `_build_one_model` doesn't exist yet.

**Step 3: Add the `_worker_text_cache` dict and `_build_one_model()` function**

Place these right before `main()` (around line 725). The function must be
at module level (not nested) so it's picklable by ProcessPoolExecutor.

```python
# ---------------------------------------------------------------------------
# Parallel model building
# ---------------------------------------------------------------------------

# Per-worker text cache. Each worker process lazily loads language texts from
# the disk cache (populated by the download phase) and caches them here to
# avoid redundant disk reads when the same language is used across multiple
# encodings.
_worker_text_cache: dict[str, list[str]] = {}


def _build_one_model(
    lang: str,
    enc_name: str,
    codec: str,
    cache_dir: str,
    max_samples: int,
    min_weight: int,
) -> tuple[str, dict[tuple[int, int], int] | None, int, int]:
    """Build a single bigram model in a (possibly forked) worker process.

    Returns
    -------
    tuple of (model_key, bigrams_or_None, sample_count, total_encoded_bytes)
    """
    model_key = f"{lang}/{enc_name}"

    # Load texts from disk cache (lazy, cached per worker)
    if lang not in _worker_text_cache:
        _worker_text_cache[lang] = get_texts(lang, max_samples, cache_dir)
    texts = _worker_text_cache[lang]

    if not texts:
        return (model_key, None, 0, 0)

    # Add HTML-wrapped samples
    html_samples = add_html_samples(texts)
    all_texts = list(texts) + html_samples

    # Prepare substitutions for this encoding
    subs = get_substitutions(enc_name, [lang])

    # Normalize, substitute, and encode all texts
    encoded: list[bytes] = []
    for text in all_texts:
        text = normalize_text(text, enc_name)
        text = apply_substitutions(text, subs)
        result = encode_text(text, codec)
        if result is not None:
            encoded.append(result)

    if not encoded:
        return (model_key, None, len(all_texts), 0)

    # Compute bigram frequencies
    freqs = compute_bigram_frequencies(encoded)
    bigrams = normalize_and_prune(freqs, min_weight)

    if not bigrams:
        return (model_key, None, len(encoded), sum(len(e) for e in encoded))

    total_bytes = sum(len(e) for e in encoded)
    return (model_key, bigrams, len(encoded), total_bytes)
```

**Step 4: Run tests to verify the function works**

Run: `uv run pytest tests/test_train_build.py -v`
Expected: Both tests pass.

**Step 5: Commit**

```bash
git add scripts/train.py tests/test_train_build.py
git commit -m "refactor(train): extract _build_one_model function"
```

---

### Task 3: Wire ProcessPoolExecutor into the build loop

**Files:**
- Modify: `scripts/train.py:821-886` (the build loop in `main()`)

**Step 1: Replace the sequential build loop with parallel dispatch**

Replace the current build loop (lines 821-886) with:

```python
    # Build models for each encoding
    print(f"=== Building bigram models ({args.build_workers} workers) ===")
    models: dict[str, dict[tuple[int, int], int]] = {}
    skipped = []

    # Pre-verify codecs and collect work items
    work_items: list[tuple[str, str, str, str, int, int]] = []
    for enc_name, langs in sorted(encoding_map.items()):
        codec = None
        codec_candidates = [enc_name]
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

        for lang in langs:
            work_items.append((
                lang, enc_name, codec, args.cache_dir, args.max_samples, args.min_weight,
            ))

    if args.build_workers == 1:
        # Sequential mode (useful for debugging)
        for item in work_items:
            key, bigrams, samples, total_bytes = _build_one_model(*item)
            if bigrams:
                models[key] = bigrams
                print(
                    f"  {key}: {len(bigrams)} bigrams from "
                    f"{samples} samples ({total_bytes:,} bytes)"
                )
            else:
                print(f"  SKIP {key}: no usable bigrams")
    else:
        # Parallel mode
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=args.build_workers,
        ) as pool:
            futures = {
                pool.submit(_build_one_model, *item): item[1]  # enc_name for error msg
                for item in work_items
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    key, bigrams, samples, total_bytes = future.result()
                except Exception as exc:
                    enc = futures[future]
                    print(f"  ERROR {enc}: {exc}")
                    continue
                if bigrams:
                    models[key] = bigrams
                    print(
                        f"  {key}: {len(bigrams)} bigrams from "
                        f"{samples} samples ({total_bytes:,} bytes)"
                    )
                else:
                    print(f"  SKIP {key}: no usable bigrams")
```

**Step 2: Run the existing tests to verify no regression**

Run: `uv run pytest tests/ -x -q`
Expected: All tests pass (accuracy tests use the existing models.bin, unaffected by train.py changes).

**Step 3: Run a small training to verify parallel execution**

Run: `uv run python scripts/train.py --max-samples 100 --encodings koi8-t koi8-r windows-1252 --build-workers 3`
Expected: Models build successfully. Output lines may arrive out of alphabetical order.

**Step 4: Run the same training with `--build-workers 1` to verify sequential fallback**

Run: `uv run python scripts/train.py --max-samples 100 --encodings koi8-t koi8-r --build-workers 1`
Expected: Same results, sequential order.

**Step 5: Commit**

```bash
git add scripts/train.py
git commit -m "feat(train): parallelize model building with ProcessPoolExecutor"
```

---

### Task 4: Full training run and timing comparison

**Files:**
- No code changes — just measurement

**Step 1: Run full training with default workers**

Run: `uv run python scripts/train.py 2>&1 | tee training_parallel_output.txt`
Expected: Completes significantly faster than 79 minutes. Models output should be 233 models, ~699 KB.

**Step 2: Verify models are identical**

Run: `md5 src/chardet/models/models.bin`

The models.bin may differ in model ordering within the binary file (since
parallel execution order is non-deterministic), but the content should be
equivalent. Verify by running accuracy tests:

Run: `uv run pytest tests/test_accuracy.py --tb=no -q`
Expected: 2060 passed, 101 failed (same as before).

**Step 3: Verify all other tests pass**

Run: `uv run pytest tests/ -x -q`
Expected: All tests pass.

**Step 4: Commit the retrained models and metadata**

```bash
git add src/chardet/models/models.bin src/chardet/models/training_metadata.yaml
git commit -m "feat: retrain models at 15K samples with parallel training

Training time reduced from ~79 minutes to ~X minutes using
ProcessPoolExecutor with N workers."
```

(Fill in actual timing from Step 1.)

**Step 5: Record timing comparison**

Note the elapsed time from the training output and compare with the
previous 79-minute sequential run (at 25K samples — adjust for the
15K sample count when comparing).
