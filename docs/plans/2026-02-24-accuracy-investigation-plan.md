# Accuracy Investigation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Gather baselines across 4 chardet versions, analyze failure patterns, then explore 4 improvement directions in parallel to identify the best path forward for accuracy.

**Architecture:** A shared collection script writes standardized JSON results to `~/chardet_experiments/`. Each baseline and experiment runs in an isolated git worktree via subagents. Analysis happens in the main agent after results are collected.

**Tech Stack:** Python 3.10+, chardet (various versions), git worktrees

---

### Task 1: Create experiment infrastructure

**Files:**
- Create: `~/chardet_experiments/collect_baseline.py`

**Step 1: Create the experiments directory**

Run: `mkdir -p ~/chardet_experiments`

**Step 2: Write the baseline collection script**

Create `~/chardet_experiments/collect_baseline.py` — a version-aware script that:

1. Takes arguments: `--version` (label), `--test-dir` (path to main's tests/), `--output` (JSON path)
2. Iterates all test files in `--test-dir`, deriving expected encoding from directory name (stripping language suffixes using the same logic as `test.py:gen_test_params()`)
3. For each file:
   - Reads the bytes
   - Calls `chardet.detect()` (no `encoding_era` for 5.2.0; `encoding_era=EncodingEra.ALL` for 6.0.0+)
   - Calls `chardet.detect_all(ignore_threshold=True)` (same version-awareness)
   - Determines pass/fail by comparing detected encoding to expected (case-insensitive), with the same NFKC-decode-comparison fallback as `test.py`
   - Records all prober results from `detect_all()` into the details map
4. Writes JSON in the specified format:

```json
{
  "version": "...",
  "passed": ["tests/utf-8/foo.txt", ...],
  "failed": ["tests/iso-8859-1/bar.html", ...],
  "details": {
    "tests/utf-8/foo.txt": {
      "expected_encoding": "utf-8",
      "detected_encoding": "utf-8",
      "detected_confidence": 0.99,
      "best_prober": "UTF-8",
      "probers": {
        "UTF-8": {"confidence": 0.99, "language": "", "encoding": "utf-8"},
        ...
      }
    }
  }
}
```

**Version detection logic:** The script should import chardet and check `chardet.__version__` to determine which API to use:
- If version starts with "5.": call `detect(data)` and `detect_all(data, ignore_threshold=True)` without `encoding_era`
- Otherwise: call `detect(data, encoding_era=EncodingEra.ALL, should_rename_legacy=False)` and `detect_all(data, ignore_threshold=True, encoding_era=EncodingEra.ALL, should_rename_legacy=False)`

**Language suffix stripping:** Import the language list from the chardet version in the worktree. For 5.2.0 use `chardet.metadata.languages.LANGUAGES` if available, otherwise hardcode the known languages from main's metadata. The key thing is consistent test file → expected encoding mapping across all versions.

**Step 3: Verify the script is syntactically correct**

Run: `uv run python -c "import ast; ast.parse(open(os.path.expanduser('~/chardet_experiments/collect_baseline.py')).read()); print('OK')"` (or equivalent)

**Step 4: Commit infrastructure**

No commit needed — this script lives outside the repo in `~/chardet_experiments/`.

---

### Task 2: Gather baseline — chardet 5.2.0

**Runs in: subagent with worktree**

**Step 1: Create worktree**

```bash
cd /Users/danblanchard/repos/chardet
git worktree add .worktrees/baseline-5.2.0 5.2.0
```

**Step 2: Copy test files from main**

The 5.2.0 tag has fewer test files. Copy main's test directory into the worktree:

```bash
rm -rf .worktrees/baseline-5.2.0/tests
cp -r tests .worktrees/baseline-5.2.0/tests
```

**Step 3: Install dependencies**

```bash
cd .worktrees/baseline-5.2.0
uv sync
```

Note: If `uv sync` fails because 5.2.0 doesn't have a `uv.lock` or compatible `pyproject.toml`, fall back to:

```bash
cd .worktrees/baseline-5.2.0
uv venv
uv pip install -e .
```

**Step 4: Run collection**

```bash
cd .worktrees/baseline-5.2.0
uv run python ~/chardet_experiments/collect_baseline.py \
  --version "5.2.0" \
  --test-dir tests \
  --output ~/chardet_experiments/test_results_5.2.0.json
```

**Step 5: Verify output**

```bash
python -c "
import json
with open(os.path.expanduser('~/chardet_experiments/test_results_5.2.0.json')) as f:
    data = json.load(f)
print(f'Version: {data[\"version\"]}')
print(f'Passed: {len(data[\"passed\"])}')
print(f'Failed: {len(data[\"failed\"])}')
print(f'Details entries: {len(data[\"details\"])}')
"
```

**Step 6: Write analysis report**

Analyze the failures and write `~/chardet_experiments/5.2.0_analysis_report.md` covering:
- Total pass/fail counts
- Failure breakdown by encoding family (EBCDIC, DOS, Latin, Cyrillic, etc.)
- Short vs long file failures (< 500 bytes vs > 500 bytes)
- Top 10 most-confused encoding pairs
- Files where correct encoding was in top-3 probers but didn't win
- Hypotheses about failure patterns

---

### Task 3: Gather baseline — chardet 6.0.0

**Runs in: subagent with worktree**

Same structure as Task 2, but:

```bash
git worktree add .worktrees/baseline-6.0.0 6.0.0
rm -rf .worktrees/baseline-6.0.0/tests
cp -r tests .worktrees/baseline-6.0.0/tests
cd .worktrees/baseline-6.0.0
uv sync
uv run python ~/chardet_experiments/collect_baseline.py \
  --version "6.0.0" \
  --test-dir tests \
  --output ~/chardet_experiments/test_results_6.0.0.json
```

Write analysis to `~/chardet_experiments/6.0.0_analysis_report.md`.

---

### Task 4: Gather baseline — current main

**Runs in: subagent with worktree**

```bash
git worktree add .worktrees/baseline-main main
cd .worktrees/baseline-main
uv sync
uv run python ~/chardet_experiments/collect_baseline.py \
  --version "main" \
  --test-dir tests \
  --output ~/chardet_experiments/test_results_main.json
```

Write analysis to `~/chardet_experiments/main_analysis_report.md`.

---

### Task 5: Gather baseline — add-symbols-to-alphabets

**Runs in: subagent with worktree**

```bash
git worktree add .worktrees/baseline-symbols add-symbols-to-alphabets
rm -rf .worktrees/baseline-symbols/tests
cp -r tests .worktrees/baseline-symbols/tests
cd .worktrees/baseline-symbols
uv sync
uv run python ~/chardet_experiments/collect_baseline.py \
  --version "add-symbols-to-alphabets" \
  --test-dir tests \
  --output ~/chardet_experiments/test_results_add-symbols-to-alphabets.json
```

Write analysis to `~/chardet_experiments/add-symbols-to-alphabets_analysis_report.md`.

---

### Task 6: Cross-version comparison

**Runs in: main agent after Tasks 2-5 complete**

**Step 1: Write comparison script or analyze directly**

Load all 4 JSON files and produce `~/chardet_experiments/cross_version_comparison.md`:

- **Regressions table:** Files that 5.2.0 got right but later versions get wrong
- **Improvements table:** Files that later versions get right but 5.2.0 got wrong
- **Post-release fix impact:** Diff between 6.0.0 and main
- **Symbols branch impact:** Diff between main and add-symbols-to-alphabets
- **Confidence distribution analysis:** How do confidence scores compare across versions for the same files?
- **Short input analysis:** Specifically identify files < 500 bytes where results differ
- **Encoding family heatmap:** Which families regressed most? Which improved?
- **Key hypotheses:** Based on all the data, what are the most promising directions?

---

### Task 7: Direction 1 — Diverse training data

**Runs in: subagent with worktree, after Task 6**

**Step 1: Create worktree**

```bash
git worktree add .worktrees/experiment-diverse -b experiment/diverse-training-data main
cd .worktrees/experiment-diverse
uv sync
```

**Step 2: Analyze what training data modifications are needed**

Examine the cross-version comparison to identify which encodings regressed most. Focus on files that are HTML/XML (check file extensions and byte content).

**Step 3: Modify create_language_model.py**

The CulturaX dataset is clean text. Options to add markup:
- Add a `--include-markup` flag that mixes in HTML-like patterns (tags, entities, attributes) around the training text
- Or find a web crawl data source that includes markup
- Or synthetically wrap training text in common HTML patterns

The key insight is that real-world encoding detection often encounters `<html>`, `<meta charset=...>`, `<p>`, entity references, etc. These are ASCII-heavy patterns that should not destroy confidence.

**Step 4: Retrain affected models**

Focus on encodings with the most regressions from the baseline analysis. Use the cached unfiltered bigrams where possible.

```bash
uv run python create_language_model.py <language> -p 1
mv lang*model.py chardet/
```

**Step 5: Run collection and compare**

```bash
uv run python ~/chardet_experiments/collect_baseline.py \
  --version "experiment-diverse" \
  --test-dir tests \
  --output ~/chardet_experiments/test_results_experiment-diverse.json
```

Write analysis to `~/chardet_experiments/experiment-diverse_analysis_report.md`, comparing against all baselines.

---

### Task 8: Direction 2 — Per-encoding models

**Runs in: subagent with worktree, after Task 6**

**Step 1: Create worktree**

```bash
git worktree add .worktrees/experiment-per-encoding -b experiment/per-encoding-models main
cd .worktrees/experiment-per-encoding
uv sync
```

**Step 2: Modify create_language_model.py to support per-encoding training**

Add a new mode (e.g., `--per-encoding`) that:
1. For each single-byte encoding (e.g., `ISO-8859-1`), finds ALL languages that use it (from `metadata/languages.py`)
2. Merges the cached unfiltered bigrams from all those languages
3. Trains a single model per encoding with a combined alphabet
4. Generates a model file per encoding (e.g., `langiso88591model.py`) instead of per language

The cached `*_unfiltered_bigrams.json` files (47 available) contain raw character frequencies and bigram counts. Merging means summing the `char_freqs` and `language_model` counters from all relevant language caches.

**Step 3: Generate per-encoding model files**

```bash
uv run python create_language_model.py --per-encoding -p 1
mv lang*model.py chardet/
```

**Step 4: Update SBCSGroupProber**

Modify `chardet/sbcsgroupprober.py` to import and register the per-encoding models instead of the per-language ones. This should dramatically reduce the prober list from ~230 to ~40-50.

**Step 5: Update imports in chardet package**

Make sure new model files are properly imported and old per-language imports are removed.

**Step 6: Run tests on targeted failures first**

Pick 10-20 files that were regressions in the baseline analysis and test them individually:

```bash
uv run python -c "
import chardet
from chardet.enums import EncodingEra
with open('tests/some-encoding/somefile.txt', 'rb') as f:
    print(chardet.detect(f.read(), encoding_era=EncodingEra.ALL, should_rename_legacy=False))
"
```

**Step 7: Run full collection**

```bash
uv run python ~/chardet_experiments/collect_baseline.py \
  --version "experiment-per-encoding" \
  --test-dir tests \
  --output ~/chardet_experiments/test_results_experiment-per-encoding.json
```

Write analysis to `~/chardet_experiments/experiment-per-encoding_analysis_report.md`.

---

### Task 9: Direction 3 — Short input robustness

**Runs in: subagent with worktree, after Task 6**

**Step 1: Create worktree**

```bash
git worktree add .worktrees/experiment-short-input -b experiment/short-input-robustness main
cd .worktrees/experiment-short-input
uv sync
```

**Step 2: Study 5.2.0's Latin1Prober**

The 5.2.0 `Latin1Prober` (at tag `5.2.0:chardet/latin1prober.py`) uses:
- 8 character classes (UDF, OTH, ASC, ASS, ACV, ACO, ASV, ASO)
- A class-to-class transition model (8x8 = 64 entries) with 4 frequency categories
- Simple confidence: `(freq[3] - freq[1] * 20) / total * 0.73`

This is fundamentally different from the current bigram approach. It's robust on short inputs because:
- It counts broad character CLASS transitions, not specific character bigrams
- It accumulates evidence faster (every byte contributes)
- The `* 0.73` cap prevents it from overwhelming other probers

**Step 3: Analyze short-input failures from baselines**

From the cross-version comparison, extract all files < 500 bytes where main returns `None` or wrong encoding. Group by:
- Files where 5.2.0 succeeded but main fails
- The confidence scores of all probers for these files
- Common byte patterns in these files

**Step 4: Experiment with confidence formula changes**

The current formula in `sbcharsetprober.py:get_confidence()` multiplies 4 factors:

```python
r = (positive_seqs / total_seqs / typical_positive_ratio)  # Factor 1
r *= (positive_seqs + likely_seqs/4) / total_char           # Factor 2
r *= (total_char - control_char) / total_char                # Factor 3
r *= freq_char / total_char                                  # Factor 4
```

On short inputs, `total_seqs` and `total_char` are small, making individual factors volatile. Experiments to try:

**Experiment A:** Add minimum floors to each factor:
```python
r = max(positive_seqs / total_seqs / typical_positive_ratio, 0.1)
```

**Experiment B:** Use additive combination instead of multiplicative:
```python
r = 0.4 * (positive_seqs / total_seqs / typical_positive_ratio)
  + 0.3 * ((positive_seqs + likely_seqs/4) / total_char)
  + 0.15 * ((total_char - control_char) / total_char)
  + 0.15 * (freq_char / total_char)
```

**Experiment C:** Bayesian smoothing — add pseudo-counts:
```python
smoothed_positive = (positive_seqs + 1) / (total_seqs + 4)
```

**Experiment D:** Short-input path — if `total_seqs < SB_ENOUGH_REL_THRESHOLD`, use a simplified formula.

**Step 5: Also look at the fallback in UniversalDetector.close()**

Currently, when no prober meets `MINIMUM_THRESHOLD` and UTF-8 is ruled out, it returns `None`. The existing fallback-encoding design doc (`docs/plans/2026-02-23-fallback-encoding-design.md`) proposes returning the best prober's result. This should be implemented here since it directly addresses the `None` return problem.

**Step 6: Test each experiment on short-input failures**

For each experiment, test against the short-input failures identified in Step 3.

**Step 7: Run full collection for the best experiment**

```bash
uv run python ~/chardet_experiments/collect_baseline.py \
  --version "experiment-short-input" \
  --test-dir tests \
  --output ~/chardet_experiments/test_results_experiment-short-input.json
```

Write analysis to `~/chardet_experiments/experiment-short-input_analysis_report.md`.

---

### Task 10: Direction 4 — Research advances

**Runs in: subagent (no worktree needed initially — research first)**

**Step 1: Research modern encoding detection approaches**

Investigate these specific sources:

1. **charset-normalizer** (https://github.com/Ousret/charset_normalizer): How does it achieve better accuracy? What's its detection algorithm? Does it use n-grams, ML, or something else?

2. **uchardet** (https://github.com/BYVoid/uchardet): What improvements has it made over the original Mozilla code? Check recent commits and issues.

3. **WHATWG Encoding Standard** (https://encoding.spec.whatwg.org/): What does the spec say about encoding sniffing for web content?

4. **ICU CharsetDetector**: What algorithm does ICU use? Is it documented?

5. **Academic papers**: Search for "character encoding detection" papers from 2010+.

6. **Byte-level approaches**: Are there approaches that work directly on byte distributions rather than character distributions (which require knowing the encoding first)?

**Step 2: Document findings**

Write `~/chardet_experiments/research_advances_report.md` covering:
- Summary of each approach
- Key differences from chardet's current algorithm
- Techniques that could be adopted without adding dependencies
- Feasibility assessment for each technique
- Recommended techniques to prototype

**Step 3: Prototype if promising technique found**

If research reveals a promising technique that can be implemented without new dependencies:

```bash
git worktree add .worktrees/experiment-research -b experiment/research-advances main
cd .worktrees/experiment-research
uv sync
```

Implement the technique, run collection, write analysis.

---

### Task 11: Synthesis and recommendations

**Runs in: main agent after Tasks 7-10 complete**

**Step 1: Load all experimental results**

Compare all JSON files:
- `test_results_5.2.0.json` (baseline)
- `test_results_6.0.0.json` (baseline)
- `test_results_main.json` (baseline)
- `test_results_add-symbols-to-alphabets.json` (baseline)
- `test_results_experiment-diverse.json` (direction 1)
- `test_results_experiment-per-encoding.json` (direction 2)
- `test_results_experiment-short-input.json` (direction 3)
- Any direction 4 prototypes

**Step 2: Produce synthesis report**

Write `~/chardet_experiments/synthesis_report.md`:
- Pass/fail counts for each version/experiment
- Net regressions and improvements vs main for each direction
- Which directions compose well (e.g., can we combine per-encoding models with short-input robustness?)
- Recommended merge order
- Remaining expected failures that are genuinely ambiguous

**Step 3: Present recommendations to user**

Summarize findings and propose a merge plan with specific branches to merge and in what order.

---

## Execution Notes

### Parallelism strategy

- **Tasks 2-5** (baselines): Run all 4 in parallel subagents, each in its own worktree
- **Task 6** (cross-comparison): Runs after all baselines complete
- **Tasks 7-10** (directions): Run all 4 in parallel subagents after Task 6
- **Task 11** (synthesis): Runs after all directions complete

### Worktree management

After each baseline/experiment completes and results are saved to `~/chardet_experiments/`, the worktree can be cleaned up:

```bash
git worktree remove .worktrees/<name>
```

Keep experiment worktrees alive until synthesis is complete in case we need to re-examine.

### Important constraints

- **5.2.0 API:** No `encoding_era`, no `should_rename_legacy` as keyword-only. Use `detect(data)` and `detect_all(data, ignore_threshold=True)`.
- **Training hangs:** `create_language_model.py` may hang with parallelism > 1. Use `-p 1` and kill after 2 minutes if stuck.
- **Test-first approach:** For experiments, test targeted files before running full suite (2180 files is slow).
- **No new dependencies:** All solutions must work with zero runtime dependencies.
- **Cached bigrams:** 47 `*_unfiltered_bigrams.json` files exist in the repo root, making retraining fast.
