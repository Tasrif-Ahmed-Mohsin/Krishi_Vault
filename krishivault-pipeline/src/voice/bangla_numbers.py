"""
Bangla numbers: reading them from speech and writing them for the farmer
=======================================================================
Speech-to-text gives numbers as digits ("৫০ মণ") or as words ("পঞ্চাশ মণ", "বিশ হাজার টাকা",
"দেড় লাখ"). Every Bangla number from 1 to 99 has its own word, so they are listed in full.

- words_to_digits(text): replaces number words and digit-plus-multiplier runs with plain digits
  ("বিশ হাজার" -> "20000", "২০ হাজার" -> "20000", "দেড় লাখ" -> "150000").
- extract_numbers(text): every number in a text, in one canonical form, for the number lock.
- fmt_taka / fmt_num: write engine numbers in Bangla digits with Bangladeshi grouping (১,২০,০০০).
"""

import re
import unicodedata
from typing import Optional

BN_DIGITS = "০১২৩৪৫৬৭৮৯"
_TO_EN = str.maketrans(BN_DIGITS, "0123456789")
_TO_BN = str.maketrans("0123456789", BN_DIGITS)


def nfc(text: str) -> str:
    """One Unicode form for Bangla text, so 'য়' typed two ways compares equal."""
    return unicodedata.normalize("NFC", text or "")


def to_en_digits(text: str) -> str:
    return (text or "").translate(_TO_EN)


def to_bn_digits(text: str) -> str:
    return (text or "").translate(_TO_BN)


# ------------------------------------------------------------------ number words
_WORDS_RAW = {
    0: "শূন্য শুন্য",
    1: "এক",
    2: "দুই দু",
    3: "তিন",
    4: "চার",
    5: "পাঁচ পাচ",
    6: "ছয় ছয় ছ",
    7: "সাত",
    8: "আট",
    9: "নয় নয়",
    10: "দশ",
    11: "এগারো এগার",
    12: "বারো বার",
    13: "তেরো তের",
    14: "চৌদ্দ চোদ্দ",
    15: "পনেরো পনের",
    16: "ষোলো ষোল",
    17: "সতেরো সতের",
    18: "আঠারো আঠার",
    19: "উনিশ ঊনিশ",
    20: "বিশ কুড়ি",
    21: "একুশ",
    22: "বাইশ",
    23: "তেইশ",
    24: "চব্বিশ",
    25: "পঁচিশ পচিশ",
    26: "ছাব্বিশ",
    27: "সাতাশ",
    28: "আটাশ",
    29: "ঊনত্রিশ উনত্রিশ",
    30: "ত্রিশ তিরিশ",
    31: "একত্রিশ",
    32: "বত্রিশ",
    33: "তেত্রিশ",
    34: "চৌত্রিশ",
    35: "পঁয়ত্রিশ",
    36: "ছত্রিশ",
    37: "সাঁইত্রিশ",
    38: "আটত্রিশ",
    39: "ঊনচল্লিশ উনচল্লিশ",
    40: "চল্লিশ",
    41: "একচল্লিশ",
    42: "বিয়াল্লিশ",
    43: "তেতাল্লিশ",
    44: "চুয়াল্লিশ",
    45: "পঁয়তাল্লিশ",
    46: "ছেচল্লিশ",
    47: "সাতচল্লিশ",
    48: "আটচল্লিশ",
    49: "ঊনপঞ্চাশ উনপঞ্চাশ",
    50: "পঞ্চাশ",
    51: "একান্ন",
    52: "বাহান্ন",
    53: "তিপ্পান্ন",
    54: "চুয়ান্ন",
    55: "পঞ্চান্ন",
    56: "ছাপ্পান্ন",
    57: "সাতান্ন",
    58: "আটান্ন",
    59: "ঊনষাট উনষাট",
    60: "ষাট",
    61: "একষট্টি",
    62: "বাষট্টি",
    63: "তেষট্টি",
    64: "চৌষট্টি",
    65: "পঁয়ষট্টি",
    66: "ছেষট্টি",
    67: "সাতষট্টি",
    68: "আটষট্টি",
    69: "ঊনসত্তর উনসত্তর",
    70: "সত্তর",
    71: "একাত্তর",
    72: "বাহাত্তর",
    73: "তিয়াত্তর",
    74: "চুয়াত্তর",
    75: "পঁচাত্তর",
    76: "ছিয়াত্তর",
    77: "সাতাত্তর",
    78: "আটাত্তর",
    79: "ঊনআশি উনআশি",
    80: "আশি",
    81: "একাশি",
    82: "বিরাশি",
    83: "তিরাশি",
    84: "চুরাশি",
    85: "পঁচাশি",
    86: "ছিয়াশি",
    87: "সাতাশি",
    88: "অষ্টাশি",
    89: "ঊননব্বই উননব্বই",
    90: "নব্বই",
    91: "একানব্বই",
    92: "বিরানব্বই",
    93: "তিরানব্বই",
    94: "চুরানব্বই",
    95: "পঁচানব্বই",
    96: "ছিয়ানব্বই",
    97: "সাতানব্বই",
    98: "আটানব্বই",
    99: "নিরানব্বই",
}

