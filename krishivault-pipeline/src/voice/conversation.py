"""
The farmer's call, step by step
===============================
One state machine for the selling call, used by the web conversation screen today and by a real phone
line later. Each turn takes the call state and what the farmer did (spoke, or pressed keys) and returns
the new state and what KrishiVault says next. The state is a plain dict, so the screen keeps it and
sends it back with each turn.

  menu ── 1 / "আলু বেচব" ──> questions (only what is missing) ──> read-back: "ঠিক হলে ১, ভুল হলে ২"
       ── 2, 3 ──> "not in this prototype yet"                          │
       ── 9 ──> officer callback (end)                                  v
                                       advice in taka (decision engine; Gemini may reword, number lock)
                                       "২ = book / send the lot, ১ = আবার শুনুন, ৯ = কর্মকর্তা"
                                                                        │
                                                       action recorded for the partner screen, SMS text

Rules from docs/PLAN_DETAILS.md, section 4: keypad always works; every number read back; two
failures lead to the keypad and an officer callback; every call ends with "১ = আবার শুনুন,
৯ = কর্মকর্তা ফোন করবেন". Every number the farmer hears comes from the engine (number lock).
"""

import math
from typing import Any, Callable, Optional

from config.settings import MAUND_TO_KG
from src import events
from src.engine.decision_engine import DecisionEngine, FarmerSituation
from src.engine.market_inputs import partner_context, seasonal_outlook
from src.voice.bangla_numbers import fmt_num, fmt_taka, nfc, to_bn_digits
from src.voice.gemini import GeminiClient
from src.voice.intent_parser import SACK_KG, prepare
from src.voice.number_lock import narrate
from src.voice.understanding import SLOTS, bare_answer, in_limits, understand

# ------------------------------------------------------------------ what KrishiVault says
GREETING = "আসসালামু আলাইকুম, কৃষিভল্টে স্বাগতম। আপনার কথা শুধু আপনাকে পরামর্শ দিতে ব্যবহার হবে।"
MENU = (
    "ফসল বেচার দাম আর পরামর্শের জন্য ১ চাপুন। সার ও কীটনাশকের জন্য ২। বীজ ও যন্ত্রপাতির জন্য ৩। "
    "কৃষি কর্মকর্তা আপনাকে ফোন করবেন, এর জন্য ৯। অথবা আপনার কথা বলুন।"
)
QUESTIONS = {
    "quantity_kg": "আপনার কত মণ আলু আছে? মণের সংখ্যা চেপে হ্যাশ চাপুন, অথবা বলুন।",
    "cash_needed_tk": "সামনে কত টাকা দরকার? টাকার অঙ্ক চেপে হ্যাশ চাপুন। দরকার না থাকলে ০ চেপে হ্যাশ।",
    "deadline_days": "কত দিনের মধ্যে টাকাটা লাগবে? দিনের সংখ্যা চেপে হ্যাশ চাপুন।",
    "offer_per_kg": "পাইকার বা ফড়িয়া কেজিতে কত টাকা দিতে চায়? না জানলে ০ চেপে হ্যাশ।",
    "dadon_tk": "দাদন নেওয়া থাকলে কত টাকা? না থাকলে ০ চেপে হ্যাশ।",
}
CONFIRM_KEYS = "ঠিক হলে ১, ভুল হলে ২ চাপুন।"
NOT_UNDERSTOOD = "দুঃখিত, বুঝতে পারিনি।"
HELP = "দুঃখিত, আমি বুঝতে পারছি না। আবার চেষ্টা করতে ১ চাপুন। কৃষি কর্মকর্তা আপনাকে ফোন করবেন, এর জন্য ৯ চাপুন।"
CLOSING = "আবার শুনতে ১, কৃষি কর্মকর্তার ফোনের জন্য ৯ চাপুন।"
OFFICER = "ঠিক আছে। কৃষি কর্মকর্তা শিগগির আপনাকে ফোন করবেন। কৃষিভল্টে ফোন করার জন্য ধন্যবাদ।"
NOT_READY = {
    "fertilizer": "সার ও কীটনাশকের পরামর্শ এই নমুনায় এখনো চালু হয়নি। কর্মকর্তার ফোনের জন্য ৯, মূল মেনুতে ফিরতে ০ চাপুন।",
    "seeds": "বীজ ও যন্ত্রপাতির বাজার এই নমুনায় এখনো চালু হয়নি। কর্মকর্তার ফোনের জন্য ৯, মূল মেনুতে ফিরতে ০ চাপুন।",
}
ENDED = "কলটি শেষ হয়েছে। ধন্যবাদ।"

