"""
The farmer's call, step by step
===============================
One state machine for a farmer's call: the call preview on the web today
(`/call`), a real phone line later. Each turn takes the call state and what
the farmer did (spoke, or pressed keys) and returns the new state and what
KrishiVault says next. The state is a plain dict that the screen keeps and
sends back each turn.

  menu ── 1 / "রাখব না বেচব" ── questions ── read-back ── store-or-sell advice ── 2: cold-storage request
       ── 2 / "দাম কেমন হবে" ── today's price ── read-back ── price outlook ──────── 2: go to the advice
       ── 3 / "একসাথে রাখব"  ── sacks ── read-back ── group storage ─────────────── 2: join the group
       ── 4 / "লোন"           ── sacks, price ── read-back ── loan estimate ──────── 2: apply to the bank
       ── 9 ── a KrishiVault helper calls back (end)

Rules (docs/PLAN_DETAILS.md): the keypad always works; every number is read
back for a keypad "yes"; two misunderstandings lead to the helper; every
answer ends with "১ = আবার শুনুন, ০ = মূল মেনু, ৯ = সহকারী". Every number the
farmer hears comes from the engine (number lock).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import re
from typing import Optional

from src import demo_data, events
from src.engine import farmer_signals, financing, group_storage, receipts
from src.engine.facts import CURING_WEEKS, MAUND_KG, SACK_KG, MONTHS_BN, StorageTerms
from src.engine.storage_plan import FarmerLot, StoragePlanner, months_left
from src.models.price_outlook import SEASON_CURVE, outlook as price_outlook
from src.voice.bangla_numbers import fmt_num, fmt_taka, nfc, to_bn_digits
from src.voice.gemini import GeminiClient
from src.voice.intent_parser import prepare
from src.voice.number_lock import narrate
from src.voice.understanding import bare_answer, in_limits, understand

# ------------------------------------------------------------------ what KrishiVault says
GREETING = "আসসালামু আলাইকুম, কৃষিভল্টে স্বাগতম। আপনার কথা শুধু আপনাকে পরামর্শ দিতে ব্যবহার হবে।"
MENU = (
    "আলু রাখবেন না বেচবেন, পরামর্শের জন্য ১ চাপুন। দামের পূর্বাভাস শুনতে ২। "
    "একসাথে হিমাগারে রেখে খরচ কমাতে ৩। হিমাগারের বস্তা জামানতে ব্যাংক ঋণের খোঁজে ৪। "
    "আমাদের সহকারী আপনাকে ফোন করবেন, এর জন্য ৯। অথবা আপনার কথা বলুন।"
)
MENU_KEYS = ["1", "2", "3", "4", "9"]
MENU_CHOICES = {"1": "advice", "2": "outlook", "3": "group", "4": "loan", "9": "helper"}

QUESTIONS = {
    "quantity_kg": "আপনার কত মণ আলু? মণের সংখ্যা চেপে হ্যাশ চাপুন, অথবা বলুন। বস্তায় বললে বলুন কত বস্তা।",
    "quantity_sacks": "কত বস্তা আলু? বস্তার সংখ্যা চেপে হ্যাশ চাপুন, অথবা বলুন।",
    "offer_per_kg": "আজ কেজিতে কত টাকা দাম পাচ্ছেন? টাকার অঙ্ক চেপে হ্যাশ চাপুন। না জানলে ০ চেপে হ্যাশ।",
    "in_storage": "আলু কি এখন হিমাগারে আছে? থাকলে ১, না থাকলে ২ চাপুন।",
    "cash_needed_tk": "সামনে কত টাকা দরকার? টাকার অঙ্ক চেপে হ্যাশ চাপুন। দরকার না থাকলে ০ চেপে হ্যাশ।",
    "deadline_days": "কত দিনের মধ্যে টাকাটা লাগবে? দিনের সংখ্যা চেপে হ্যাশ চাপুন।",
}
CONFIRM_KEYS = "ঠিক হলে ১, ভুল হলে ২ চাপুন।"
NOT_UNDERSTOOD = "দুঃখিত, বুঝতে পারিনি।"
HELP = "দুঃখিত, আমি বুঝতে পারছি না। আবার চেষ্টা করতে ১ চাপুন। আমাদের সহকারী আপনাকে ফোন করবেন, এর জন্য ৯ চাপুন।"
CLOSING = "আবার শুনতে ১, মূল মেনুতে ০, সহকারীর ফোনের জন্য ৯ চাপুন।"
# Asked once after the store-or-sell answer: counting is opt-in, so the greeting's promise stays true
CONSENT_ASK = "নাম ও নম্বর ছাড়া আপনার উত্তর জেলার হিসাবে গুনতে দিলে ৮ চাপুন।"
COUNTED = "ধন্যবাদ। নাম ও নম্বর ছাড়া আপনার উত্তর জেলার হিসাবে গোনা হলো।"
HELPER = "ঠিক আছে। কৃষিভল্টের একজন সহকারী শিগগির আপনাকে ফোন করবেন। কৃষিভল্টে ফোন করার জন্য ধন্যবাদ।"
ENDED = "কলটি শেষ হয়েছে। ধন্যবাদ।"

REWORD_PROMPT = """Reword this phone advice for a potato farmer in Bogura, Bangladesh, in simple, warm,
spoken Bangla. The call is already under way: no greeting, no name, no চাচা or ভাই.
Rules:
- Keep every number exactly as written, in Bangla digits, and keep what each number counts (sacks,
  taka per kg, taka in hand after costs, a month, a chance out of 10).
- Keep the meaning exactly: the same action, the same month; "খরচ বাদে" (after costs) stays after costs;
  storing means the cold storage (হিমাগার), not the home.
- Do not add, drop, round or calculate any number; do not add reasons, advice, promises, loans or certainty.
- Keep it short: no more sentences than the advice has.
Return only the reworded Bangla text.

Advice: \"\"\"{text}\"\"\""""

# Which questions each part of the menu needs, in order
FLOW_SLOTS = {
    "advice": ["quantity_kg", "offer_per_kg", "in_storage", "cash_needed_tk", "deadline_days"],
    "outlook": ["offer_per_kg"],
    "group": ["quantity_kg"],
    "loan": ["quantity_kg", "offer_per_kg"],
}
SACK_FLOWS = ("group", "loan")      # these ask for sacks, not maunds
HARVEST_MONTHS = (2, 3, 4)          # at harvest the potatoes are not in cold storage yet
DEFAULT_SEASON = (3, 2027)          # demo default: the next harvest, March 2027

