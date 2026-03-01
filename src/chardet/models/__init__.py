"""Model loading and bigram scoring utilities.

Note: ``from __future__ import annotations`` is intentionally omitted because
this module is compiled with mypyc, which does not support PEP 563 string
annotations.
"""

import importlib.resources
import math
import struct
import threading

_MODEL_CACHE: dict[str, bytearray] | None = None
_MODEL_CACHE_LOCK = threading.Lock()
# Pre-grouped index: encoding name -> [(lang, model), ...]
_ENC_INDEX: dict[str, list[tuple[str | None, bytearray]]] | None = None
_ENC_INDEX_LOCK = threading.Lock()
# Cached L2 norms for all models, keyed by id(model)
_MODEL_NORMS: dict[int, float] | None = None
_MODEL_NORMS_LOCK = threading.Lock()
# Encodings that map to exactly one language.  Includes gb2312 which has no
# bigram model of its own but is unambiguously Chinese.
_SINGLE_LANG_MAP: dict[str, str] = {
    "big5": "zh",
    "cp1006": "ur",
    "cp1026": "tr",
    "cp1125": "uk",
    "cp424": "he",
    "cp737": "el",
    "cp856": "he",
    "cp857": "tr",
    "cp860": "pt",
    "cp861": "is",
    "cp862": "he",
    "cp863": "fr",
    "cp864": "ar",
    "cp869": "el",
    "cp874": "th",
    "cp875": "el",
    "cp932": "ja",
    "cp949": "ko",
    "euc-jp": "ja",
    "euc-kr": "ko",
    "gb18030": "zh",
    "gb2312": "zh",
    "hz-gb-2312": "zh",
    "iso-2022-jp": "ja",
    "iso-2022-kr": "ko",
    "iso-8859-7": "el",
    "iso-8859-8": "he",
    "iso-8859-9": "tr",
    "johab": "ko",
    "koi8-r": "ru",
    "koi8-t": "tg",
    "koi8-u": "uk",
    "kz-1048": "kk",
    "mac-greek": "el",
    "mac-iceland": "is",
    "mac-turkish": "tr",
    "ptcp154": "kk",
    "shift_jis": "ja",
    "tis-620": "th",
    "windows-1253": "el",
    "windows-1254": "tr",
    "windows-1255": "he",
    "windows-1258": "vi",
}


def load_models() -> dict[str, bytearray]:
    """Load all bigram models from the bundled models.bin file.

    Each model is a bytearray of length 65536 (256*256).
    Index: (b1 << 8) | b2 -> weight (0-255).

    :returns: A dict mapping model key strings to 65536-byte lookup tables.
    """
    global _MODEL_CACHE  # noqa: PLW0603
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    with _MODEL_CACHE_LOCK:
        # No re-check: mypyc type-narrows _MODEL_CACHE to None after the
        # outer check, so a re-read here would hit a TypeError under mypyc.
        # Worst case two threads both build on first call (idempotent).
        models: dict[str, bytearray] = {}
        ref = importlib.resources.files("chardet.models").joinpath("models.bin")
        data = ref.read_bytes()

        if not data:
            _MODEL_CACHE = models
            return models

        try:
            offset = 0
            (num_encodings,) = struct.unpack_from("!I", data, offset)
            offset += 4

            if num_encodings > 10_000:
                msg = f"corrupt models.bin: num_encodings={num_encodings} exceeds limit"
                raise ValueError(msg)

            for _ in range(num_encodings):
                (name_len,) = struct.unpack_from("!I", data, offset)
                offset += 4
                name = data[offset : offset + name_len].decode("utf-8")
                offset += name_len
                (num_entries,) = struct.unpack_from("!I", data, offset)
                offset += 4

                table = bytearray(65536)
                for _ in range(num_entries):
                    b1, b2, weight = struct.unpack_from("!BBB", data, offset)
                    offset += 3
                    table[(b1 << 8) | b2] = weight
                models[name] = table
        except (struct.error, UnicodeDecodeError) as e:
            msg = f"corrupt models.bin: {e}"
            raise ValueError(msg) from e

        _MODEL_CACHE = models
        return models


def _get_enc_index() -> dict[str, list[tuple[str | None, bytearray]]]:
    """Return a pre-grouped index mapping encoding name -> [(lang, model), ...]."""
    global _ENC_INDEX  # noqa: PLW0603
    if _ENC_INDEX is not None:
        return _ENC_INDEX
    with _ENC_INDEX_LOCK:
        # No re-check: mypyc type-narrows _ENC_INDEX to None after the
        # outer check, so a re-read here would hit a TypeError under mypyc.
        models = load_models()
        index: dict[str, list[tuple[str | None, bytearray]]] = {}
        for key, model in models.items():
            if "/" in key:
                lang, enc = key.split("/", 1)
                index.setdefault(enc, []).append((lang, model))
            else:
                # Plain encoding key (backward compat / fallback)
                index.setdefault(key, []).append((None, model))
        _ENC_INDEX = index
        return index