SCENARIO_BN = {
    "sell_now": "এখনই সব বেচা",
    "sell_part": "কিছু বেচে বাকিটা হিমাগারে রাখা",
    "store_review": "সব হিমাগারে রাখা",
    "group_sell": "দল বেঁধে বেচা",
}

REWORD_PROMPT = """Reword this phone advice for a potato farmer in Bogura, Bangladesh, in simple, warm,
spoken Bangla. Rules: keep every number exactly as written, in Bangla digits; do not add, drop, round
or calculate any number; do not add advice, pesticide names, loans or promises; at most four short
sentences. Return only the reworded Bangla text.

Advice: \"\"\"{text}\"\"\""""

MENU_KEYS = ["1", "2", "3", "9"]
SLOT_LABELS = {
    "quantity_kg": ("আলুর পরিমাণ", "Potato"),
    "cash_needed_tk": ("টাকার দরকার", "Cash needed"),
    "deadline_days": ("কত দিনে", "Within"),
    "offer_per_kg": ("পাইকারের দর", "Trader's offer"),
    "dadon_tk": ("দাদন", "Dadon"),
}
NO_DEADLINE_DAYS = 30  # used when no cash is needed, so the deadline does not matter


def new_state(district: str = "Bogura", month: Optional[int] = None, phone: Optional[str] = None) -> dict:
    return {
        "v": 1, "step": "menu", "asking": None, "slots": {}, "fails": 0,
        "district": district or "Bogura", "month": month, "phone": phone,
        "last_say": "", "advice_say": "", "advice_body": "", "done_say": "", "help_return": None,
        "decision": None, "action": None,
    }


def _value(slots: dict, slot: str, default: float = 0.0) -> float:
    return float(slots.get(slot, {}).get("value", default))


def _missing(slots: dict) -> Optional[str]:
    for slot in SLOTS:
        if slot == "deadline_days" and "cash_needed_tk" in slots and _value(slots, "cash_needed_tk") == 0:
            continue
        if slot not in slots:
            return slot
    return None


def _maunds(kg: float) -> float:
    return kg / MAUND_TO_KG


def _said_again(text: str) -> bool:
    return any(tok.startswith(nfc("আবার")) for tok in prepare(text).split())


# ------------------------------------------------------------------ reading values back
def quantity_phrase(slot: dict) -> str:
    kg = slot["value"]
    unit = slot.get("unit") or "maund"
    if unit == "sack":
        return f"{fmt_num(kg / SACK_KG)} বস্তা আলু, মানে প্রায় {fmt_num(_maunds(kg))} মণ"
    if unit == "kg":
        return f"{fmt_num(kg, 0)} কেজি আলু, মানে প্রায় {fmt_num(_maunds(kg))} মণ"
    return f"{fmt_num(_maunds(kg))} মণ আলু"


def readback(slots: dict) -> str:
    parts = [quantity_phrase(slots["quantity_kg"])]
    cash = _value(slots, "cash_needed_tk")
    if cash > 0:
        parts.append(f"{fmt_num(_value(slots, 'deadline_days'), 0)} দিনের মধ্যে {fmt_taka(cash, rounded=False)} টাকা দরকার")
    else:
        parts.append("এখন টাকার জরুরি দরকার নেই")
    offer = slots["offer_per_kg"]
    if offer["value"] > 0 and offer.get("unit") == "taka_per_maund":
        parts.append(f"পাইকারের দর মণে {fmt_num(offer['value'] * MAUND_TO_KG, 0)} টাকা, মানে কেজিতে {fmt_num(offer['value'])} টাকা")
    elif offer["value"] > 0:
        parts.append(f"পাইকারের দর কেজিতে {fmt_num(offer['value'])} টাকা")
    else:
        parts.append("পাইকারের দর জানা নেই")
    dadon = _value(slots, "dadon_tk")
    parts.append(f"দাদন {fmt_taka(dadon, rounded=False)} টাকা" if dadon > 0 else "দাদন নেই")
    return "আপনি বললেন: " + "। ".join(parts) + "। " + CONFIRM_KEYS