SLOT_LABELS = {
    "quantity_kg": ("আলুর পরিমাণ", "Potato"),
    "offer_per_kg": ("আজকের দাম", "Price today"),
    "in_storage": ("হিমাগারে আছে?", "Already in cold storage?"),
    "cash_needed_tk": ("টাকার দরকার", "Cash needed"),
    "deadline_days": ("কত দিনে", "Within"),
}
FLOW_NAMES = {"advice": ("রাখব না বেচব", "Store or sell"), "outlook": ("দামের পূর্বাভাস", "Price outlook"),
              "group": ("একসাথে হিমাগার", "Group storage"), "loan": ("বস্তা জামানতে ঋণ", "Loan against sacks")}


def new_state(district: str = "Bogura", month: Optional[int] = None, year: Optional[int] = None,
              phone: Optional[str] = None) -> dict:
    return {
        "v": 2, "step": "menu", "flow": None, "asking": None, "slots": {}, "fails": 0,
        "district": district or "Bogura", "month": month or DEFAULT_SEASON[0], "year": year or DEFAULT_SEASON[1],
        "phone": phone, "last_say": "", "result_say": "", "result_body": "", "done_say": "",
        "help_return": None, "result": None, "action": None, "sms": None, "sms_sig": None, "booking_ref": None,
    }


def _clean(state: dict) -> dict:
    """The state comes back from the browser: keep its settings within sensible bounds."""
    state = dict(state)
    state["slots"] = {k: v for k, v in dict(state.get("slots") or {}).items()
                      if k in SLOT_LABELS and isinstance(v, dict) and isinstance(v.get("value"), (int, float))}
    try:
        month, year = int(state.get("month")), int(state.get("year"))
    except (TypeError, ValueError):
        month, year = DEFAULT_SEASON
    state["month"] = month if 1 <= month <= 12 else DEFAULT_SEASON[0]
    state["year"] = year if 2013 <= year <= 2035 else DEFAULT_SEASON[1]
    state["district"] = str(state.get("district") or "Bogura")[:40]
    if state.get("flow") not in FLOW_SLOTS:
        state["flow"] = None
    if state.get("step") not in ("menu", "ask", "confirm", "result", "done", "help", "ended"):
        state["step"] = "menu"
    if state["step"] in ("ask", "confirm", "result") and not state["flow"]:
        state["step"] = "menu"
    if state["step"] == "ask" and state.get("asking") not in SLOT_LABELS:
        state["step"] = "menu"
    for key in ("result_say", "done_say", "last_say"):
        state[key] = str(state.get(key) or "")
    return state


def _value(slots: dict, slot: str, default: float = 0.0) -> float:
    return float(slots.get(slot, {}).get("value", default))


def _needed(state: dict) -> list[str]:
    slots, flow = state["slots"], state["flow"]
    need = []
    for slot in FLOW_SLOTS.get(flow, []):
        if slot == "deadline_days" and "cash_needed_tk" in slots and _value(slots, "cash_needed_tk") == 0:
            continue
        if slot == "in_storage" and state["month"] in HARVEST_MONTHS:
            continue
        need.append(slot)
    return need


def _missing(state: dict) -> Optional[str]:
    return next((s for s in _needed(state) if s not in state["slots"]), None)


def _said_again(text: str) -> bool:
    return any(tok.startswith(nfc("আবার")) for tok in prepare(text).split())


def demo_price(month: int) -> float:
    """Used only when the farmer does not know today's price: a demo price moved by the usual season."""
    return round(16.0 * SEASON_CURVE[month] / SEASON_CURVE[3], 1)


def _sacks(kg: float) -> int:
    return max(1, math.ceil(kg / SACK_KG - 1e-9))


# ------------------------------------------------------------------ reading values back
def quantity_phrase(slot: dict) -> str:
    kg = slot["value"]
    unit = slot.get("unit") or "maund"
    if unit == "sack":
        return f"{fmt_num(kg / SACK_KG, 0)} বস্তা আলু, মানে প্রায় {fmt_num(kg / MAUND_KG)} মণ"
    if unit == "kg":
        return f"{fmt_num(kg, 0)} কেজি আলু, মানে প্রায় {fmt_num(kg / SACK_KG, 0)} বস্তা"
    return f"{fmt_num(kg / MAUND_KG)} মণ আলু, মানে প্রায় {fmt_num(_sacks(kg), 0)} বস্তা"


def readback(state: dict) -> str:
    slots = state["slots"]
    parts = []
    for slot in _needed(state):
        if slot == "quantity_kg":
            parts.append(quantity_phrase(slots["quantity_kg"]))
        elif slot == "offer_per_kg":
            offer = slots["offer_per_kg"]
            if offer["value"] > 0 and offer.get("unit") == "taka_per_maund":
                parts.append(f"আজকের দাম মণে {fmt_num(offer['value'] * MAUND_KG, 0)} টাকা, মানে কেজিতে {fmt_num(offer['value'])} টাকা")
            elif offer["value"] > 0:
                parts.append(f"আজকের দাম কেজিতে {fmt_num(offer['value'])} টাকা")
            else:
                parts.append("আজকের দাম জানা নেই")
        elif slot == "in_storage":
            parts.append("আলু এখন হিমাগারে আছে" if _value(slots, "in_storage") else "আলু এখনো হিমাগারে রাখা হয়নি")
        elif slot == "cash_needed_tk":
            cash = _value(slots, "cash_needed_tk")
            if cash > 0:
                days = _value(slots, "deadline_days")
                parts.append(f"{fmt_num(days, 0)} দিনের মধ্যে {fmt_taka(cash, rounded=False)} টাকা দরকার"
                             if days else f"{fmt_taka(cash, rounded=False)} টাকা দরকার")
            else:
                parts.append("এখন টাকার জরুরি দরকার নেই")
    return "আপনি বললেন: " + "। ".join(parts) + "। " + CONFIRM_KEYS