def infer_language(encoding: str) -> str | None:
    """Return the language for a single-language encoding, or None.

    :param encoding: The canonical encoding name.
    :returns: An ISO 639-1 language code, or ``None`` if the encoding is
        multi-language.
    """
    return _SINGLE_LANG_MAP.get(encoding)


def has_model_variants(encoding: str) -> bool:
    """Return True if the encoding has language variants in the model index.

    :param encoding: The canonical encoding name.
    :returns: ``True`` if bigram models exist for this encoding.
    """
    return encoding in _get_enc_index()


def _get_model_norms() -> dict[int, float]:
    """Return cached L2 norms for all models, keyed by id(model)."""
    global _MODEL_NORMS  # noqa: PLW0603
    if _MODEL_NORMS is not None:
        return _MODEL_NORMS
    with _MODEL_NORMS_LOCK:
        # No re-check: mypyc type-narrows _MODEL_NORMS to None after the
        # outer check, so a re-read here would hit a TypeError under mypyc.
        models = load_models()
        norms: dict[int, float] = {}
        for model in models.values():
            mid = id(model)
            if mid not in norms:
                sq_sum = 0
                for i in range(65536):
                    v = model[i]
                    if v:
                        sq_sum += v * v
                norms[mid] = math.sqrt(sq_sum)
        _MODEL_NORMS = norms
        return norms


class BigramProfile:
    """Pre-computed bigram frequency distribution for a data sample.

    Computing this once and reusing it across all models reduces per-model
    scoring from O(n) to O(distinct_bigrams).

    Stores a single ``weighted_freq`` dict mapping bigram index to
    *count * weight* (weight is 8 for non-ASCII bigrams, 1 otherwise).
    This pre-multiplies the weight during construction so the scoring
    inner loop only needs a single dict traversal with no branching.
    """

    __slots__ = ("input_norm", "weight_sum", "weighted_freq")

    def __init__(self, data: bytes) -> None:
        """Compute the bigram frequency distribution for *data*.

        :param data: The raw byte data to profile.
        """
        total_bigrams = len(data) - 1
        if total_bigrams <= 0:
            self.weighted_freq: dict[int, int] = {}
            self.weight_sum: int = 0
            self.input_norm: float = 0.0
            return

        freq: dict[int, int] = {}
        w_sum = 0
        _get = freq.get
        for i in range(total_bigrams):
            b1 = data[i]
            b2 = data[i + 1]
            idx = (b1 << 8) | b2
            if b1 > 0x7F or b2 > 0x7F:
                freq[idx] = _get(idx, 0) + 8
                w_sum += 8
            else:
                freq[idx] = _get(idx, 0) + 1
                w_sum += 1
        self.weighted_freq = freq
        self.weight_sum = w_sum
        self.input_norm = math.sqrt(sum(v * v for v in freq.values()))

    @classmethod
    def from_weighted_freq(
        cls, weighted_freq: dict[int, int], weight_sum: int
    ) -> "BigramProfile":
        """Create a BigramProfile from pre-computed weighted frequencies.

        :param weighted_freq: Mapping of bigram index to weighted count.
        :param weight_sum: The total sum of all weights.
        :returns: A new :class:`BigramProfile` instance.
        """
        profile = cls(b"")
        profile.weighted_freq = weighted_freq
        profile.weight_sum = weight_sum
        profile.input_norm = math.sqrt(sum(v * v for v in weighted_freq.values()))
        return profile


def _score_with_profile(profile: BigramProfile, model: bytearray) -> float:
    """Score a pre-computed bigram profile against a single model using cosine similarity."""
    if profile.input_norm == 0.0:
        return 0.0
    norms = _get_model_norms()
    model_norm = norms.get(id(model), 0.0)
    if model_norm == 0.0:
        return 0.0
    dot = 0
    for idx, wcount in profile.weighted_freq.items():
        dot += model[idx] * wcount
    return dot / (model_norm * profile.input_norm)


def score_best_language(
    data: bytes,
    encoding: str,
    profile: BigramProfile | None = None,
) -> tuple[float, str | None]:
    """Score data against all language variants of an encoding.

    Returns (best_score, best_language). Uses a pre-grouped index for O(L)
    lookup where L is the number of language variants for the encoding.

    If *profile* is provided, it is reused instead of recomputing the bigram
    frequency distribution from *data*.

    :param data: The raw byte data to score.
    :param encoding: The canonical encoding name to match against.
    :param profile: Optional pre-computed :class:`BigramProfile` to reuse.
    :returns: A ``(score, language)`` tuple with the best cosine-similarity
        score and the corresponding language code (or ``None``).
    """
    if not data:
        return 0.0, None

    index = _get_enc_index()
    variants = index.get(encoding)
    if variants is None:
        return 0.0, None

    if profile is None:
        profile = BigramProfile(data)

    best_score = 0.0
    best_lang: str | None = None
    for lang, model in variants:
        s = _score_with_profile(profile, model)
        if s > best_score:
            best_score = s
            best_lang = lang

    return best_score, best_lang