def slots_for_screen(slots: dict) -> list[dict]:
    rows = []
    for slot in SLOTS:
        label_bn, label_en = SLOT_LABELS[slot]
        s = slots.get(slot)
        if s is None:
            display = None
        elif slot == "quantity_kg":
            display = f"{fmt_num(_maunds(s['value']))} মণ ({fmt_num(s['value'], 0)} কেজি)"
        elif slot == "deadline_days":
            display = f"{fmt_num(s['value'], 0)} দিন"
        elif slot == "offer_per_kg":
            display = f"৳{fmt_num(s['value'])} / কেজি" if s["value"] > 0 else "জানা নেই"
        else:
            display = f"৳{fmt_taka(s['value'], rounded=False)}" if s["value"] > 0 else "নেই"
        rows.append({
            "slot": slot, "label_bn": label_bn, "label_en": label_en, "display": display,
            "value": None if s is None else s["value"],
            "source": None if s is None else s.get("source"),
            "heard": None if s is None else s.get("heard"),
        })
    return rows


# ------------------------------------------------------------------ the advice
def _alternative(output, rec) -> Optional[Any]:
    others = [s for s in output.scenarios if s.feasible and s.scenario != rec.scenario]
    return max(others, key=lambda s: s.expected_proceeds_tk) if others else None