NUMBER_WORDS: dict[str, float] = {}
for _value, _forms in _WORDS_RAW.items():
    for _form in _forms.split():
        NUMBER_WORDS[nfc(_form)] = float(_value)

# Half steps: দেড় 1.5, আড়াই 2.5, আধা 0.5; সাড়ে adds a half to the next number (সাড়ে তিন = 3.5)
FRACTION_WORDS = {nfc("দেড়"): 1.5, nfc("আড়াই"): 2.5, nfc("আধা"): 0.5}
HALF_MORE = nfc("সাড়ে")

MULTIPLIERS = {
    nfc("শ"): 100, nfc("শো"): 100, nfc("শত"): 100,
    nfc("হাজার"): 1000,
    nfc("লাখ"): 100_000, nfc("লক্ষ"): 100_000,
    nfc("কোটি"): 10_000_000,
}
_HUNDRED_SUFFIXES = [nfc(s) for s in ("শত", "শো", "শ")]

# Classifiers spoken after a number: পঞ্চাশটা, দুইটি, দুটো, দশজন
_CLASSIFIERS = [nfc(s) for s in ("খানা", "টা", "টি", "টো", "জন")]

# Words that are also ordinary words (এক = "a", নয় = "is not", বার = "times"): numbers only before a unit
_AMBIGUOUS = {nfc("এক"), nfc("নয়"), nfc("বার")}
_UNIT_STARTS = [nfc(s) for s in (
    "মণ", "মন", "বস্তা", "কেজি", "কেজী", "টাকা", "টেকা", "দিন", "সপ্তাহ", "মাস", "বিঘা", "শতক",
    "হাজার", "লাখ", "লক্ষ", "কোটি", "শো", "শত", "টন", "জন",
)]

_NUMBER_RE = re.compile(r"^\d+(?:\.\d+)?$")
_TOKEN_SPLIT = re.compile(r"(\s+|[,।?!;:()\"'/\-–—]+)")


def _word_value(token: str) -> Optional[tuple[str, float]]:
    """('number' | 'fraction' | 'hundreds' | 'multiplier' | 'half', value) for one token, or None."""
    if _NUMBER_RE.match(token):
        return "number", float(token)
    if token == HALF_MORE:
        return "half", 0.5
    if token in MULTIPLIERS:
        return "multiplier", float(MULTIPLIERS[token])
    if token in NUMBER_WORDS:
        return "number", NUMBER_WORDS[token]
    if token in FRACTION_WORDS:
        return "fraction", FRACTION_WORDS[token]
    # পাঁচশো, আড়াইশো, একশ: a number word with "hundred" joined on
    for suffix in _HUNDRED_SUFFIXES:
        if token.endswith(suffix) and len(token) > len(suffix):
            stem = token[: -len(suffix)]
            base = NUMBER_WORDS.get(stem, FRACTION_WORDS.get(stem))
            if base is not None:
                return "hundreds", base * 100
    for clf in _CLASSIFIERS:
        if token.endswith(clf) and len(token) > len(clf):
            stem = token[: -len(clf)]
            if stem in NUMBER_WORDS:
                return "number", NUMBER_WORDS[stem]
            if _NUMBER_RE.match(stem):
                return "number", float(stem)
    return None


