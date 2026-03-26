"""Model loading and bigram scoring utilities.

Note: ``from __future__ import annotations`` is intentionally omitted because
this module is compiled with mypyc, which does not support PEP 563 string
annotations.
"""

import functools
import importlib.resources
import math
import struct
import warnings

from chardet.registry import REGISTRY, lookup_encoding

_unpack_uint32 = struct.Struct(">I").unpack_from
_iter_3bytes = struct.Struct(">BBB").iter_unpack

#: Flat fallback weight for non-ASCII bigrams when IDF is not yet available
#: (used only during the brief window before models are loaded).
#: Imported by pipeline/confusion.py for focused bigram re-scoring.
NON_ASCII_BIGRAM_WEIGHT: int = 8
# Encodings that map to exactly one language, derived from the registry.
# Keyed by canonical name only — callers always use canonical names.
_SINGLE_LANG_MAP: dict[str, str] = {}
for _enc in REGISTRY.values():
    if len(_enc.languages) == 1:
        _SINGLE_LANG_MAP[_enc.name] = _enc.languages[0]


def _parse_models_bin(
    data: bytes,
) -> tuple[dict[str, bytearray], dict[str, float]]:
    """Parse the binary models.bin format into model tables and L2 norms.

    :param data: Raw bytes of models.bin (must be non-empty).
    :returns: A ``(models, norms)`` tuple.
    :raises ValueError: If the data is corrupt or truncated.
    """
    models: dict[str, bytearray] = {}
    norms: dict[str, float] = {}
    _sqrt = math.sqrt
    _unpack_u32 = _unpack_uint32
    _iter_bbb = _iter_3bytes
    try:
        offset = 0
        (num_encodings,) = _unpack_u32(data, offset)
        offset += 4

        if num_encodings > 10_000:
            msg = f"corrupt models.bin: num_encodings={num_encodings} exceeds limit"
            raise ValueError(msg)

        for _ in range(num_encodings):
            (name_len,) = _unpack_u32(data, offset)
            offset += 4
            if name_len > 256:
                msg = f"corrupt models.bin: name_len={name_len} exceeds 256"
                raise ValueError(msg)
            name = data[offset : offset + name_len].decode("utf-8")
            offset += name_len
            (num_entries,) = _unpack_u32(data, offset)
            offset += 4
            if num_entries > 65536:
                msg = f"corrupt models.bin: num_entries={num_entries} exceeds 65536"
                raise ValueError(msg)

            table = bytearray(65536)
            sq_sum = 0
            expected_bytes = num_entries * 3
            chunk = data[offset : offset + expected_bytes]
            if len(chunk) != expected_bytes:
                msg = f"corrupt models.bin: truncated entry data for {name!r}"
                raise ValueError(msg)
            offset += expected_bytes
            for b1, b2, weight in _iter_bbb(chunk):
                table[(b1 << 8) | b2] = weight
                sq_sum += weight * weight
            models[name] = table
            norms[name] = _sqrt(sq_sum)
    except (struct.error, UnicodeDecodeError) as e:
        msg = f"corrupt models.bin: {e}"
        raise ValueError(msg) from e

    return models, norms


@functools.cache
def _load_models_data() -> tuple[dict[str, bytearray], dict[str, float]]:
    """Load and parse models.bin, returning (models, norms).

    Cached: only reads from disk on first call.
    """
    ref = importlib.resources.files("chardet.models").joinpath("models.bin")
    data = ref.read_bytes()

    if not data:
        warnings.warn(
            "chardet models.bin is empty — statistical detection disabled; "
            "reinstall chardet to fix",
            RuntimeWarning,
            stacklevel=2,
        )
        return {}, {}

    return _parse_models_bin(data)


def load_models() -> dict[str, bytearray]:
    """Load all bigram models from the bundled models.bin file.

    Each model is a bytearray of length 65536 (256*256).
    Index: (b1 << 8) | b2 -> weight (0-255).

    :returns: A dict mapping model key strings to 65536-byte lookup tables.
    """
    return _load_models_data()[0]


def _build_enc_index(
    models: dict[str, bytearray],
) -> dict[str, list[tuple[str | None, bytearray, str]]]:
    """Build a grouped index from a models dict.

    :param models: Mapping of ``"lang/encoding"`` keys to 65536-byte tables.
    :returns: Mapping of encoding name to ``[(lang, model, model_key), ...]``.
    """
    index: dict[str, list[tuple[str | None, bytearray, str]]] = {}
    for key, model in models.items():
        lang, enc = key.split("/", 1)
        index.setdefault(enc, []).append((lang, model, key))

    # Resolve aliases: if a model key uses a non-canonical name,
    # copy the entry under the canonical name.
    for enc_name in list(index):
        canonical = lookup_encoding(enc_name)
        if canonical is not None and canonical not in index:
            index[canonical] = index[enc_name]

    return index


