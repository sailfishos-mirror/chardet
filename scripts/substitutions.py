"""Character substitution tables for legacy encoding training.

Maps modern Unicode characters to their legacy encoding equivalents,
enabling training on modern text for historical code pages.
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Universal substitutions
# ---------------------------------------------------------------------------

# Universal substitutions for all single-byte encodings: replace modern
# typographic punctuation with ASCII equivalents that would have been used
# historically in legacy encodings.
_UNIVERSAL_SUBSTITUTIONS: dict[str, str] = {
    # Dashes
    "\u2010": "-",  # HYPHEN
    "\u2011": "-",  # NON-BREAKING HYPHEN
    "\u2012": "-",  # FIGURE DASH
    "\u2013": "-",  # EN DASH
    "\u2014": "-",  # EM DASH
    "\u2015": "-",  # HORIZONTAL BAR
    # Quotes
    "\u2018": "'",  # LEFT SINGLE QUOTATION MARK
    "\u2019": "'",  # RIGHT SINGLE QUOTATION MARK
    "\u201a": "'",  # SINGLE LOW-9 QUOTATION MARK
    "\u201b": "'",  # SINGLE HIGH-REVERSED-9 QUOTATION MARK
    "\u201c": '"',  # LEFT DOUBLE QUOTATION MARK
    "\u201d": '"',  # RIGHT DOUBLE QUOTATION MARK
    "\u201e": '"',  # DOUBLE LOW-9 QUOTATION MARK
    "\u201f": '"',  # DOUBLE HIGH-REVERSED-9 QUOTATION MARK
    # Ellipsis
    "\u2026": "...",  # HORIZONTAL ELLIPSIS
    # Spaces
    "\u00a0": " ",  # NO-BREAK SPACE
    "\u2002": " ",  # EN SPACE
    "\u2003": " ",  # EM SPACE
    "\u2009": " ",  # THIN SPACE
    "\u200a": " ",  # HAIR SPACE
    # Other common punctuation
    "\u2022": "*",  # BULLET
    "\u2032": "'",  # PRIME
    "\u2033": '"',  # DOUBLE PRIME
    "\u2212": "-",  # MINUS SIGN
    # Zero-width and formatting characters (remove)
    "\u200b": "",  # ZERO WIDTH SPACE
    "\u200c": "",  # ZERO WIDTH NON-JOINER
    "\u200d": "",  # ZERO WIDTH JOINER
    "\u200e": "",  # LEFT-TO-RIGHT MARK
    "\u200f": "",  # RIGHT-TO-LEFT MARK
    "\ufeff": "",  # ZERO WIDTH NO-BREAK SPACE (BOM)
}

# ---------------------------------------------------------------------------
# Arabic substitutions
# ---------------------------------------------------------------------------

# Arabic-specific substitutions for limited code pages
_ARABIC_SUBSTITUTIONS: dict[str, str] = {
    "\u060c": ",",  # ARABIC COMMA
    "\u061b": ";",  # ARABIC SEMICOLON
    "\u061f": "?",  # ARABIC QUESTION MARK (missing from CP720)
    "\u066a": "%",  # ARABIC PERCENT SIGN
    # Standard Arabic-Indic digits → Western digits (missing from CP720/ISO-8859-6)
    "\u0660": "0",
    "\u0661": "1",
    "\u0662": "2",
    "\u0663": "3",
    "\u0664": "4",
    "\u0665": "5",
    "\u0666": "6",
    "\u0667": "7",
    "\u0668": "8",
    "\u0669": "9",
}

# Arabic standard letters → isolated presentation forms for encodings
# that use presentation forms (CP1006, CP864).  Modern Unicode uses
# standard Arabic letters (U+0621-U+064A) but these legacy encodings
# store the positional presentation forms (U+FE70-U+FEFF) instead.
# Using the isolated form as a catch-all is historically accurate for
# training data that contains standalone or mixed-context Arabic text.
_ARABIC_PRESENTATION_FORM_SUBSTITUTIONS: dict[str, str] = {
    "\u0621": "\ufe80",  # HAMZA
    "\u0622": "\ufe81",  # ALEF WITH MADDA ABOVE
    "\u0623": "\ufe83",  # ALEF WITH HAMZA ABOVE
    "\u0624": "\ufe85",  # WAW WITH HAMZA ABOVE
    "\u0625": "\ufe87",  # ALEF WITH HAMZA BELOW
    "\u0626": "\ufe89",  # YEH WITH HAMZA ABOVE
    "\u0627": "\ufe8d",  # ALEF
    "\u0628": "\ufe8f",  # BEH
    "\u0629": "\ufe93",  # TEH MARBUTA
    "\u062a": "\ufe95",  # TEH
    "\u062b": "\ufe99",  # THEH
    "\u062c": "\ufe9d",  # JEEM
    "\u062d": "\ufea1",  # HAH
    "\u062e": "\ufea5",  # KHAH
    "\u062f": "\ufea9",  # DAL
    "\u0630": "\ufeab",  # THAL
    "\u0631": "\ufead",  # REH
    "\u0632": "\ufeaf",  # ZAIN
    "\u0633": "\ufeb1",  # SEEN
    "\u0634": "\ufeb5",  # SHEEN
    "\u0635": "\ufeb9",  # SAD
    "\u0636": "\ufebd",  # DAD
    "\u0637": "\ufec1",  # TAH
    "\u0638": "\ufec5",  # ZAH
    "\u0639": "\ufec9",  # AIN
    "\u063a": "\ufecd",  # GHAIN
    "\u0641": "\ufed1",  # FEH
    "\u0642": "\ufed5",  # QAF
    "\u0643": "\ufed9",  # KAF
    "\u0644": "\ufedd",  # LAM
    "\u0645": "\ufee1",  # MEEM
    "\u0646": "\ufee5",  # NOON
    "\u0647": "\ufee9",  # HEH
    "\u0648": "\ufeed",  # WAW
    "\u0649": "\ufeef",  # ALEF MAKSURA
    "\u064a": "\ufef1",  # YEH
}

# ---------------------------------------------------------------------------
# Cyrillic substitutions
# ---------------------------------------------------------------------------

# CP866: Belarusian/Ukrainian/Serbian/Macedonian workaround.
# CP866 is a Russian Cyrillic code page.  Other Cyrillic languages have
# letters not in CP866 that were historically approximated with the
# closest Russian letter (or Latin letter in the case of Serbian ј).
# Note: Serbians primarily used CP855 (which has all Serbian letters
# natively) rather than CP866.  These substitutions are plausible
# approximations for the rare case of Serbian text on CP866 systems.
_CP866_SUBSTITUTIONS: dict[str, str] = {
    # Ukrainian/Belarusian
    "\u0456": "\u0438",  # і → и
    "\u0406": "\u0418",  # І → И
    "\u0491": "\u0433",  # ґ → г (reintroduced 1990, missing from Soviet-era CP866)
    "\u0490": "\u0413",  # Ґ → Г
    # Serbian-specific Cyrillic → closest Russian/Latin equivalents
    "\u0452": "\u0434",  # ђ (DJE) → д (DE) — visual base letter
    "\u0402": "\u0414",  # Ђ → Д
    "\u0458": "j",  # ј (JE) → Latin j (identical appearance)
    "\u0408": "J",  # Ј → J
    "\u0459": "\u043b",  # љ (LJE) → л (EL) — visual base letter
    "\u0409": "\u041b",  # Љ → Л
    "\u045a": "\u043d",  # њ (NJE) → н (EN) — visual base letter
    "\u040a": "\u041d",  # Њ → Н
    "\u045b": "\u0442",  # ћ (TSHE) → т (TE) — visual base letter
    "\u040b": "\u0422",  # Ћ → Т
    "\u045f": "\u0446",  # џ (DZHE) → ц (TSE) — visually more similar than д
    "\u040f": "\u0426",  # Џ → Ц
    # Macedonian-specific Cyrillic → closest Russian equivalents
    "\u0453": "\u0433",  # ѓ (GJE) → г (GHE)
    "\u0403": "\u0413",  # Ѓ → Г
    "\u045c": "\u043a",  # ќ (KJE) → к (KA)
    "\u040c": "\u041a",  # Ќ → К
    "\u0455": "\u0437",  # ѕ (DZE) → з (ZE) — closest sound
    "\u0405": "\u0417",  # Ѕ → З
}

# ---------------------------------------------------------------------------
# Farsi substitutions
# ---------------------------------------------------------------------------

# Farsi-specific letters → closest standard Arabic equivalents for
# encodings that only support basic Arabic (CP720, ISO-8859-6, and
# CP1256 for FARSI YEH only).
# These substitutions mirror what Farsi writers historically used when
# limited to Arabic-only code pages.
_FARSI_SUBSTITUTIONS: dict[str, str] = {
    "\u067e": "\u0628",  # پ (PEH) → ب (BEH) — same shape without dots
    "\u0686": "\u062c",  # چ (TCHEH) → ج (JEEM) — same base shape
    "\u0698": "\u0632",  # ژ (JEH) → ز (ZAIN) — same base shape
    "\u06a9": "\u0643",  # ک (KEHEH) → ك (KAF) — standard Arabic KAF
    "\u06af": "\u0643",  # گ (GAF) → ك (KAF) — closest available
    "\u06cc": "\u064a",  # ی (FARSI YEH) → ي (YEH) — standard Arabic YEH
    # Extended Arabic-Indic digits → Western digits
    "\u06f0": "0",
    "\u06f1": "1",
    "\u06f2": "2",
    "\u06f3": "3",
    "\u06f4": "4",
    "\u06f5": "5",
    "\u06f6": "6",
    "\u06f7": "7",
    "\u06f8": "8",
    "\u06f9": "9",
}

# CP1256 Farsi YEH substitution — CP1256 supports most Farsi letters
# natively (PEH, TCHEH, JEH, KEHEH, GAF) but NOT Farsi YEH (U+06CC).
_CP1256_FARSI_SUBSTITUTIONS: dict[str, str] = {
    "\u06cc": "\u064a",  # ی (FARSI YEH) → ي (YEH) — standard Arabic YEH
}

# ---------------------------------------------------------------------------
# Romanian substitutions
# ---------------------------------------------------------------------------

# Romanian: comma-below → cedilla for encodings without modern forms
_ROMANIAN_CEDILLA_SUBSTITUTIONS: dict[str, str] = {
    "\u021b": "\u0163",  # ț → ţ (comma-below → cedilla)
    "\u0219": "\u015f",  # ș → ş (comma-below → cedilla)
    "\u021a": "\u0162",  # Ț → Ţ (uppercase)
    "\u0218": "\u015e",  # Ș → Ş (uppercase)
}

# ---------------------------------------------------------------------------
# Vietnamese decomposition
# ---------------------------------------------------------------------------

# Vietnamese: Windows-1258 uses base letters + combining tone marks rather
# than precomposed characters.
_VIETNAMESE_DECOMPOSITION: dict[str, str] = {
    # Regular vowels + tones
    "à": "a\u0300",
    "á": "a\u0301",
    "ả": "a\u0309",
    "ã": "a\u0303",
    "ạ": "a\u0323",
    "è": "e\u0300",
    "é": "e\u0301",
    "ẻ": "e\u0309",
    "ẽ": "e\u0303",
    "ẹ": "e\u0323",
    "ì": "i\u0300",
    "í": "i\u0301",
    "ỉ": "i\u0309",
    "ĩ": "i\u0303",
    "ị": "i\u0323",
    "ò": "o\u0300",
    "ó": "o\u0301",
    "ỏ": "o\u0309",
    "õ": "o\u0303",
    "ọ": "o\u0323",
    "ù": "u\u0300",
    "ú": "u\u0301",
    "ủ": "u\u0309",
    "ũ": "u\u0303",
    "ụ": "u\u0323",
    "ỳ": "y\u0300",
    "ý": "y\u0301",
    "ỷ": "y\u0309",
    "ỹ": "y\u0303",
    "ỵ": "y\u0323",
    # â (circumflex) + tones
    "ấ": "â\u0301",
    "ầ": "â\u0300",
    "ẩ": "â\u0309",
    "ẫ": "â\u0303",
    "ậ": "â\u0323",
    # ê (circumflex) + tones
    "ế": "ê\u0301",
    "ề": "ê\u0300",
    "ể": "ê\u0309",
    "ễ": "ê\u0303",
    "ệ": "ê\u0323",
    # ô (circumflex) + tones
    "ố": "ô\u0301",
    "ồ": "ô\u0300",
    "ổ": "ô\u0309",
    "ỗ": "ô\u0303",
    "ộ": "ô\u0323",
    # ă (breve) + tones
    "ắ": "ă\u0301",
    "ằ": "ă\u0300",
    "ẳ": "ă\u0309",
    "ẵ": "ă\u0303",
    "ặ": "ă\u0323",
    # ơ (horn) + tones
    "ớ": "ơ\u0301",
    "ờ": "ơ\u0300",
    "ở": "ơ\u0309",
    "ỡ": "ơ\u0303",
    "ợ": "ơ\u0323",
    # ư (horn) + tones
    "ứ": "ư\u0301",
    "ừ": "ư\u0300",
    "ử": "ư\u0309",
    "ữ": "ư\u0303",
    "ự": "ư\u0323",
    # Uppercase variants
    "À": "A\u0300",
    "Á": "A\u0301",
    "Ả": "A\u0309",
    "Ã": "A\u0303",
    "Ạ": "A\u0323",
    "È": "E\u0300",
    "É": "E\u0301",
    "Ẻ": "E\u0309",
    "Ẽ": "E\u0303",
    "Ẹ": "E\u0323",
    "Ì": "I\u0300",
    "Í": "I\u0301",
    "Ỉ": "I\u0309",
    "Ĩ": "I\u0303",
    "Ị": "I\u0323",
    "Ò": "O\u0300",
    "Ó": "O\u0301",
    "Ỏ": "O\u0309",
    "Õ": "O\u0303",
    "Ọ": "O\u0323",
    "Ù": "U\u0300",
    "Ú": "U\u0301",
    "Ủ": "U\u0309",
    "Ũ": "U\u0303",
    "Ụ": "U\u0323",
    "Ỳ": "Y\u0300",
    "Ý": "Y\u0301",
    "Ỷ": "Y\u0309",
    "Ỹ": "Y\u0303",
    "Ỵ": "Y\u0323",
    "Ấ": "Â\u0301",
    "Ầ": "Â\u0300",
    "Ẩ": "Â\u0309",
    "Ẫ": "Â\u0303",
    "Ậ": "Â\u0323",
    "Ế": "Ê\u0301",
    "Ề": "Ê\u0300",
    "Ể": "Ê\u0309",
    "Ễ": "Ê\u0303",
    "Ệ": "Ê\u0323",
    "Ố": "Ô\u0301",
    "Ồ": "Ô\u0300",
    "Ổ": "Ô\u0309",
    "Ỗ": "Ô\u0303",
    "Ộ": "Ô\u0323",
    "Ắ": "Ă\u0301",
    "Ằ": "Ă\u0300",
    "Ẳ": "Ă\u0309",
    "Ẵ": "Ă\u0303",
    "Ặ": "Ă\u0323",
    "Ớ": "Ơ\u0301",
    "Ờ": "Ơ\u0300",
    "Ở": "Ơ\u0309",
    "Ỡ": "Ơ\u0303",
    "Ợ": "Ơ\u0323",
    "Ứ": "Ư\u0301",
    "Ừ": "Ư\u0300",
    "Ử": "Ư\u0309",
    "Ữ": "Ư\u0303",
    "Ự": "Ư\u0323",
}


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def get_substitutions(charset_name: str, langs: list[str]) -> dict[str, str]:
    """Build the character substitution table for a given encoding."""
    subs = dict(_UNIVERSAL_SUBSTITUTIONS)

    upper = charset_name.upper()
    if upper in ("CP720", "CP864", "ISO-8859-6"):
        subs.update(_ARABIC_SUBSTITUTIONS)
    # Farsi-specific letters for encodings that only support basic Arabic
    if "fa" in langs and upper in ("CP720", "ISO-8859-6"):
        subs.update(_FARSI_SUBSTITUTIONS)
    # CP1256 supports most Farsi letters but NOT Farsi YEH
    if "fa" in langs and upper == "CP1256":
        subs.update(_CP1256_FARSI_SUBSTITUTIONS)
    # Arabic presentation forms for legacy encodings that store positional
    # forms instead of standard Arabic letters
    if upper in ("CP1006", "CP864"):
        subs.update(_ARABIC_PRESENTATION_FORM_SUBSTITUTIONS)
    if upper == "CP866":
        subs.update(_CP866_SUBSTITUTIONS)
    # Romanian comma-below → cedilla for all encodings except ISO-8859-16
    if "ro" in langs and upper != "ISO-8859-16":
        subs.update(_ROMANIAN_CEDILLA_SUBSTITUTIONS)

    return subs


def normalize_text(text: str, charset_name: str) -> str:
    """Clean and normalize text for encoding into a legacy charset."""
    # Collapse repeated whitespace
    text = re.sub(r"(\s)\1+", r"\1", text)
    # Vietnamese decomposition for Windows-1258
    if charset_name.upper() in ("WINDOWS-1258", "CP1258"):
        nfc = unicodedata.normalize("NFC", text)
        text = "".join(_VIETNAMESE_DECOMPOSITION.get(c, c) for c in nfc)
    return text


def apply_substitutions(text: str, subs: dict[str, str]) -> str:
    """Apply character substitutions to make text encodable in legacy charsets."""
    for old, new in subs.items():
        if old in text:
            text = text.replace(old, new)
    return text
