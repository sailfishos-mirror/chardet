"""Post-decode mess detection.

Scores decoded Unicode text for signs that the wrong encoding was used.
Inspired by charset-normalizer's mess detection approach.
"""

from __future__ import annotations

import unicodedata

_COMMON_CONTROL = {"\t", "\n", "\r"}
_SKIP_SCRIPTS = {"Common", "Inherited"}
# Cap the number of characters to inspect.  10k is sufficient for a stable
# score and avoids O(candidates * file_size) blowup on large files.
_MAX_SAMPLE_CHARS = 10_000

# Cache NFKD accent checks — real text has a small vocabulary of distinct
# letter codepoints, so a per-codepoint cache avoids repeated normalization.
_accent_cache: dict[str, bool] = {}


def _is_accented(ch: str) -> bool:
    """Return True if *ch* is a letter with combining marks after NFKD."""
    result = _accent_cache.get(ch)
    if result is None:
        decomposed = unicodedata.normalize("NFKD", ch)
        result = len(decomposed) > 1 and any(
            unicodedata.combining(c) for c in decomposed
        )
        _accent_cache[ch] = result
    return result


def compute_mess_score(text: str) -> float:
    """Return a mess score for decoded text. 0.0 = clean, 1.0 = very messy.

    Checks for:
    1. Unprintable characters (category Cc, excluding tab/newline/CR)
    2. Excessive accented characters (>40% of alphabetic chars)
    3. Suspicious adjacent script mixing (Python 3.13+ only)
    """
    if not text:
        return 0.0

    text = text[:_MAX_SAMPLE_CHARS]
    total = len(text)
    unprintable_count = 0
    alpha_count = 0
    accented_count = 0
    prev_script = None
    script_changes = 0
    non_space_count = 0

    for ch in text:
        cat = unicodedata.category(ch)

        # 1. Unprintable — only true control chars (Cc), not format chars (Cf).
        # Cf includes legitimate characters like ZWJ, RTL marks, and soft
        # hyphens that appear in Arabic, Hebrew, and word-processed text.
        if cat == "Cc" and ch not in _COMMON_CONTROL:
            unprintable_count += 1

        # 2. Accent tracking
        if cat.startswith("L"):
            alpha_count += 1
            if _is_accented(ch):
                accented_count += 1

        # 3. Script mixing (Python 3.13+ only)
        if not ch.isspace():
            non_space_count += 1
            try:
                script = unicodedata.script(ch)
            except (AttributeError, ValueError):
                script = None
            if (
                script is not None
                and prev_script is not None
                and script not in _SKIP_SCRIPTS
                and prev_script not in _SKIP_SCRIPTS
                and script != prev_script
            ):
                script_changes += 1
            if script is not None and script not in _SKIP_SCRIPTS:
                prev_script = script

    # Compute component scores
    unprintable_ratio = unprintable_count / total
    accent_ratio = accented_count / alpha_count if alpha_count > 10 else 0.0
    script_ratio = script_changes / non_space_count if non_space_count > 10 else 0.0

    # Weight unprintable chars heavily, accent excess moderately.
    # Cap unprintable contribution at 0.8 so a single control char in a
    # short string doesn't produce maximum mess on its own.
    score = (
        min(unprintable_ratio * 8.0, 0.8)
        + max(0.0, accent_ratio - 0.40) * 2.0  # Only penalize above 40%
        + script_ratio * 3.0
    )

    return min(score, 1.0)