@functools.cache
def get_enc_index() -> dict[str, list[tuple[str | None, bytearray, str]]]:
    """Return a pre-grouped index mapping encoding name -> [(lang, model, model_key), ...]."""
    return _build_enc_index(load_models())


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
    return encoding in get_enc_index()


def _get_model_norms() -> dict[str, float]:
    """Return cached L2 norms for all models, keyed by model key string."""
    return _load_models_data()[1]


@functools.cache
def get_idf_weights() -> bytearray:
    """Return a 65536-byte IDF weight table for bigram profile construction.

    For each bigram index, the weight reflects how discriminative that bigram
    is across all loaded models:

    - Bigrams in every model (common ASCII) → weight 1 (minimal signal)
    - Bigrams in one model → weight 255 (maximum signal)
    - Bigrams not in any model → weight 1 (unknown, treat as neutral)

    This replaces the flat ``NON_ASCII_BIGRAM_WEIGHT = 8`` with per-bigram
    IDF (inverse document frequency) weighting.  Computed once from the
    loaded models and cached.
    """
    models = load_models()
    num_models = len(models)
    if num_models == 0:
        return bytearray(65536)

    # Count how many models contain each bigram.
    doc_freq = bytearray(65536)  # uint8 is enough — max 352 models < 255
    # For >255 models, would need a wider array, but we cap at 255.
    for model in models.values():
        for idx in range(65536):
            if model[idx] and doc_freq[idx] < 255:
                doc_freq[idx] += 1

    # Map IDF to uint8 weights [1, 255].
    # idf = ln(num_models / doc_freq), max when doc_freq=1.
    _log = math.log
    max_idf = _log(num_models)  # IDF when bigram is in exactly 1 model
    if max_idf == 0:
        return bytearray(b"\x01" * 65536)

    scale = 254.0 / max_idf
    table = bytearray(65536)
    for idx in range(65536):
        df = doc_freq[idx]
        if df > 0:
            idf = _log(num_models / df)
            table[idx] = max(1, round(idf * scale) + 1)
        else:
            table[idx] = 1  # Not in any model — neutral weight
    return table


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

        Each bigram is weighted by its IDF (inverse document frequency) across
        all loaded models.  Bigrams unique to few models get high weight;
        bigrams common to all models get weight 1.

        :param data: The raw byte data to profile.
        """
        total_bigrams = len(data) - 1
        if total_bigrams <= 0:
            self.weighted_freq: dict[int, int] = {}
            self.weight_sum: int = 0
            self.input_norm: float = 0.0
            return

        idf = get_idf_weights()
        freq: dict[int, int] = {}
        w_sum = 0
        _get = freq.get
        for i in range(total_bigrams):
            idx = (data[i] << 8) | data[i + 1]
            w = idf[idx]
            freq[idx] = _get(idx, 0) + w
            w_sum += w
        self.weighted_freq = freq
        self.weight_sum = w_sum
        self.input_norm = math.sqrt(sum(v * v for v in freq.values()))

    @classmethod
    def from_weighted_freq(cls, weighted_freq: dict[int, int]) -> "BigramProfile":
        """Create a BigramProfile from pre-computed weighted frequencies.

        Computes ``weight_sum`` and ``input_norm`` from *weighted_freq* to
        ensure consistency between the three fields.

        :param weighted_freq: Mapping of bigram index to weighted count.
        :returns: A new :class:`BigramProfile` instance.
        """
        profile = cls(b"")
        profile.weighted_freq = weighted_freq
        profile.weight_sum = sum(weighted_freq.values())
        profile.input_norm = math.sqrt(sum(v * v for v in weighted_freq.values()))
        return profile


def score_with_profile(
    profile: BigramProfile, model: bytearray, model_key: str = ""
) -> float:
    """Score a pre-computed bigram profile against a single model using cosine similarity."""
    if profile.input_norm == 0.0:
        return 0.0
    norms = _get_model_norms()
    model_norm = norms.get(model_key) if model_key else None
    if model_norm is None:
        sq_sum = 0
        for i in range(65536):
            v = model[i]
            if v:
                sq_sum += v * v
        model_norm = math.sqrt(sq_sum)
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
    if not data and profile is None:
        return 0.0, None

    index = get_enc_index()
    variants = index.get(encoding)
    if variants is None:
        return 0.0, None

    if profile is None:
        profile = BigramProfile(data)

    best_score = 0.0
    best_lang: str | None = None
    for lang, model, model_key in variants:
        s = score_with_profile(profile, model, model_key)
        if s > best_score:
            best_score = s
            best_lang = lang

    return best_score, best_lang
