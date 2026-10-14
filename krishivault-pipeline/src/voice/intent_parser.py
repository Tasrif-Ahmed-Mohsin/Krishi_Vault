"""
KrishiVault Voice Intent & Entity Parser
========================================
Parses farmer voice inputs (transcripts from Bengali ASR or IVR touchtone/text)
into structured FarmerSituation parameters.

Handles:
- Bengali numerals (০-৯) and English numerals (0-9), and number words (পঞ্চাশ, বিশ হাজার, দেড় লাখ)
- Local agricultural units: মণ (maund ~ 37.32 kg), বস্তা (sack ~ 50 or 85 kg), কেজি (kg)
- Currency terms: টাকা (Tk), হাজার (thousand), লাখ (lakh); northern forms টেকা, নাগবে
- Time deadlines: দিন (days), সপ্তাহ (weeks), কাল/পরশু (tomorrow/day after)
- Storage access: হিমাগার/কোল্ড স্টোরেজ আছে/নাই
- Dadon (advance from a trader), yes/no answers and the keypad-menu choice said in words

parse_all() reads a whole sentence clause by clause, so "২৫ হাজার লাগবে ... ২০ হাজার দাদন" gives a
cash need of 25,000 and dadon of 20,000 rather than mixing them up.
"""

import re
from typing import Dict, Any, Optional
from config.settings import MAUND_TO_KG
from src.voice.bangla_numbers import nfc, to_en_digits, words_to_digits

# Mapping Bengali digits to English digits
BN_TO_EN_DIGITS = {
    '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
    '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'
}

SACK_KG = 50.0  # a standard potato sack (বস্তা) in Bangladesh today

# Northern and colloquial forms heard in Bogura and Rangpur, mapped to the standard word
_DIALECT = [
    ("টেকা", "টাকা"), ("ট্যাকা", "টাকা"),
    ("নাগবে", "লাগবে"), ("নাগবি", "লাগবে"), ("নাগে", "লাগে"),
    ("দিবার চায়", "দিতে চায়"), ("দিবার", "দিতে"),
]

_NEED_WORDS = ["লাগবে", "লাগবো", "লাগব", "লাগে", "দরকার", "প্রয়োজন", "জরুরি", "জরুরী", "need"]
_NEGATION = ["না", "নাই", "নেই", "নাহ", "no"]
_DADON_WORDS = ["দাদন", "দাদোন", "অগ্রিম"]
# A lender named without the word দাদন counts only with "took" words and no "need" word in the clause
_LENDER_WORDS = ["মহাজন", "আড়তদার", "ফড়িয়া"]
_TOOK_WORDS = ["ধার", "নেওয়া", "নিয়েছি", "নিছি", "নিসি"]
_MONEY_WORDS = r"(?:টাকা|টাকার|tk|taka)"
_KG_WORDS = r"(?:কেজি|কেজী|kg|kilo)"
_MAUND_WORDS = r"(?:মণ|মন|maund|mounds?)"


def normalize_bn_numbers(text: str) -> str:
    """Convert Bengali numbers to standard ASCII digits."""
    for bn, en in BN_TO_EN_DIGITS.items():
        text = text.replace(bn, en)
    return text


def prepare(text: str) -> str:
    """One form for parsing: NFC, lower case, standard words for dialect forms, number words as digits."""
    t = nfc(text or "").lower()
    for dialect, standard in _DIALECT:
        t = t.replace(nfc(dialect), nfc(standard))
    return words_to_digits(to_en_digits(t))


def _clauses(prepared: str) -> list[str]:
    return [c.strip() for c in re.split(r"[।\n?!;,]|\.(?!\d)", prepared) if c.strip()]


def _tokens(prepared: str) -> list[str]:
    return [t for t in re.split(r"[\s,।?!;:()\"'\-]+", prepared) if t]


def _has_word(prepared: str, words: list[str]) -> bool:
    """True if any token starts with one of the words (লাগবে matches লাগবে, দাদনের matches দাদন)."""
    words = [nfc(w) for w in words]
    return any(tok.startswith(w) for tok in _tokens(prepared) for w in words)