def slots_for_screen(state: dict) -> list[dict]:
    slots = state["slots"]
    wanted = _needed(state) if state.get("flow") else []
    rows = []
    for slot in wanted:
        if slot == "deadline_days" and slot not in slots and _value(slots, "cash_needed_tk") == 0:
            continue
        label_bn, label_en = SLOT_LABELS[slot]
        s = slots.get(slot)
        if s is None:
            display = None
        elif slot == "quantity_kg":
            display = f"{fmt_num(s['value'] / MAUND_KG)} মণ = {fmt_num(_sacks(s['value']), 0)} বস্তা ({fmt_num(s['value'], 0)} কেজি)"
        elif slot == "deadline_days":
            display = f"{fmt_num(s['value'], 0)} দিন"
        elif slot == "offer_per_kg":
            display = f"৳{fmt_num(s['value'])} / কেজি" if s["value"] > 0 else "জানা নেই"
        elif slot == "in_storage":
            display = "হ্যাঁ" if s["value"] else "না"
        else:
            display = f"৳{fmt_taka(s['value'], rounded=False)}" if s["value"] > 0 else "নেই"
        rows.append({"slot": slot, "label_bn": label_bn, "label_en": label_en, "display": display,
                     "value": None if s is None else s["value"], "source": None if s is None else s.get("source"),
                     "heard": None if s is None else s.get("heard")})
    return rows


def advice_sms(plan: dict) -> str:
    """The store-or-sell advice as one SMS, from the engine's plan (used by the call and the dashboard)."""
    rec, opts = plan["recommendation"], plan["options"]
    chosen = opts.get(rec["key"]) or opts["sell_now"]
    sacks = plan["inputs"]["sacks"]
    text = f"কৃষিভল্ট: {fmt_num(sacks, 0)} বস্তা আলু। পরামর্শ: {rec['title_bn']}। "
    if rec["key"] == "sell_now":
        return text + f"খরচ বাদে প্রায় {fmt_taka(chosen['money_mean'])} টাকা।"
    return text + (f"গড়ে প্রায় {fmt_taka(chosen['money_mean'])} টাকা (খারাপ হলে {fmt_taka(chosen['money_low'])})। "
                   f"এখন সব বেচলে {fmt_taka(opts['sell_now']['money_mean'])} টাকা। নিশ্চিত নয়।")


def _profit_lines(p: dict, key: str) -> list[str]:
    """Net profit after the growing cost (the plan's "net-profit visibility"): the farmer's local benchmark."""
    cost = f"এলাকার গড় উৎপাদন খরচ কেজিতে {fmt_num(p['growing_cost_per_kg'])} টাকা ধরলে"
    if key == "sell_now":
        if p["below_cost_now"]:
            return [f"{cost}, এই দামে খরচও পুরো উঠছে না; তবু রাখলে লোকসান আরও বাড়তে পারে।"]
        return [f"{cost}, লাভ থাকে প্রায় {fmt_taka(p['sell_all_now'])} টাকা।"]
    now = (f"এখন সব বেচলে লাভ প্রায় {fmt_taka(p['sell_all_now'])} টাকা" if p["sell_all_now"] >= 0
           else f"এখন সব বেচলে লোকসান প্রায় {fmt_taka(-p['sell_all_now'])} টাকা")
    lines = [f"{cost}, {now}; পরামর্শমতো গড়ে লাভ প্রায় {fmt_taka(p['with_advice'])} টাকা।"]
    if p["with_advice_low"] < 0:
        lines.append(f"দাম খারাপ হলে প্রায় {fmt_taka(-p['with_advice_low'])} টাকা লোকসানও হতে পারে।")
    return lines


def curing_sms() -> str:
    """The reminder sent before the harvest: cure in shade, sort, then cold storage (from the plan)."""
    lo, hi = CURING_WEEKS
    return (f"কৃষিভল্ট: আলু তোলার পর {fmt_num(lo, 0)}-{fmt_num(hi, 0)} সপ্তাহ ছায়ায় রেখে শুকিয়ে নিন (কিউরিং), "
            f"কাটা ও পচা আলু বাদ দিন, তারপর হিমাগারে দিন। এতে হিমাগারে ওজন ও পচন কম হয়। বীজ আলু আলাদা রাখুন।")


# The call state lives in the browser, so the SMS text in it is signed: only text this server wrote
# can be sent. The key is random per server start unless KV_STATE_SECRET is set.
_SECRET = (os.getenv("KV_STATE_SECRET") or os.urandom(16).hex()).encode()


def sign(text: str) -> str:
    return hmac.new(_SECRET, text.encode("utf-8"), hashlib.sha256).hexdigest()[:24]


def _sign_next(nxt: Optional[dict]) -> Optional[str]:
    return sign(json.dumps(nxt, sort_keys=True, ensure_ascii=False)) if nxt else None


def receipt_sms(state: dict) -> Optional[str]:
    """The SMS receipt: built from the engine's numbers when the answer was given, plus the action's number."""
    text = state.get("sms")
    if not text or not hmac.compare_digest(sign(text), str(state.get("sms_sig") or "")):
        return None
    action = state.get("action") or {}
    ref = re.sub(r"\D", "", str(action.get("ref") or ""))[:6]
    if ref:
        text += f" নং {to_bn_digits(ref)} (ডেমো)।"
    return text