def advice_text(output, ctx: dict) -> tuple[str, Optional[dict]]:
    """(the advice body with the engine's numbers, the action offered or None)."""
    rec = output.recommended
    q = ctx["quantity_maunds"]
    cash = ctx["cash"]
    dadon = ctx["dadon"]
    total = rec.expected_proceeds_tk
    storage = ctx.get("cold_storage")
    lines: list[str] = []
    action: Optional[dict] = None

    if rec.scenario == "sell_now":
        lines.append(f"পরামর্শ: এখনই সব {fmt_num(q)} মণ বিক্রি করুন।")
        price = fmt_num(rec.sell_price_per_kg)
        if ctx.get("network_buyer"):
            lines.append(f"আমাদের সহযোগী ক্রেতা কেজিতে {price} টাকা দিচ্ছে; গাড়িভাড়া বাদে হাতে আসবে প্রায় {fmt_taka(total)} টাকা।")
        else:
            lines.append(f"কেজিতে {price} টাকা দরে গাড়িভাড়া বাদে হাতে আসবে প্রায় {fmt_taka(total)} টাকা।")
        if cash > 0:
            lines.append(f"এতে আপনার {fmt_taka(cash, rounded=False)} টাকার দরকার মিটবে।" if total >= cash
                         else f"তবে এতে আপনার {fmt_taka(cash, rounded=False)} টাকার পুরোটা মিটবে না।")
        if dadon > 0:
            lines.append(f"দাদনের {fmt_taka(dadon, rounded=False)} টাকা শোধের পর থাকবে প্রায় {fmt_taka(total - dadon)} টাকা।"
                         if total >= dadon else f"এতে দাদনের {fmt_taka(dadon, rounded=False)} টাকা পুরো শোধ হবে না।")
        action = {"kind": "buyer_lot", "maunds": q,
                  "line": "আমাদের ক্রেতাদের কাছে আপনার আলুর খবর পাঠাতে ২ চাপুন।"}

    elif rec.scenario == "sell_part":
        sell_m = min(math.ceil(_maunds(rec.sell_quantity_kg)), math.floor(q))
        store_m = round(q - sell_m, 1)
        lines.append(f"পরামর্শ: এখন {fmt_num(sell_m)} মণ বিক্রি করুন, তাতে আপনার {fmt_taka(cash, rounded=False)} টাকার দরকার মিটবে।")
        lines.append(f"বাকি {fmt_num(store_m)} মণ হিমাগারে রাখুন।")
        lines.append(f"সব মিলিয়ে আনুমানিক {fmt_taka(total)} টাকা হতে পারে, তবে পরে দাম বাড়বেই এমন নিশ্চয়তা নেই।")
        ctx["sell_maunds"], ctx["store_maunds"] = sell_m, store_m
        if storage:
            action = {"kind": "cold_storage_booking", "maunds": store_m,
                      "line": f"হিমাগারে {fmt_num(store_m)} মণের জায়গার অনুরোধ পাঠাতে ২ চাপুন।"}

    elif rec.scenario == "store_review":
        lines.append(f"পরামর্শ: সব {fmt_num(q)} মণ হিমাগারে রাখুন।")
        lines.append(f"দাম কেজিতে {fmt_num(rec.break_even_price)} টাকার বেশি হলে তবেই রাখা লাভজনক।")
        lines.append(f"মৌসুমি হিসাবে এক মাস পরে দাম কেজিতে প্রায় {fmt_num(ctx['price_in_30d'])} টাকা হতে পারে, তবে নিশ্চয়তা নেই।")
        if storage:
            action = {"kind": "cold_storage_booking", "maunds": q,
                      "line": f"হিমাগারে {fmt_num(q)} মণের জায়গার অনুরোধ পাঠাতে ২ চাপুন।"}

    else:  # group_sell
        lines.append("পরামর্শ: আশেপাশের কৃষকদের সাথে মিলে একসাথে বড় ক্রেতার কাছে বিক্রি করুন।")
        lines.append(f"বাছাই আর গাড়িভাড়া বাদে কেজিতে পড়বে প্রায় {fmt_num(rec.sell_price_per_kg)} টাকা, মোট প্রায় {fmt_taka(total)} টাকা।")
        if dadon > 0 and total >= dadon:
            lines.append(f"দাদনের {fmt_taka(dadon, rounded=False)} টাকা শোধের পর থাকবে প্রায় {fmt_taka(total - dadon)} টাকা।")
        action = {"kind": "group_lot_join", "maunds": q,
                  "line": f"দলের বিক্রিতে আপনার {fmt_num(q)} মণ যোগ করতে ২ চাপুন।"}

    alt = _alternative(output, rec)
    if alt:
        lines.append(f"অন্য উপায়, {SCENARIO_BN[alt.scenario]}: প্রায় {fmt_taka(alt.expected_proceeds_tk)} টাকা।")
        if alt.expected_proceeds_tk > total and cash > 0 and ctx["deadline"] <= 3:
            # the engine's urgency rule chose quick cash over a larger but slower sum
            lines.append(f"কিন্তু আপনার {fmt_num(ctx['deadline'], 0)} দিনের মধ্যে টাকা লাগবে, তাই দ্রুত টাকা পাওয়ার এই উপায়টাই নিরাপদ।")
    return " ".join(lines), action


def receipt_sms(state: dict) -> Optional[str]:
    d = state.get("decision")
    if not d:
        return None
    short = {
        "sell_now": "এখনই সব বেচুন",
        "sell_part": f"এখন {fmt_num(d.get('sell_maunds') or 0)} মণ বেচুন, {fmt_num(d.get('store_maunds') or 0)} মণ হিমাগারে",
        "store_review": "সব হিমাগারে রাখুন",
        "group_sell": "দল বেঁধে বেচুন",
    }[d["scenario"]]
    text = f"কৃষিভল্ট: {fmt_num(d['quantity_maunds'])} মণ আলু। পরামর্শ: {short}। আনুমানিক {fmt_taka(d['total'])} টাকা।"
    action = state.get("action")
    if action:
        name = {"cold_storage_booking": "হিমাগার অনুরোধ", "buyer_lot": "ক্রেতার কাছে লট",
                "group_lot_join": "দলের লট"}[action["kind"]]
        text += f" {name} নং {to_bn_digits(action['ref'])} (ডেমো)।"
    return text


