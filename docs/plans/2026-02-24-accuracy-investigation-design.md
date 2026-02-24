# Accuracy Investigation Design

**Date:** 2026-02-24
**Goal:** Improve chardet's accuracy, especially on short inputs, reduce
expected failures, and identify the best path forward for the single-byte
prober models.

## Background

chardet 6.0.0 retrained all single-byte bigram models on clean CulturaX
corpora. While this modernized the codebase, users report:

1. Frequent `None` returns on short inputs (regression from 5.2.0)
2. Coverage.py slowdown from ~230 language model dict literals
3. New models not significantly more accurate, sometimes worse

The `add-symbols-to-alphabets` branch attempted category pseudo-rank
bigrams but introduced more regressions.

## Phase 1: Baseline Collection

Four baselines, each in an isolated git worktree, using `EncodingEra.ALL`
for apples-to-apples comparison. All baselines run against the test files
from `main`.

| Baseline | Source | Worktree |
|----------|--------|----------|
| 5.2.0 | tag `5.2.0` | `.worktrees/baseline-5.2.0` |
| 6.0.0 | tag `6.0.0` | `.worktrees/baseline-6.0.0` |
| main | branch `main` | `.worktrees/baseline-main` |
| add-symbols-to-alphabets | branch `add-symbols-to-alphabets` | `.worktrees/baseline-symbols` |

### Collection script

A shared script at `~/chardet_experiments/collect_baseline.py` that:

- Iterates all test files from main's `tests/` directory
- Runs `chardet.detect()` to determine pass/fail
- Runs `chardet.detect_all(ignore_threshold=True)` for all prober scores
- Handles API differences (5.2.0 has no `encoding_era` parameter)
- Writes JSON to `~/chardet_experiments/test_results_{version}.json`

### JSON format

```json
{
  "version": "6.0.0",
  "passed": ["tests/utf-8/foo.txt", ...],
  "failed": ["tests/iso-8859-1/bar.html", ...],
  "details": {
    "tests/utf-8/foo.txt": {
      "best_prober": "UTF-8",
      "probers": {
        "UTF-8": {
          "confidence": 0.99,
          "language": "",
          "encoding": "utf-8"
        },
        "Windows-1252 French": {
          "confidence": 0.12,
          "language": "French",
          "encoding": "Windows-1252"
        }
      }
    }
  }
}
```

### 5.2.0 considerations

- No `encoding_era` parameter — call `detect()` and `detect_all()` without it
- Different prober structure — adapt prober name extraction
- Test files from main may include encodings 5.2.0 doesn't support;
  record these as failures with a note

## Phase 2: Analysis Reports

After baselines are collected:

1. **Per-version reports** (`~/chardet_experiments/{version}_analysis_report.md`):
   - Failure categorization by encoding family
   - Byte-level pattern analysis on failed files
   - Short vs long input failure rates
   - Was correct encoding in top-3 probers?
   - Hypotheses about failure root causes

2. **Cross-version comparison** (`~/chardet_experiments/cross_version_comparison.md`):
   - Regressions: files 5.2.0 got right but 6.0.0/main get wrong
   - Improvements: files 6.0.0/main get right but 5.2.0 got wrong
   - Impact of post-release fixes (6.0.0 vs main)
   - Impact of category pseudo-ranks (main vs add-symbols-to-alphabets)

## Phase 3: Exploration Directions

Four directions, each in its own worktree and branch, explored in
parallel after baselines complete. Each produces results in the same
JSON format for comparison.

### Direction 1: Train on diverse data including markup

**Branch:** `experiment/diverse-training-data`

**Hypothesis:** 5.2.0 trained on Mozilla web crawl data that included
HTML/XML markup. The 6.0.0 CulturaX corpus is clean text only. Training
on markup-containing data may restore robustness on HTML/XML files.

**Steps:**
- Modify `create_language_model.py` to include markup in training
- Retrain models for encodings with the most baseline regressions
- Collect results in same JSON format, compare to baselines

### Direction 2: Collapse to per-encoding models

**Branch:** `experiment/per-encoding-models`

**Hypothesis:** Collapsing ~230 language-specific probers into ~40-50
per-encoding probers (one per encoding, trained on all languages) will:
- Reduce prober count, fixing coverage.py slowdown
- Provide more training data per model
- Potentially improve accuracy through broader bigram coverage
- Trade-off: lose language identification

**Steps:**
- Modify `create_language_model.py` to merge languages per encoding
- Retrain all single-byte encoding models
- Update `SBCSGroupProber` for collapsed models
- Collect results, compare to baselines

### Direction 3: Improve robustness on short inputs

**Branch:** `experiment/short-input-robustness`

**Hypothesis:** The multiplicative confidence formula collapses on short
inputs. The old `Latin1Prober` in 5.2.0 was hacky but robust. A better
confidence formula or short-input path could fix `None` returns.

**Steps:**
- Study 5.2.0's `Latin1Prober` implementation
- Identify short-input failures from baselines
- Experiment with confidence formula alternatives
- Test lower thresholds, additive components, Bayesian smoothing
- Collect results, compare to baselines

### Direction 4: Research advances in encoding detection

**Branch:** `experiment/research-advances`

**Hypothesis:** Encoding detection has advanced since the late 1990s
Mozilla algorithm. Modern libraries may use techniques we can adopt.

**Steps:**
- Research charset-normalizer, uchardet, ICU approaches
- Review WHATWG encoding spec
- Search for academic papers on encoding detection
- Document findings, prototype promising techniques
- Collect results if prototype built

## Phase 4: Synthesis

After all directions complete:

1. Compare all experimental results against baselines
2. Identify which changes are net-positive (fewer failures, no regressions)
3. Determine which changes compose well together
4. Recommend a merge plan for main
5. Primary goal: fully passing test suite with improved short-input accuracy
6. Secondary goal: reduced memory/CPU usage

## Constraints

- Zero new runtime dependencies
- Avoid increasing codebase complexity or size significantly
- Accuracy over speed
- Memory and CPU efficiency as secondary concern
- Test targeted files first, full suite only for promising changes