def _has_negation(prepared: str) -> bool:
    neg = {nfc(w) for w in _NEGATION}
    return any(tok in neg for tok in _tokens(prepared))


def _rate_per_kg(prepared: str) -> Optional[tuple[float, str]]:
    """A price per kg or per maund ('১৮ টাকা কেজি', 'কেজিতে ১৮ টাকা', '৮০০ টাকা মণ', 'মণে ৮০০ টাকা')."""
    num = r"(\d+(?:\.\d+)?)"
    patterns = [
        (rf"{num}\s*{_MONEY_WORDS}?\s*(?:করে\s*)?{_KG_WORDS}", "kg"),
        (rf"{_KG_WORDS}\S*\s*{num}\s*{_MONEY_WORDS}", "kg"),
        (rf"{num}\s*{_MONEY_WORDS}\s*(?:করে\s*)?{_MAUND_WORDS}", "maund"),
        (rf"{_MAUND_WORDS}\S*\s*{num}\s*{_MONEY_WORDS}", "maund"),
    ]
    for pattern, unit in patterns:
        for m in re.finditer(pattern, prepared):
            value = float(m.group(1))
            if unit == "kg" and "টাকা" not in m.group(0) and not re.search(r"\b(?:tk|taka)\b", m.group(0)):
                continue  # "১৫০০ কেজি" is a quantity, not a price
            per_kg = value if unit == "kg" else value / MAUND_TO_KG
            if 3 <= per_kg <= 200:  # a believable potato price per kg
                return round(per_kg, 2), m.group(0)
    return None


def _money_amount(clause: str) -> Optional[tuple[float, str]]:
    """A sum of money in a clause that is not a price per kg or maund."""
    rate = _rate_per_kg(clause)
    rate_text = rate[1] if rate else ""
    cleaned = clause.replace(rate_text, " ") if rate_text else clause
    m = re.search(rf"(\d+(?:\.\d+)?)\s*{_MONEY_WORDS}", cleaned)
    if m:
        return float(m.group(1)), m.group(0)
    m = re.search(r"(\d{3,}(?:\.\d+)?)", cleaned)  # a bare large number ("২৫০০০ লাগবে")
    if m and not re.search(rf"{m.group(1)}\s*(?:{_KG_WORDS}|{_MAUND_WORDS}|বস্তা|দিন|সপ্তাহ|মাস)", cleaned):
        return float(m.group(1)), m.group(0)
    return None