# ------------------------------------------------------------------ the state machine
class Conversation:
    def __init__(self, session_factory: Callable, gemini: Optional[GeminiClient] = None):
        self.session_factory = session_factory
        self.gemini = gemini

    # -- public -------------------------------------------------------------------------------
    def turn(self, state: Optional[dict], inp: dict) -> dict:
        kind = (inp or {}).get("kind", "start")
        if state is None or kind == "start":
            state = new_state(inp.get("district", "Bogura"), inp.get("month"), inp.get("phone"))
            return self._reply(state, f"{GREETING} {MENU}", "menu", MENU_KEYS)

        state = dict(state)
        if inp.get("phone"):
            state["phone"] = inp["phone"]
        if inp.get("month"):
            state["month"] = inp["month"]
        text = (inp.get("text") or "").strip()
        digits = (inp.get("digits") or "").strip()
        heard = None
        if kind == "speech":
            if not text:
                return self._fail(state, None)
            expecting = state.get("asking") if state["step"] == "sell_ask" else None
            heard = understand(text, expecting=expecting, asked_text=state.get("last_say", ""), gemini=self.gemini)
            heard["text"] = text

        handler = {
            "menu": self._menu,
            "not_ready": self._not_ready,
            "sell_ask": self._sell_ask,
            "sell_confirm": self._sell_confirm,
            "sell_advice": self._sell_advice,
            "sell_done": self._sell_done,
            "help": self._help,
            "ended": self._ended,
        }[state["step"]]
        reply = handler(state, kind, digits, heard)
        reply["heard"] = None if heard is None else {
            "text": text,
            "values": heard["values"],
            "rejected": heard["rejected"],
            "menu": heard["menu"],
            "yes_no": heard["yes_no"],
            "gemini": heard["gemini"],
        }
        return reply

    # -- replies ------------------------------------------------------------------------------
    def _reply(self, state: dict, say: str, expects: str, keys: list, **extra) -> dict:
        state["last_say"] = say
        out = {
            "state": state,
            "say": say,
            "expects": expects,   # "menu" / "choice": one key; "number": digits then #; "end"
            "keys": keys,
            "slots": slots_for_screen(state["slots"]),
            "decision": None,
            "narration": None,
            "event": None,
            "sms_text": receipt_sms(state),
            "done": expects == "end",
        }
        out.update(extra)
        return out

    def _prompt(self, state: dict) -> tuple[str, str, list]:
        """What to say to repeat the current step's question."""
        step = state["step"]
        if step == "sell_ask":
            return QUESTIONS[state["asking"]], "number", []
        if step == "sell_confirm":
            return readback(state["slots"]), "choice", ["1", "2"]
        if step == "sell_advice":
            return state["advice_say"], "choice", self._advice_keys(state)
        if step == "sell_done":
            return state["done_say"], "choice", ["1", "9"]
        if step == "not_ready":
            return state["last_say"], "choice", ["9", "0"]
        return MENU, "menu", MENU_KEYS

    def _fail(self, state: dict, _heard) -> dict:
        state["fails"] = state.get("fails", 0) + 1
        if state["fails"] >= 2 and state["step"] != "help":
            state["help_return"] = {"step": state["step"], "asking": state.get("asking")}
            state["step"] = "help"
            state["fails"] = 0
            return self._reply(state, HELP, "choice", ["1", "9"])
        if state["step"] == "help":
            return self._reply(state, HELP, "choice", ["1", "9"])
        say, expects, keys = self._prompt(state)
        return self._reply(state, f"{NOT_UNDERSTOOD} {say}", expects, keys)

    def _merge(self, state: dict, values: dict) -> None:
        """Take what the farmer said; a newer value replaces an older one (a correction)."""
        for slot, v in values.items():
            state["slots"][slot] = dict(v)

    # -- steps --------------------------------------------------------------------------------
    def _menu(self, state, kind, digits, heard):
        if kind == "keypad":
            choice = {"1": "sell", "2": "fertilizer", "3": "seeds", "9": "officer"}.get(digits[:1])
        else:
            choice = heard["menu"]
            # Selling numbers (maunds, taka, a trader's price) mean a selling call, even if the farmer
            # also mentions fertilizer ("মহাজনের সার বাবদ ২৫ হাজার লাগবে")
            if heard["values"] and choice != "officer":
                choice = "sell"
        if choice == "sell":
            if heard:
                self._merge(state, heard["values"])
            return self._next_question(state)
        if choice in NOT_READY:
            state["step"] = "not_ready"
            state["fails"] = 0
            return self._reply(state, NOT_READY[choice], "choice", ["9", "0"])
        if choice == "officer":
            return self._officer(state, "pressed 9 at the menu")
        return self._fail(state, heard)

    def _not_ready(self, state, kind, digits, heard):
        if kind == "keypad" and digits[:1] in ("0", "*"):
            state["step"] = "menu"
            state["fails"] = 0
            return self._reply(state, MENU, "menu", MENU_KEYS)
        state["step"] = "menu"
        return self._menu(state, kind, digits, heard)

    def _next_question(self, state):
        missing = _missing(state["slots"])
        state["fails"] = 0
        if missing:
            state["step"] = "sell_ask"
            state["asking"] = missing
            return self._reply(state, QUESTIONS[missing], "number", [])
        state["step"] = "sell_confirm"
        state["asking"] = None
        return self._reply(state, readback(state["slots"]), "choice", ["1", "2"])

    def _sell_ask(self, state, kind, digits, heard):
        slot = state["asking"]
        if kind == "keypad":
            if digits.startswith("*"):
                state["step"], state["asking"], state["fails"] = "menu", None, 0
                return self._reply(state, MENU, "menu", MENU_KEYS)
            number = digits.rstrip("#")
            if number.isdigit():
                ans = bare_answer(slot, float(number))
                if in_limits(slot, ans["value"]):
                    state["slots"][slot] = {**ans, "heard": f"{number}#", "source": "keypad"}
                    return self._next_question(state)
            return self._fail(state, heard)
        if heard["values"]:
            self._merge(state, heard["values"])
            return self._next_question(state)
        if heard["menu"] == "officer":
            return self._officer(state, "asked for an officer while answering questions")
        return self._fail(state, heard)

    def _sell_confirm(self, state, kind, digits, heard):
        if kind == "keypad":
            yes, no = digits[:1] == "1", digits[:1] == "2"
        else:
            if heard["values"]:  # "না, ৬০ মণ": take the correction and read back again
                self._merge(state, heard["values"])
                return self._next_question(state)
            yes, no = heard["yes_no"] is True, heard["yes_no"] is False
        if yes:
            return self._advise(state)
        if no:
            state["slots"] = {}
            reply = self._next_question(state)
            reply["say"] = "ঠিক আছে, আবার শুরু করি। " + reply["say"]
            state["last_say"] = reply["say"]
            return reply
        return self._fail(state, heard)

    def _advice_keys(self, state) -> list:
        return (["2"] if (state.get("decision") or {}).get("action") else []) + ["1", "9"]

    def _sell_advice(self, state, kind, digits, heard):
        decision = state.get("decision") or {}
        if kind == "keypad":
            key = digits[:1]
        elif heard["menu"] == "officer":
            key = "9"
        elif _said_again(heard["text"]):
            key = "1"
        elif heard["yes_no"] is True:
            key = "2"
        else:
            key = None
        if key == "2" and decision.get("action"):
            return self._act(state)
        if key == "1":
            return self._reply(state, state["advice_say"], "choice", self._advice_keys(state))
        if key == "9":
            return self._officer(state, "pressed 9 after the advice")
        return self._fail(state, heard)

    def _sell_done(self, state, kind, digits, heard):
        if kind == "keypad":
            key = digits[:1]
        else:
            key = "9" if heard["menu"] == "officer" else ("1" if _said_again(heard["text"]) else None)
        if key == "1":
            return self._reply(state, state["done_say"], "choice", ["1", "9"])
        if key == "9":
            return self._officer(state, "pressed 9 after the booking")
        state["step"] = "ended"
        return self._reply(state, ENDED, "end", [])

    def _help(self, state, kind, digits, heard):
        key = digits[:1] if kind == "keypad" else None
        if kind == "speech":
            key = "9" if heard["menu"] == "officer" else ("1" if heard["yes_no"] is True else None)
        if key == "9":
            return self._officer(state, "could not be understood twice")
        if key == "1":
            back = state.get("help_return") or {"step": "menu", "asking": None}
            state["step"], state["asking"], state["fails"] = back["step"], back["asking"], 0
            say, expects, keys = self._prompt(state)
            return self._reply(state, say, expects, keys)
        return self._fail(state, heard)

    def _ended(self, state, kind, digits, heard):
        return self._reply(state, ENDED, "end", [])

    # -- actions ------------------------------------------------------------------------------
    def _officer(self, state, reason: str) -> dict:
        details = {"reason": reason, "values": {s["slot"]: s["display"] for s in slots_for_screen(state["slots"]) if s["display"]}}
        event = events.record("officer_callback", "কৃষক কর্মকর্তার ফোন চেয়েছেন", details,
                              district=state.get("district", ""), phone=state.get("phone"))
        state["step"] = "ended"
        return self._reply(state, OFFICER, "end", [], event=event)

    def _act(self, state) -> dict:
        d = state["decision"]
        action = d["action"]
        q = fmt_num(action["maunds"])
        kind = action["kind"]
        summaries = {
            "cold_storage_booking": f"{q} মণ আলু রাখার অনুরোধ",
            "buyer_lot": f"{q} মণ আলু বিক্রির লট",
            "group_lot_join": f"দলের লটে {q} মণ আলু",
        }
        details = {
            "maunds": round(action["maunds"], 1),
            "scenario": d["scenario"],
            "expected_total_tk": round(d["total"]),
            "farmer_offer_per_kg": d["offer"],
        }
        if kind == "cold_storage_booking" and d.get("cold_storage"):
            details["cold_storage"] = d["cold_storage"]["name"]
            details["rate_per_kg"] = d["cold_storage"]["rate_per_kg"]
        event = events.record(kind, summaries[kind], details, district=state.get("district", ""), phone=state.get("phone"))
        state["action"] = {"kind": kind, "ref": event["ref"], "maunds": action["maunds"]}
        ref = to_bn_digits(event["ref"])
        say = {
            "cold_storage_booking": f"হিমাগারে {q} মণের জায়গার অনুরোধ পাঠানো হয়েছে। অনুরোধ নম্বর {ref}। হিমাগার আপনাকে ফোন করে তারিখ আর ভাড়া জানাবে।",
            "buyer_lot": f"আপনার {q} মণ আলুর খবর আমাদের ক্রেতাদের কাছে গেছে। নম্বর {ref}। ক্রেতার দর পেলে আমরা আপনাকে ফোন করে জানাব।",
            "group_lot_join": f"দলের বিক্রিতে আপনার {q} মণ যোগ হয়েছে। নম্বর {ref}। দল পুরো হলে ক্রেতার দর নিয়ে আমরা ফোন করব।",
        }[kind] + " রসিদ এসএমএসে যাবে। " + CLOSING
        state["done_say"] = say
        state["step"] = "sell_done"
        return self._reply(state, say, "choice", ["1", "9"], event=event)

    def _advise(self, state) -> dict:
        output, ctx, decision_screen = self.decide(state)
        body, action = advice_text(output, ctx)
        rewrite = None
        if self.gemini is not None and self.gemini.available:
            rewrite = lambda t: self.gemini.text(REWORD_PROMPT.format(text=t))  # noqa: E731
        narration = narrate(body, rewrite)
        say = narration["text"] + (" " + action["line"] if action else "") + " " + CLOSING
        state["decision"] = {
            "scenario": output.recommended.scenario,
            "total": output.recommended.expected_proceeds_tk,
            "quantity_maunds": ctx["quantity_maunds"],
            "sell_maunds": ctx.get("sell_maunds"),
            "store_maunds": ctx.get("store_maunds"),
            "offer": ctx["offer"],
            "cold_storage": ctx.get("cold_storage"),
            "action": action,
        }
        state["advice_say"] = say
        state["advice_body"] = narration["text"]
        state["step"] = "sell_advice"
        state["fails"] = 0
        narration_screen = {"status": narration["status"], "check": narration["check"],
                            "template": body, "rejected_text": narration.get("rejected_text"),
                            "model": getattr(self.gemini, "model_used", None)}
        return self._reply(state, say, "choice", self._advice_keys(state),
                           decision=decision_screen, narration=narration_screen)

    # -- the engine ---------------------------------------------------------------------------
    def decide(self, state: dict):
        slots = state["slots"]
        qty_kg = _value(slots, "quantity_kg")
        cash = _value(slots, "cash_needed_tk")
        deadline = int(_value(slots, "deadline_days", NO_DEADLINE_DAYS)) if cash > 0 else NO_DEADLINE_DAYS
        offer = _value(slots, "offer_per_kg")
        dadon = _value(slots, "dadon_tk")
        district = state.get("district") or "Bogura"

        session = self.session_factory()
        try:
            partners = partner_context(session, district)
        finally:
            session.close()

        price_today = offer if offer > 0 else partners.reference_price
        price_basis = "the farmer's trader offer" if offer > 0 else partners.reference_label
        market, outlook = seasonal_outlook(price_today, state.get("month"))
        storage = partners.cold_storage

        farmer = FarmerSituation(
            crop="potato",
            quantity_kg=qty_kg,
            district=district,
            cash_needed_tk=cash,
            deadline_days=deadline,
            current_offer_per_kg=offer,
            has_cold_storage=storage is not None,
            storage_cost_per_kg=(storage or {}).get("rate_per_kg") or FarmerSituation.storage_cost_per_kg,
            has_dadon=dadon > 0,
            dadon_amount_tk=dadon,
        )
        output = DecisionEngine().evaluate(farmer, market, partners.buyer_offers, partners.neighbours)
        rec = output.recommended

        network_buyer = (rec.scenario == "sell_now" and rec.sell_price_per_kg > price_today)
        ctx = {
            "quantity_maunds": round(_maunds(qty_kg), 1),
            "cash": cash, "deadline": deadline, "dadon": dadon, "offer": offer, "price_today": price_today,
            "price_in_30d": outlook["price_in_30d"], "cold_storage": storage,
            "network_buyer": network_buyer,
        }
        screen = {
            "recommended": rec.scenario,
            "recommended_bn": SCENARIO_BN[rec.scenario],
            "scenarios": [
                {
                    "scenario": s.scenario,
                    "name_bn": SCENARIO_BN[s.scenario],
                    "feasible": s.feasible,
                    "rank": s.rank,
                    "recommended": s is rec,
                    "expected_proceeds_tk": round(s.expected_proceeds_tk),
                    "sell_maunds": round(_maunds(s.sell_quantity_kg), 1),
                    "store_maunds": round(_maunds(s.store_quantity_kg), 1),
                    "price_per_kg": round(s.sell_price_per_kg, 2),
                    "explanation_en": s.explanation_en if s.feasible else s.infeasible_reason,
                    "risk": s.risk_level,
                }
                for s in output.scenarios
            ],
            "inputs": {
                "quantity_maunds": ctx["quantity_maunds"],
                "cash_needed_tk": cash,
                "deadline_days": deadline if cash > 0 else None,
                "dadon_tk": dadon,
                "price_today_per_kg": price_today,
                "price_basis": price_basis,
                "outlook": outlook,
                "cold_storage": storage,
                "demo_buyers": len(partners.buyer_offers),
                "demo_neighbours": len(partners.neighbours),
            },
        }
        return output, ctx, screen