# ------------------------------------------------------------------ the state machine
class Conversation:
    def __init__(self, gemini: Optional[GeminiClient] = None, planner: Optional[StoragePlanner] = None):
        self.gemini = gemini
        self.planner = planner or StoragePlanner()

    # -- public -------------------------------------------------------------------------------
    def turn(self, state: Optional[dict], inp: dict) -> dict:
        inp = inp or {}
        kind = inp.get("kind", "start")
        if state is None or kind == "start":
            state = new_state(inp.get("district", "Bogura"), inp.get("month"), inp.get("year"), inp.get("phone"))
            return self._reply(state, f"{GREETING} {MENU}", "menu", MENU_KEYS)

        state = _clean(state)
        if inp.get("phone"):
            state["phone"] = inp["phone"]
        text = (inp.get("text") or "").strip()
        digits = (inp.get("digits") or "").strip()
        heard = None
        if kind == "speech":
            if not text:
                return self._fail(state)
            expecting = state.get("asking") if state["step"] == "ask" else None
            unit = "sack" if state.get("flow") in SACK_FLOWS else "maund"
            heard = understand(text, expecting=expecting, asked_text=state.get("last_say", ""),
                               gemini=self.gemini, quantity_unit=unit)
            heard["text"] = text

        handler = {
            "menu": self._menu, "ask": self._ask, "confirm": self._confirm, "result": self._result,
            "done": self._done, "help": self._help, "ended": self._ended,
        }[state["step"]]
        reply = handler(state, kind, digits, heard)
        reply["heard"] = None if heard is None else {
            "text": text, "values": heard["values"], "rejected": heard["rejected"], "menu": heard["menu"],
            "yes_no": heard["yes_no"], "in_storage": heard.get("in_storage"), "gemini": heard["gemini"],
        }
        return reply

    # -- replies ------------------------------------------------------------------------------
    def _reply(self, state: dict, say: str, expects: str, keys: list, **extra) -> dict:
        state["last_say"] = say
        out = {
            "state": state, "say": say,
            "expects": expects,   # "menu" / "choice": one key; "number": digits then #; "end"
            "keys": keys,
            "flow": state.get("flow"),
            "slots": slots_for_screen(state),
            "result": state.get("result"),
            "narration": None, "event": None,
            "sms_text": receipt_sms(state),
            "done": expects == "end",
        }
        out.update(extra)
        return out

    def _result_keys(self, state: dict) -> list:
        result = state.get("result") or {}
        consent = ["8"] if result.get("flow") == "advice" and not state.get("counted") else []
        return (["2"] if result.get("next") else []) + consent + ["1", "0", "9"]

    def _count_me(self, state: dict) -> dict:
        """The farmer pressed 8: count this answer for the district figures, without a name or number."""
        # The state comes back from the browser: take the figures from the read-back answers, within limits
        result, slots = state["result"], state["slots"]
        cash = min(max(_value(slots, "cash_needed_tk"), 0.0), 10_000_000)
        key = result.get("key") if result.get("key") in ("sell_now", "sell_part", "store") else "unknown"
        farmer_signals.record(state.get("district", ""), state["month"], state["year"],
                              min(_sacks(_value(slots, "quantity_kg")), 100_000), cash,
                              min(int(_value(slots, "deadline_days", 30)), 365) if cash > 0 else 0,
                              "cold" if _value(slots, "in_storage") else "no", key, "call")
        state["counted"] = True
        state["result_say"] = state["result_say"].replace(CONSENT_ASK + " ", "")
        next_line = (result.get("next") or {}).get("line")
        return self._reply(state, f"{COUNTED} " + (next_line + " " if next_line else "") + CLOSING,
                           "choice", self._result_keys(state))

    def _prompt(self, state: dict) -> tuple[str, str, list]:
        step = state["step"]
        if step == "ask":
            return self._question(state), ("choice" if state["asking"] == "in_storage" else "number"), \
                (["1", "2"] if state["asking"] == "in_storage" else [])
        if step == "confirm":
            return readback(state), "choice", ["1", "2"]
        if step == "result":
            return state["result_say"], "choice", self._result_keys(state)
        if step == "done":
            return state["done_say"], "choice", ["1", "0", "9"]
        return MENU, "menu", MENU_KEYS

    def _question(self, state: dict) -> str:
        slot = state["asking"]
        if slot == "quantity_kg" and state.get("flow") in SACK_FLOWS:
            return QUESTIONS["quantity_sacks"]
        return QUESTIONS[slot]

    def _fail(self, state: dict) -> dict:
        state["fails"] = state.get("fails", 0) + 1
        if state["step"] == "help":
            return self._reply(state, HELP, "choice", ["1", "9"])
        if state["fails"] >= 2:
            state["help_return"] = {"step": state["step"], "asking": state.get("asking")}
            state["step"], state["fails"] = "help", 0
            return self._reply(state, HELP, "choice", ["1", "9"])
        say, expects, keys = self._prompt(state)
        return self._reply(state, f"{NOT_UNDERSTOOD} {say}", expects, keys)

    def _merge(self, state: dict, heard: dict) -> bool:
        """Take what the farmer said; a newer value replaces an older one (a correction)."""
        took = False
        for slot, v in heard["values"].items():
            if slot in SLOT_LABELS:
                state["slots"][slot] = dict(v)
                took = True
        if heard.get("in_storage") is not None:
            state["slots"]["in_storage"] = {"value": 1.0 if heard["in_storage"] else 0.0,
                                            "heard": heard.get("text"), "source": "parser"}
            took = True
        return took

    def _to_menu(self, state: dict, prefix: str = "") -> dict:
        state.update({"step": "menu", "flow": None, "asking": None, "fails": 0, "result": None})
        return self._reply(state, (prefix + " " + MENU).strip(), "menu", MENU_KEYS)

    # -- steps --------------------------------------------------------------------------------
    def _menu(self, state, kind, digits, heard):
        if kind == "keypad":
            choice = MENU_CHOICES.get(digits[:1])
        else:
            choice = heard["menu"]
            # Potato numbers without a clear choice mean the store-or-sell question
            if choice is None and heard["values"]:
                choice = "advice"
        if choice == "helper":
            return self._helper(state, "pressed 9 at the menu")
        if choice in FLOW_SLOTS:
            return self._start_flow(state, choice, heard)
        return self._fail(state)

    def _start_flow(self, state: dict, flow: str, heard: Optional[dict] = None) -> dict:
        state["flow"] = flow
        state["result"] = None
        if heard:
            self._merge(state, heard)
        return self._next_question(state)

    def _next_question(self, state):
        missing = _missing(state)
        state["fails"] = 0
        if missing:
            state["step"], state["asking"] = "ask", missing
            say, expects, keys = self._prompt(state)
            return self._reply(state, say, expects, keys)
        state["step"], state["asking"] = "confirm", None
        return self._reply(state, readback(state), "choice", ["1", "2"])

    def _ask(self, state, kind, digits, heard):
        slot = state["asking"]
        if kind == "keypad":
            if digits.startswith("*"):
                return self._to_menu(state)
            if slot == "in_storage":
                if digits[:1] in ("1", "2"):
                    state["slots"]["in_storage"] = {"value": 1.0 if digits[:1] == "1" else 0.0,
                                                    "heard": digits[:1], "source": "keypad"}
                    return self._next_question(state)
                return self._fail(state)
            number = digits.rstrip("#")
            if number.isdigit():
                unit = "sack" if state.get("flow") in SACK_FLOWS else "maund"
                ans = bare_answer(slot, float(number), unit)
                if in_limits(slot, ans["value"]):
                    state["slots"][slot] = {**ans, "heard": f"{number}#", "source": "keypad"}
                    return self._next_question(state)
            return self._fail(state)
        if slot == "in_storage" and heard.get("in_storage") is None and heard["yes_no"] is not None:
            heard["in_storage"] = heard["yes_no"]
        if self._merge(state, heard):
            return self._next_question(state)
        if heard["menu"] == "helper":
            return self._helper(state, "asked for a person while answering questions")
        return self._fail(state)

    def _confirm(self, state, kind, digits, heard):
        if kind == "keypad":
            yes, no = digits[:1] == "1", digits[:1] == "2"
        else:
            if heard["values"] or heard.get("in_storage") is not None:   # "না, ৬০ মণ": correct and read back
                self._merge(state, heard)
                return self._next_question(state)
            yes, no = heard["yes_no"] is True, heard["yes_no"] is False
        if yes:
            return self._answer(state)
        if no:
            state["slots"] = {}
            reply = self._next_question(state)
            reply["say"] = "ঠিক আছে, আবার শুরু করি। " + reply["say"]
            state["last_say"] = reply["say"]
            return reply
        return self._fail(state)

    def _key_from_speech(self, heard) -> Optional[str]:
        if heard["menu"] == "helper":
            return "9"
        if _said_again(heard["text"]):
            return "1"
        if heard["yes_no"] is True:
            return "2"
        return None

    def _result(self, state, kind, digits, heard):
        key = digits[:1] if kind == "keypad" else self._key_from_speech(heard)
        result = state.get("result") or {}
        if key == "2" and result.get("next"):
            return self._next_step(state)
        if key == "8" and "8" in self._result_keys(state):
            return self._count_me(state)
        if key == "1":
            return self._reply(state, state["result_say"], "choice", self._result_keys(state))
        if key == "0":
            return self._to_menu(state)
        if key == "9":
            return self._helper(state, f"pressed 9 after the {state.get('flow')} answer")
        return self._fail(state)

    def _done(self, state, kind, digits, heard):
        key = digits[:1] if kind == "keypad" else self._key_from_speech(heard)
        if key == "1":
            return self._reply(state, state["done_say"], "choice", ["1", "0", "9"])
        if key == "0":
            return self._to_menu(state)
        if key == "9":
            return self._helper(state, "pressed 9 after the request")
        state["step"] = "ended"
        return self._reply(state, ENDED, "end", [])

    def _help(self, state, kind, digits, heard):
        key = digits[:1] if kind == "keypad" else (
            "9" if heard["menu"] == "helper" else ("1" if heard["yes_no"] is True else None))
        if key == "9":
            return self._helper(state, "could not be understood twice")
        if key == "1":
            back = state.get("help_return") or {"step": "menu", "asking": None}
            state["step"], state["asking"], state["fails"] = back["step"], back["asking"], 0
            say, expects, keys = self._prompt(state)
            return self._reply(state, say, expects, keys)
        return self._fail(state)

    def _ended(self, state, kind, digits, heard):
        return self._reply(state, ENDED, "end", [])

    def _helper(self, state, reason: str) -> dict:
        details = {"reason": reason, "flow": state.get("flow"),
                   "values": {s["slot"]: s["display"] for s in slots_for_screen(state) if s["display"]}}
        event = events.record("helper_callback", "কৃষক সহকারীর ফোন চেয়েছেন", details,
                              district=state.get("district", ""), phone=state.get("phone"))
        state["step"] = "ended"
        return self._reply(state, HELPER, "end", [], event=event)

    # -- answers ------------------------------------------------------------------------------
    def _answer(self, state: dict) -> dict:
        flow = state["flow"]
        body, result, sms = {"advice": self._advice, "outlook": self._outlook,
                             "group": self._group, "loan": self._loan}[flow](state)
        rewrite = None
        if self.gemini is not None and self.gemini.available:
            rewrite = lambda t: self.gemini.text(REWORD_PROMPT.format(text=t))  # noqa: E731
        narration = narrate(body, rewrite)
        next_line = (result.get("next") or {}).get("line")
        consent = CONSENT_ASK if flow == "advice" and not state.get("counted") else ""
        say = narration["text"] + (" " + next_line if next_line else "") + (" " + consent if consent else "") + " " + CLOSING
        state.update({"result": result, "result_say": say, "result_body": narration["text"], "sms": sms,
                      "sms_sig": sign(sms) if sms else None, "next_sig": _sign_next(result.get("next")),
                      "step": "result", "fails": 0, "action": None})
        narration_screen = {"status": narration["status"], "check": narration["check"], "template": body,
                            "rejected_text": narration.get("rejected_text"),
                            "model": getattr(self.gemini, "model_used", None)}
        return self._reply(state, say, "choice", self._result_keys(state), narration=narration_screen)

    def _price(self, state: dict) -> tuple[float, bool]:
        offer = _value(state["slots"], "offer_per_kg")
        return (offer, False) if offer > 0 else (demo_price(state["month"]), True)

    def lot(self, state: dict) -> FarmerLot:
        slots = state["slots"]
        price, _ = self._price(state)
        stored = "cold" if _value(slots, "in_storage") else "no"
        cash = _value(slots, "cash_needed_tk")
        return FarmerLot(
            quantity_kg=_value(slots, "quantity_kg"), price_today=price,
            decision_month=state["month"], decision_year=state["year"],
            stored=stored, stored_since_month=3 if stored == "cold" else None,
            cash_needed_tk=cash, cash_days=int(_value(slots, "deadline_days", 30)) if cash > 0 else 0,
        )

    def _advice(self, state: dict):
        lot = self.lot(state)
        plan = self.planner.plan(lot)
        rec = plan["recommendation"]
        opts = plan["options"]
        chosen = opts.get(rec["key"]) or opts["sell_now"]
        now = opts["sell_now"]
        sacks = lot.sacks
        price, assumed = self._price(state)
        lines = []
        if assumed:
            lines.append(f"আজকের দাম জানা না থাকায় নমুনা হিসেবে কেজি {fmt_num(price)} টাকা ধরা হলো।")
        if rec["key"] == "sell_now":
            lines.append(f"পরামর্শ: এখনই সব {fmt_num(sacks, 0)} বস্তা আলু বেচুন।")
            lines.append(f"কেজিতে {fmt_num(price)} টাকা দরে খরচ বাদে হাতে আসবে প্রায় {fmt_taka(now['money_mean'])} টাকা।")
            store = opts.get("store")
            if store and store["gain_vs_now"] < 0:
                lines.append(f"হিমাগারে রাখলে ভাড়া আর খরচ বাদে সবচেয়ে ভালো মাসেও গড়ে প্রায় "
                             f"{fmt_taka(abs(store['gain_vs_now']))} টাকা কম আসতে পারে।")
            elif plan["months_left"] == 0:
                lines.append("এ মৌসুমে হিমাগারে রাখার সময় আর নেই।")
            else:
                lines.append("রাখলে লাভের সম্ভাবনা কম, ঝুঁকি বেশি।")
            if plan["outlook"]["k"] <= 0.3:
                lines.append("এবার ফলন বেশি, তাই দাম তেমন বাড়ার সম্ভাবনা কম।")
            if lot.cash_needed_tk > 0 and now["money_mean"] >= lot.cash_needed_tk:
                lines.append(f"এতে আপনার {fmt_taka(lot.cash_needed_tk, rounded=False)} টাকার দরকার মিটবে।")
            nxt = {"kind": "buyer_lot", "sacks": sacks,
                   "line": "আমাদের ক্রেতাদের দর তুলনা করে জানাতে ২ চাপুন।"}
        elif rec["key"] == "store":
            lines.append(f"পরামর্শ: সব {fmt_num(sacks, 0)} বস্তা হিমাগারে রেখে {chosen['sell_month_bn']} মাসে বেচুন।")
            lines.append(f"গড়ে হাতে আসতে পারে প্রায় {fmt_taka(chosen['money_mean'])} টাকা, "
                         f"এখন বেচার চেয়ে প্রায় {fmt_taka(chosen['gain_vs_now'])} টাকা বেশি।")
            lines.append(f"দাম খারাপ হলে প্রায় {fmt_taka(chosen['money_low'])} টাকা। "
                         f"১০০ বারের হিসাবে {fmt_num(round(chosen['chance_beats_now'] * 100), 0)} বার রাখাটাই ভালো হয়।")
            if lot.stored == "no":
                lines.append(f"ভাড়া এক মাস রাখলেও বস্তায় {fmt_num(lot.terms.rent_per_sack, 0)} টাকা, "
                             f"{fmt_num(lot.terms.season_months, 0)} মাস রাখলেও একই, তাই আগেভাগে বেচবেন না।")
            if chosen.get("loan"):
                loan = chosen["loan"]
                lines.append(f"টাকার দরকার মেটাতে বস্তার জামানতে প্রায় {fmt_taka(loan['amount'])} টাকা ঋণ লাগবে, "
                             f"সুদ প্রায় {fmt_taka(loan['interest'])} টাকা।")
            nxt = None if lot.stored == "cold" else {
                "kind": "cold_storage_booking", "sacks": sacks,
                "line": f"হিমাগারে {fmt_num(sacks, 0)} বস্তার জায়গা চাইতে ২ চাপুন।"}
        else:  # sell_part (or the staggered exit)
            lines.append(f"পরামর্শ: এখন {fmt_num(chosen['sell_sacks_now'], 0)} বস্তা বেচুন, "
                         f"হাতে আসবে প্রায় {fmt_taka(chosen['cash_now'])} টাকা।")
            if rec["key"] == "staggered":
                lines.append(f"বাকি {fmt_num(chosen['store_sacks'], 0)} বস্তা হিমাগারে রাখুন: {chosen['title_bn'].split(': ', 1)[1]}।")
            else:
                lines.append(f"বাকি {fmt_num(chosen['store_sacks'], 0)} বস্তা হিমাগারে রেখে {chosen['sell_month_bn']} মাসে বেচুন।")
            lines.append(f"সব মিলিয়ে গড়ে প্রায় {fmt_taka(chosen['money_mean'])} টাকা, এখন সব বেচার চেয়ে প্রায় "
                         f"{fmt_taka(chosen['gain_vs_now'])} টাকা বেশি; দাম খারাপ হলে প্রায় {fmt_taka(chosen['money_low'])} টাকা।")
            if lot.cash_needed_tk > 0 and chosen["cash_now"] >= lot.cash_needed_tk:
                lines.append(f"এতে আপনার {fmt_taka(lot.cash_needed_tk, rounded=False)} টাকার দরকার মিটবে।")
            lines.append("দাম বাড়বেই এমন কথা নেই, তাই কিছুটা এখনই বেচা নিরাপদ।")
            nxt = None if lot.stored == "cold" else {
                "kind": "cold_storage_booking", "sacks": chosen["store_sacks"],
                "line": f"হিমাগারে {fmt_num(chosen['store_sacks'], 0)} বস্তার জায়গা চাইতে ২ চাপুন।"}

        lines.extend(_profit_lines(plan["net_profit"], rec["key"]))
        result = {
            "flow": "advice", "title_bn": rec["title_bn"], "title_en": rec["title_en"], "key": rec["key"],
            "net_profit": plan["net_profit"],
            "reasons": rec["reasons"], "notes": plan["notes"], "price_today": price, "price_assumed": assumed,
            "months_left": plan["months_left"], "outlook": plan["outlook"],
            "options": [dict(o, recommended=(o["key"] == rec["key"])) for o in opts.values() if o],
            "by_month": [{k: r[k] for k in ("h", "month_bn", "month_en", "price_low", "price_mid", "price_high",
                                             "net_mean", "net_low", "net_high", "gain_vs_now", "chance_beats_now",
                                             "break_even_price")} for r in plan["by_month"]],
            "sacks": sacks, "next": nxt,
        }
        return " ".join(lines), result, advice_sms(plan)

    def _outlook(self, state: dict):
        price, assumed = self._price(state)
        lot = FarmerLot(quantity_kg=SACK_KG, price_today=price, decision_month=state["month"],
                        decision_year=state["year"], stored="cold" if state["month"] not in HARVEST_MONTHS else "no",
                        stored_since_month=3)
        H = months_left(lot)
        lines = []
        if assumed:
            lines.append(f"আজকের দাম জানা না থাকায় নমুনা হিসেবে কেজি {fmt_num(price)} টাকা ধরা হলো।")
        if H == 0:
            lines.append("এ মৌসুমে হিমাগারে রাখার সময় শেষ, নতুন আলু আসছে।")
            months, o = [], None
        else:
            o = price_outlook(price, state["month"], state["year"], horizon=H)
            months = o["months"]
            mid = months[min(3, H)] if H > 3 else None
            last = months[H]
            if mid:
                lines.append(f"আজ কেজি {fmt_num(price)} টাকা হলে, {mid['month_bn']} মাসে মাঝামাঝি প্রায় {fmt_num(mid['mid'])} টাকা,")
                lines.append(f"আর {last['month_bn']} মাসে প্রায় {fmt_num(last['mid'])} টাকা হতে পারে।")
            else:
                lines.append(f"আজ কেজি {fmt_num(price)} টাকা হলে, {last['month_bn']} মাসে প্রায় {fmt_num(last['mid'])} টাকা হতে পারে।")
            lines.append(f"কম হলে {fmt_num(last['low'])} টাকা, বেশি হলে {fmt_num(last['high'])} টাকা পর্যন্ত।")
            gap = o["rise"]["gap_pct"]
            if gap > 3 or o["rise"]["k"] <= 0.3:
                lines.append("এবার ফলন বেশি, তাই দাম কম বাড়তে পারে।")
            elif gap < -3:
                lines.append("এবার ফলন কম, তাই দাম বেশি বাড়তে পারে।")
            lines.append("এটা হিসাব, নিশ্চিত নয়।")
        result = {"flow": "outlook", "title_bn": "দামের পূর্বাভাস", "title_en": "Price outlook",
                  "price_today": price, "price_assumed": assumed, "months_left": H,
                  "outlook": o["rise"] if o else None, "months": months,
                  "next": {"kind": "go_advice", "line": "রাখবেন না বেচবেন, পরামর্শ শুনতে ২ চাপুন।"}}
        sms = None
        if months:
            last = months[-1]
            sms = (f"কৃষিভল্ট দামের পূর্বাভাস: আজ কেজি {fmt_num(price)} টাকা। {last['month_bn']} মাসে "
                   f"{fmt_num(last['low'])} থেকে {fmt_num(last['high'])} টাকা, মাঝামাঝি {fmt_num(last['mid'])}। নিশ্চিত নয়।")
        return " ".join(lines), result, sms

    def _pool_for(self, district: str) -> Optional[dict]:
        pools = [p for p in demo_data.partners()["group_pools"] if p["district"].lower() == (district or "").lower()]
        return pools[0] if pools else None

    def _group(self, state: dict):
        sacks = _sacks(_value(state["slots"], "quantity_kg"))
        pool = self._pool_for(state["district"])
        if not pool:
            body = "আপনার এলাকায় এখনো কোনো দল নেই। আমাদের সহকারী ফোন করে দল গড়তে সাহায্য করবেন।"
            result = {"flow": "group", "title_bn": "এলাকায় দল নেই", "title_en": "No group in this area yet", "next": None}
            return body, result, None
        cmp = group_storage.compare(pool["id"], sacks)
        st = cmp["pool"]
        transport = demo_data.partners()["transport"]
        per_sack = transport["individual_per_sack"] - transport["group_truck_per_sack"]
        lines = [f"{pool['name_bn']}: এখন {fmt_num(st['member_count'], 0)} জন কৃষক, মোট {fmt_num(st['total_sacks'] - sacks, 0)} বস্তা।",
                 f"একসাথে গাড়ি নিলে বস্তায় প্রায় {fmt_num(per_sack, 0)} টাকা, আপনার {fmt_num(sacks, 0)} বস্তায় প্রায় "
                 f"{fmt_taka(cmp['group_now']['saving'], rounded=False)} টাকা বাঁচবে।"]
        nt = st["next_tier"]
        reached = [t for t in st["tiers"] if t["reached"] and not t["agreed"]]
        if reached:
            t = reached[-1]
            lines.append(f"আপনাকে নিয়ে দলে {fmt_num(st['total_sacks'], 0)} বস্তা হয়, তাতে হিমাগার বস্তায় "
                         f"{fmt_num(t['rent_per_sack'], 0)} টাকা ভাড়ার প্রস্তাব দিয়েছে। হিমাগার রাজি হলে তবেই এটা গণ্য হবে।")
        elif nt:
            lines.append(f"আরও {fmt_num(nt['sacks_short'], 0)} বস্তা হলে হিমাগার বস্তায় {fmt_num(nt['rent_per_sack'], 0)} "
                         f"টাকা ভাড়ার প্রস্তাব দিয়েছে। হিমাগার রাজি হলে তবেই এটা গণ্য হবে।")
        result = {"flow": "group", "title_bn": f"{pool['name_bn']}-এ যোগ দিন", "title_en": f"Join {pool['name']}",
                  "compare": cmp, "sacks": sacks,
                  "next": {"kind": "group_storage_join", "pool_id": pool["id"], "sacks": sacks,
                           "line": "দলে যোগ দিতে ২ চাপুন।"}}
        sms = (f"কৃষিভল্ট: {pool['name_bn']}, {fmt_num(sacks, 0)} বস্তা। গাড়ি ভাগ করে প্রায় "
               f"{fmt_taka(cmp['group_now']['saving'], rounded=False)} টাকা কম খরচ।")
        return " ".join(lines), result, sms

    def _loan(self, state: dict):
        sacks = _sacks(_value(state["slots"], "quantity_kg"))
        price, assumed = self._price(state)
        months = max(1, months_left(FarmerLot(SACK_KG, price, state["month"], state["year"])))
        rows = financing.compare_banks(sacks, price, state["month"], state["year"], months)
        banks = [r for r in rows if r["bank"]["id"] != "cold-storage-advance" and not r["problems"] and r["max_loan"] > 0]
        adv = next(r for r in rows if r["bank"]["id"] == "cold-storage-advance")
        lines = []
        if assumed:
            lines.append(f"আজকের দাম জানা না থাকায় নমুনা হিসেবে কেজি {fmt_num(price)} টাকা ধরা হলো।")
        if not banks:
            lines.append(f"আপনার {fmt_num(sacks, 0)} বস্তায় ডেমো ব্যাংকের ঋণ মিলছে না। হিমাগারের নিজের অগ্রিম "
                         f"বস্তায় {fmt_num(StorageTerms().cs_advance_per_sack, 0)} টাকা, মোট প্রায় {fmt_taka(adv['max_loan'], rounded=False)} টাকা।")
            result = {"flow": "loan", "title_bn": "ব্যাংক ঋণ মিলছে না", "title_en": "No bank loan fits", "banks": rows, "next": None}
            return " ".join(lines), result, None
        best = min(banks, key=lambda r: r["bank"]["rate_year"])
        bank = demo_data.bank(best["bank"]["id"])
        lines.append(f"আপনার {fmt_num(sacks, 0)} বস্তা আলুর জামানতে {bank['name_bn']} সর্বোচ্চ প্রায় "
                     f"{fmt_taka(best['max_loan'])} টাকা ঋণ দিতে পারে।")
        lines.append(f"{fmt_num(best['months'], 0)} মাসে সুদ প্রায় {fmt_taka(best['interest'])} টাকা। হিমাগারের ভাড়া আগে কাটা হবে।")
        if best.get("sacks_to_repay"):
            lines.append(f"শোধ করতে {MONTHS_BN[best['repay_month']]} মাসে প্রায় "
                         f"{fmt_num(best['sacks_to_repay'], 0)} বস্তা বেচতে হবে।")
        lines.append("এটা ডেমো ব্যাংকের হিসাব; ব্যাংক যাচাই করে সিদ্ধান্ত নেবে।")
        result = {"flow": "loan", "title_bn": f"{bank['name_bn']}: সর্বোচ্চ {fmt_taka(best['max_loan'])} টাকা",
                  "title_en": f"{bank['name']}: up to ৳{best['max_loan']:,}", "banks": rows, "best": best,
                  "next": {"kind": "loan_application", "bank_id": bank["id"], "sacks": sacks, "price": price,
                           "months": best["months"], "line": "আবেদন পাঠাতে ২ চাপুন।"}}
        sms = (f"কৃষিভল্ট: {fmt_num(sacks, 0)} বস্তা জামানতে {bank['name_bn']} সর্বোচ্চ প্রায় "
               f"{fmt_taka(best['max_loan'])} টাকা, সুদ প্রায় {fmt_taka(best['interest'])} টাকা (ডেমো হিসাব)।")
        return " ".join(lines), result, sms

    # -- the "press 2" step -------------------------------------------------------------------
    def _next_step(self, state: dict) -> dict:
        nxt = state["result"]["next"]
        if not hmac.compare_digest(_sign_next(nxt) or "", str(state.get("next_sig") or "")):
            return self._fail(state)   # only an action this server offered can be taken
        kind = nxt["kind"]
        if kind == "go_advice":
            price = state["slots"].get("offer_per_kg")
            state["slots"] = {"offer_per_kg": price} if price else {}
            return self._start_flow(state, "advice")
        district = state.get("district", "")
        phone = state.get("phone")
        sacks = nxt.get("sacks")
        if kind == "cold_storage_booking":
            cs = next((c for c in demo_data.partners()["cold_storages"]
                       if c["district"].lower() == district.lower()), demo_data.partners()["cold_storages"][0])
            if farmer_signals.free_sacks(cs) < sacks:      # full: try a partner cold storage with space
                other = next((c for c in demo_data.partners()["cold_storages"]
                              if c["id"] != cs["id"] and not receipts.partner_check(c)
                              and farmer_signals.free_sacks(c) >= sacks), None)
                events.record(kind, f"{sacks} বস্তা আলু রাখার অনুরোধ (জায়গা নেই)",
                              {"sacks": sacks, "cold_storage": cs["name"], "no_space": True},
                              district=district, phone=phone)
                cs = other or cs
            event = events.record(kind, f"{sacks} বস্তা আলু রাখার অনুরোধ",
                                  {"sacks": sacks, "cold_storage": cs["name"], "rent_per_sack": cs["rent_per_sack"],
                                   "advice": state["result"]["title_en"]}, district=district, phone=phone)
            state["booking_ref"] = event["ref"]
            say = (f"{cs['name_bn']}-তে {fmt_num(sacks, 0)} বস্তার জায়গার অনুরোধ পাঠানো হয়েছে। অনুরোধ নম্বর "
                   f"{to_bn_digits(event['ref'])}। আলু রাখার সময় হিমাগার ওজন করে রসিদ এসএমএসে পাঠাবে; সেই রসিদ দিয়ে "
                   f"বস্তার জামানতে ব্যাংক ঋণের আবেদন করা যাবে।")
        elif kind == "buyer_lot":
            event = events.record(kind, f"{sacks} বস্তা আলু বিক্রির লট",
                                  {"sacks": sacks, "kg": round(sacks * SACK_KG),
                                   "price_today": state["result"].get("price_today")}, district=district, phone=phone)
            say = (f"আপনার {fmt_num(sacks, 0)} বস্তা আলুর খবর আমাদের ক্রেতাদের কাছে গেছে। নম্বর "
                   f"{to_bn_digits(event['ref'])}। ভালো দর পেলে আমরা ফোন করে জানাব।")
        elif kind == "group_storage_join":
            joined = group_storage.join(nxt["pool_id"], "Caller (call preview)", sacks, phone)
            event = joined["event"]
            say = (f"দলে আপনার {fmt_num(sacks, 0)} বস্তা যোগ হয়েছে। নম্বর {to_bn_digits(joined['ref'])}। "
                   f"দলে এখন মোট {fmt_num(joined['pool']['total_sacks'], 0)} বস্তা।")
        elif kind == "loan_application":
            cs = next((c for c in demo_data.partners()["cold_storages"]
                       if c["district"].lower() == district.lower()), demo_data.partners()["cold_storages"][0])
            booking = re.sub(r"\D", "", str(state.get("booking_ref") or ""))[:6]
            receipt = f"DEMO-{booking or 'R' + events.new_reference()}"
            app = financing.apply("Caller (call preview)", phone, district, cs["id"], receipt, sacks, nxt["price"],
                                  state["month"], state["year"], nxt["months"], nxt["bank_id"])
            event = {"ref": app["ref"], "kind": kind, "application": app["id"]}
            say = (f"ঋণের আবেদন পাঠানো হয়েছে। নম্বর {to_bn_digits(app['ref'])}। হিমাগার আপনার বস্তা মিলিয়ে "
                   f"দেখলে তারপর ব্যাংক সিদ্ধান্ত জানাবে।")
        else:
            return self._fail(state)
        state["action"] = {"kind": kind, "ref": event["ref"]}
        state["done_say"] = say + " রসিদ এসএমএসে যাবে। " + CLOSING
        state["step"] = "done"
        return self._reply(state, state["done_say"], "choice", ["1", "0", "9"], event=event)