def _is_ambiguous(token: str) -> bool:
    if token in _AMBIGUOUS:
        return True
    return any(token.endswith(c) and token[: -len(c)] in _AMBIGUOUS for c in _CLASSIFIERS)


def canonical(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def words_to_digits(text: str) -> str:
    """
    Replace Bangla number words, and digits followed by হাজার / লাখ, with plain ASCII digits.
    Bangla digits and digit-group commas are normalised first ("২০,০০০" -> "20000").
    """
    text = to_en_digits(nfc(text))
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    parts = _TOKEN_SPLIT.split(text)
    # parts alternate: token, separator, token, separator, ...
    tokens = [(p, bool(_TOKEN_SPLIT.fullmatch(p)) or p == "") for p in parts]

    def next_word(i: int) -> str:
        for t, is_sep in tokens[i + 1:]:
            if not is_sep and t:
                return t
        return ""

    out: list[str] = []
    i = 0
    n = len(tokens)
    while i < n:
        tok, is_sep = tokens[i]
        kind = None if is_sep else _word_value(tok)
        if kind and _is_ambiguous(tok) and not any(next_word(i).startswith(u) for u in _UNIT_STARTS):
            kind = None
        if not kind or kind[0] == "multiplier":
            out.append(tok)
            i += 1
            continue

        # Collect a run of number tokens separated only by spaces
        total = 0.0
        current: Optional[float] = None
        half = False
        has_value = False
        prev = None
        j = i
        last_used = i
        while j < n:
            t, sep = tokens[j]
            if sep:
                if t.strip() == "":
                    j += 1
                    continue
                break
            k = _word_value(t)
            if k and _is_ambiguous(t) and not any(next_word(j).startswith(u) for u in _UNIT_STARTS):
                k = None
            if not k:
                break
            kind_j, val = k
            if kind_j in ("number", "fraction") and prev in ("number", "fraction"):
                break  # two plain numbers in a row are two numbers ("বিশ পঁচিশ" is a range)
            if kind_j == "multiplier":
                base = current if current is not None else 1.0
                if val == 100:
                    current = base * 100
                else:
                    total += base * val
                    current = None
            elif kind_j == "half":
                half = True
            elif kind_j == "hundreds":
                current = (current or 0.0) + val + (50.0 if half else 0.0)
                half = False
                has_value = True
            else:
                current = (current or 0.0) + val + (0.5 if half else 0.0)
                half = False
                has_value = True
            prev = "multiplier" if kind_j in ("multiplier", "hundreds") else kind_j
            last_used = j
            j += 1
        if not has_value:  # a lone সাড়ে with no number after it
            out.append(tok)
            i += 1
            continue
        value = total + (current or 0.0)
        out.append(canonical(value))
        # keep the separators that followed the last token of the run
        i = last_used + 1
    return "".join(out)


_NUM_IN_TEXT = re.compile(r"\d+(?:\.\d+)?")


def extract_numbers(text: str) -> list[str]:
    """Every number in a text (digits in either script, or words), canonical: '80200', '18.5'."""
    return [canonical(float(m)) for m in _NUM_IN_TEXT.findall(words_to_digits(text))]


# ------------------------------------------------------------------ writing numbers for the farmer
def group_bd(n: int) -> str:
    """Bangladeshi grouping: 1,20,000 and 80,200."""
    s = str(abs(int(n)))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        s = f"{head},{tail}"
    return ("-" if n < 0 else "") + s


def round_taka(x: float) -> int:
    """Round money for speech: to the nearest 100 taka from ৳1,000 up, else to the nearest 10."""
    step = 100 if abs(x) >= 1000 else 10
    return int(round(x / step) * step)


def fmt_taka(x: float, rounded: bool = True) -> str:
    """'৮০,২০০' (Bangla digits, no ৳ sign; the template adds 'টাকা')."""
    value = round_taka(x) if rounded else int(round(x))
    return to_bn_digits(group_bd(value))


def fmt_num(x: float, decimals: int = 1) -> str:
    """'১৮.৫', '৫০' (trailing .0 dropped)."""
    s = f"{x:.{decimals}f}".rstrip("0").rstrip(".") if decimals else str(int(round(x)))
    return to_bn_digits(s)
