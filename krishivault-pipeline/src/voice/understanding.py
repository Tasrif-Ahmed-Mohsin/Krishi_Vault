"""
Understanding what the farmer said
==================================
1. KrishiVault's Bangla parser reads numbers and units (মণ, বস্তা, টাকা, দিন, দাদন).
2. If a number was said that the parser could not place, Gemini is asked to fill fixed fields.
   Each number Gemini returns must be one the farmer actually said (the parser checks it); a number
   that was not said is rejected and shown as rejected.
3. A bare answer to a question ("পঞ্চাশ" after "কত মণ?") fills the slot that was asked about.
"""

from typing import Any, Optional

from config.settings import MAUND_TO_KG
from src.voice.bangla_numbers import extract_numbers, canonical
from src.voice.gemini import GeminiClient
from src.voice.intent_parser import FarmerIntentParser, SACK_KG, prepare

SLOTS = ["quantity_kg", "cash_needed_tk", "deadline_days", "offer_per_kg", "dadon_tk"]

# Believable ranges; anything outside is treated as misheard
LIMITS = {
    "quantity_kg": (1 * MAUND_TO_KG, 5000 * MAUND_TO_KG),
    "cash_needed_tk": (0, 1_000_000),
    "deadline_days": (1, 180),
    "offer_per_kg": (0, 200),
    "dadon_tk": (0, 1_000_000),
}

# Answers that mean "none" or "don't know" for the optional money questions
_NONE_WORDS = ["না", "নাই", "নেই", "জানি না", "জানিনা", "কিছু না", "লাগবে না", "দরকার নাই", "দরকার নেই"]


def in_limits(slot: str, value: float) -> bool:
    lo, hi = LIMITS[slot]
    return lo <= value <= hi


def bare_answer(slot: str, number: float) -> dict:
    """A number said or pressed in answer to a question about one slot, in that slot's usual unit."""
    if slot == "quantity_kg":
        return {"value": round(number * MAUND_TO_KG, 2), "said": number, "unit": "maund"}
    if slot == "offer_per_kg" and number > 200:  # a price per maund ("৮০০")
        return {"value": round(number / MAUND_TO_KG, 2), "said": number, "unit": "taka_per_maund"}
    return {"value": float(number), "said": number}


GEMINI_PROMPT = """You read what a Bangladeshi potato farmer said on a phone call. It is Bangla, maybe in a
northern dialect, and may contain speech-recognition mistakes.
{asked}
Return only a JSON object with exactly these fields (null when the farmer did not say it):
{{"intent": "sell" | "fertilizer" | "seeds" | "officer" | "yes" | "no" | null,
 "quantity": {{"number": <number>, "unit": "maund" | "sack" | "kg"}} | null,
 "cash_needed_taka": <number> | null,
 "deadline_days": <number> | null,
 "offer_price": {{"number": <number>, "per": "kg" | "maund"}} | null,
 "dadon_taka": <number> | null}}
Rules: write each number in digits exactly as the farmer said it ("বিশ হাজার" is 20000).
Never calculate, convert or guess a number. "dadon" is an advance taken from a trader.

The farmer said: \"\"\"{text}\"\"\""""


def _gemini_values(data: dict) -> dict[str, dict]:
    """Gemini's fixed fields as {slot: {"number", "value", "unit"}} before checking."""
    out: dict[str, dict] = {}
    q = data.get("quantity")
    if isinstance(q, dict) and isinstance(q.get("number"), (int, float)):
        unit = q.get("unit") or "maund"
        factor = {"maund": MAUND_TO_KG, "sack": SACK_KG, "kg": 1.0}.get(unit, MAUND_TO_KG)
        out["quantity_kg"] = {"number": q["number"], "value": round(q["number"] * factor, 2), "unit": unit}
    for key, slot in (("cash_needed_taka", "cash_needed_tk"), ("deadline_days", "deadline_days"), ("dadon_taka", "dadon_tk")):
        v = data.get(key)
        if isinstance(v, (int, float)):
            out[slot] = {"number": v, "value": float(v)}
    o = data.get("offer_price")
    if isinstance(o, dict) and isinstance(o.get("number"), (int, float)):
        per = o.get("per") or "kg"
        value = o["number"] / MAUND_TO_KG if per == "maund" else o["number"]
        out["offer_per_kg"] = {"number": o["number"], "value": round(value, 2), "unit": f"taka_per_{per}"}
    return out


def understand(text: str, expecting: Optional[str] = None, asked_text: str = "",
               gemini: Optional[GeminiClient] = None) -> dict[str, Any]:
    """
    {
      "values":   {slot: {"value", "heard", "source": "parser" | "gemini"}},
      "rejected": [{"slot", "number", "reason"}],
      "menu":     "sell" | "fertilizer" | "seeds" | "officer" | None,
      "yes_no":   True | False | None,
      "gemini":   "not_set_up" | "not_needed" | "used" | "no_answer",
    }
    """
    values: dict[str, dict] = {}
    rejected: list[dict] = []

    for slot, found in FarmerIntentParser.parse_all(text).items():
        if in_limits(slot, found["value"]):
            values[slot] = {**found, "source": "parser"}
        else:
            rejected.append({"slot": slot, "number": found["value"], "reason": "out_of_range"})

    said_numbers = extract_numbers(text)
    prepared = prepare(text)

    # A bare answer to the question that was asked
    if expecting in SLOTS and expecting not in values:
        if len(said_numbers) == 1:
            ans = bare_answer(expecting, float(said_numbers[0]))
            if in_limits(expecting, ans["value"]):
                values[expecting] = {**ans, "heard": said_numbers[0], "source": "parser"}
        elif not said_numbers and expecting in ("cash_needed_tk", "offer_per_kg", "dadon_tk"):
            if any(w in prepared for w in _NONE_WORDS):
                values[expecting] = {"value": 0.0, "heard": text.strip(), "source": "parser"}

    menu = FarmerIntentParser.parse_menu_choice(text)
    yes_no = FarmerIntentParser.parse_yes_no(text)

    # Numbers the parser did not place
    used = set()
    for v in values.values():
        used.update(extract_numbers(str(v.get("heard", ""))))
    unplaced = [n for n in said_numbers if n not in used]

    gemini_status = "not_set_up"
    if gemini is not None and gemini.available:
        needs_help = bool(unplaced) or (not values and menu is None and yes_no is None)
        if not needs_help:
            gemini_status = "not_needed"
        else:
            asked = f'KrishiVault had just asked: "{asked_text}"' if asked_text else ""
            data = gemini.json(GEMINI_PROMPT.format(asked=asked, text=text))
            if data is None:
                gemini_status = "no_answer"
            else:
                gemini_status = "used"
                said = set(said_numbers)
                for slot, g in _gemini_values(data).items():
                    if slot in values:
                        continue  # the parser's reading wins
                    if canonical(float(g["number"])) not in said:
                        rejected.append({"slot": slot, "number": g["number"], "reason": "not_said"})
                        continue
                    if not in_limits(slot, g["value"]):
                        rejected.append({"slot": slot, "number": g["number"], "reason": "out_of_range"})
                        continue
                    values[slot] = {"value": g["value"], "said": g["number"], "unit": g.get("unit"),
                                    "heard": str(g["number"]), "source": "gemini"}
                intent = data.get("intent")
                if menu is None and intent in ("sell", "fertilizer", "seeds", "officer"):
                    menu = intent
                if yes_no is None and intent in ("yes", "no"):
                    yes_no = intent == "yes"

    return {"values": values, "rejected": rejected, "menu": menu, "yes_no": yes_no, "gemini": gemini_status}