class FarmerIntentParser:
    """Extracts situational entities from spoken farmer transcripts."""

    @staticmethod
    def parse_quantity(text: str) -> Optional[float]:
        """
        Extract total harvest in KG.
        Handles '২০ মণ', '50 maund', '৮০ বস্তা', '1000 kg', 'পঞ্চাশ মণ'.
        """
        found = FarmerIntentParser._quantity(prepare(text), allow_bare='আলু' in text or 'potato' in text.lower())
        return found[0] if found else None

    @staticmethod
    def _quantity(text_norm: str, allow_bare: bool = False) -> Optional[tuple[float, str, str]]:
        """(kg, heard text, unit) or None."""
        maund_match = re.search(rf'(\d+(?:\.\d+)?)\s*{_MAUND_WORDS}', text_norm)
        if maund_match:
            maunds = float(maund_match.group(1))
            return round(maunds * MAUND_TO_KG, 2), maund_match.group(0), "maund"

        # Sacks / বস্তা (a standard potato sack is 50 kg)
        sack_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:বস্তা|ব্যাগ|sacks?|bags?)', text_norm)
        if sack_match:
            sacks = float(sack_match.group(1))
            return round(sacks * SACK_KG, 2), sack_match.group(0), "sack"

        kg_match = re.search(rf'(\d+(?:\.\d+)?)\s*{_KG_WORDS}', text_norm)
        if kg_match and not _rate_per_kg(kg_match.group(0)):
            return float(kg_match.group(1)), kg_match.group(0), "kg"

        # Bare number fallback if context implies quantity
        if allow_bare:
            num_match = re.search(r'\b(\d+(?:\.\d+)?)\b', text_norm)
            if num_match:
                val = float(num_match.group(1))
                # If smaller than 300, usually maunds
                if val <= 300:
                    return round(val * MAUND_TO_KG, 2), num_match.group(0), "maund"
                return val, num_match.group(0), "kg"
        return None

    @staticmethod
    def parse_cash_needed(text: str) -> Optional[float]:
        """
        Extract urgent cash requirements in BDT.
        Handles '১০ হাজার টাকা', '10000 tk', '১ লাখ টাকা', '৫০,০০০', 'বিশ হাজার টেকা নাগবে'.
        """
        text_norm = prepare(text)
        has_need_context = _has_word(text_norm, _NEED_WORDS + ['ধার', 'ঋণ', 'খরচ'])
        found = _money_amount(text_norm)
        if found:
            val = found[0]
            if val >= 500 or has_need_context:
                return val
        return None

    @staticmethod
    def parse_deadline_days(text: str) -> int:
        """
        Extract urgency deadline in days.
        Defaults to 7 days if unmentioned or flexible.
        """
        days = FarmerIntentParser.parse_deadline_days_explicit(text)
        return days if days is not None else 7

    @staticmethod
    def parse_deadline_days_explicit(text: str) -> Optional[int]:
        """The deadline in days if the farmer said one, else None."""
        found = FarmerIntentParser._deadline(prepare(text))
        return found[0] if found else None

    @staticmethod
    def _deadline(text_norm: str) -> Optional[tuple[int, str]]:
        """(days, the words it came from) or None."""
        tokens = _tokens(text_norm)

        def first(pred) -> Optional[str]:
            return next((t for t in tokens if pred(t)), None)

        word = first(lambda t: t.startswith(nfc('আজ'))) or ('today' if 'today' in text_norm else None)
        if word:
            return 1, word
        word = first(lambda t: t in {nfc('কাল'), nfc('কালকে'), nfc('কালকেই'), nfc('আগামীকাল')}) or ('tomorrow' if 'tomorrow' in text_norm else None)
        if word:
            return 1, word
        word = first(lambda t: t.startswith(nfc('পরশু')))
        if word:
            return 2, word

        day_match = re.search(r'(\d+)\s*(?:দিন|days?)\S*', text_norm)
        if day_match:
            return int(day_match.group(1)), day_match.group(0)

        week_match = re.search(r'(\d+)\s*(?:সপ্তাহ|weeks?)\S*', text_norm)
        if week_match:
            return int(week_match.group(1)) * 7, week_match.group(0)
        word = first(lambda t: t.startswith(nfc('সপ্তাহ')))
        if word:
            return 7, word

        month_match = re.search(r'(\d+)\s*(?:মাস|months?)\S*', text_norm)
        if month_match:
            return int(month_match.group(1)) * 30, month_match.group(0)

        return None

    @staticmethod
    def parse_storage_access(text: str) -> bool:
        """Check if farmer has access or booking in a cold storage."""
        text_l = text.lower()
        positive_keywords = ['আছে', 'বুকিং আছে', 'রাখতে পারব', 'সুবিধা আছে', 'yes', 'হিমাগারে দিতে পারব']
        negative_keywords = ['নাই', 'নেই', 'না', 'পারব না', 'সুবিধা নাই', 'no', 'দূরে']

        for neg in negative_keywords:
            if neg in text_l:
                return False

        for pos in positive_keywords:
            if pos in text_l:
                return True

        return False

    @staticmethod
    def parse_offer_price(text: str) -> Optional[float]:
        """Extract current buyer/faria offer per KG (a price per maund is converted)."""
        found = _rate_per_kg(prepare(text))
        return found[0] if found else None

    @staticmethod
    def parse_yes_no(text: str) -> Optional[bool]:
        """True for হ্যাঁ / ঠিক আছে, False for না / ভুল, None if neither was said."""
        t = prepare(text)
        tokens = set(_tokens(t))
        negative = {nfc(w) for w in ["না", "নাহ", "ভুল", "নেই", "নাই", "no", "wrong"]}
        positive = {nfc(w) for w in ["হ্যাঁ", "হ্যা", "হা", "হাঁ", "জি", "জ্বি", "ঠিক", "হুম", "আছে", "yes", "ok", "okay", "correct"]}
        if tokens & negative:
            return False
        if tokens & positive:
            return True
        return None

    @staticmethod
    def parse_menu_choice(text: str) -> Optional[str]:
        """The keypad-menu choice said in words: 'sell', 'fertilizer', 'seeds', 'officer' or None."""
        t = prepare(text)
        tokens = _tokens(t)

        def starts(words: list[str]) -> bool:
            return any(tok.startswith(nfc(w)) for tok in tokens for w in words)

        def exact(words: list[str]) -> bool:
            ws = {nfc(w) for w in words}
            return any(tok in ws for tok in tokens)

        if starts(["কর্মকর্তা", "অফিসার", "officer"]):
            return "officer"
        if exact(["সার", "সারের", "সারে", "বিষ", "ওষুধ", "ঔষধ"]) or starts(["কীটনাশক", "ইউরিয়া", "পটাশ", "টিএসপি", "fertili", "pestic"]):
            return "fertilizer"
        if starts(["বীজ", "যন্ত্র", "ট্রাক্টর", "টিলার", "হারভেস্টার", "মেশিন", "পাম্প", "seed", "machin", "tractor"]):
            return "seeds"
        if starts(["বেচ", "বিক্রি", "বিক্রয়", "দাম", "দর", "আলু", "হিমাগার", "কোল্ড", "sell", "price", "potato"]):
            return "sell"
        return None

    @staticmethod
    def parse_all(text: str) -> Dict[str, Dict[str, Any]]:
        """
        Every value the farmer said, clause by clause:
          quantity_kg, cash_needed_tk, deadline_days, offer_per_kg, dadon_tk
        Each found value is {"value": number, "heard": the words it came from}.
        A clear "no" ("টাকা লাগবে না", "দাদন নেই") gives 0.
        """
        prepared = prepare(text)
        found: Dict[str, Dict[str, Any]] = {}

        qty = FarmerIntentParser._quantity(prepared)
        if qty:
            found["quantity_kg"] = {"value": qty[0], "heard": qty[1], "unit": qty[2]}

        rate = _rate_per_kg(prepared)
        if rate:
            per_maund = re.search(_MAUND_WORDS, rate[1]) is not None
            found["offer_per_kg"] = {"value": rate[0], "heard": rate[1],
                                     "unit": "taka_per_maund" if per_maund else "taka_per_kg"}

        for clause in _clauses(prepared):
            is_need = _has_word(clause, _NEED_WORDS)
            is_dadon = _has_word(clause, _DADON_WORDS) or (
                _has_word(clause, _LENDER_WORDS) and _has_word(clause, _TOOK_WORDS) and not is_need
            )
            amount = _money_amount(clause)
            if is_dadon and "dadon_tk" not in found:
                if amount:
                    found["dadon_tk"] = {"value": amount[0], "heard": amount[1]}
                elif _has_negation(clause):
                    found["dadon_tk"] = {"value": 0.0, "heard": clause}
            elif is_need and "cash_needed_tk" not in found:
                if amount:
                    found["cash_needed_tk"] = {"value": amount[0], "heard": amount[1]}
                elif _has_negation(clause):
                    found["cash_needed_tk"] = {"value": 0.0, "heard": clause}
            if is_need or "cash_needed_tk" in found:
                deadline = FarmerIntentParser._deadline(clause)
                if deadline and "deadline_days" not in found:
                    found["deadline_days"] = {"value": float(deadline[0]), "heard": deadline[1]}

        if "deadline_days" not in found:
            deadline = FarmerIntentParser._deadline(prepared)
            if deadline and re.search(r"(?:দিন|সপ্তাহ|মাস|days?|weeks?)", prepared):
                found["deadline_days"] = {"value": float(deadline[0]), "heard": deadline[1]}
        return found
