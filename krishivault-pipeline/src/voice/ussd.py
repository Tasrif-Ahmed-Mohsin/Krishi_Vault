"""
USSD: the plan's text menu for any phone
========================================
The plan's step 1: the farmer dials a Grameenphone USSD code (or calls the voice line) and gives two
numbers, **sacks harvested** and **cash needed now**; KrishiVault answers with the split, using the
pre-loaded local price and cost benchmarks.

USSD gateways send the whole session's input on every turn ("1*36*25000"), and expect "CON <screen>"
to keep the session open or "END <screen>" to close it. This handler works that way, so it can sit
behind an aggregator's USSD gateway unchanged. Every number on a screen comes from the engine.

Screens are kept short: a Bangla (Unicode) USSD screen holds far fewer characters than an English one;
the exact limit must be confirmed with Grameenphone. In the prototype there is no USSD code: the
preview at /ussd plays the menus in the browser.
"""

from __future__ import annotations

from typing import Optional

from src import events
from src.engine import farmer_signals, financing, group_storage
from src.engine.facts import SACK_KG
from src.engine.storage_plan import FarmerLot, StoragePlanner
from src.models.price_outlook import outlook
from src.voice.bangla_numbers import fmt_num, fmt_taka, to_bn_digits, to_en_digits

MENU = "কৃষিভল্ট (ডেমো)\n1 রাখব না বেচব\n2 দামের পূর্বাভাস\n3 বস্তা জামানতে ঋণ\n4 দলে রাখা ও বেচা"
ASK_SACKS = "কত বস্তা আলু? (৮৪ কেজির বস্তা)"
ASK_CASH = "এখনই কত টাকা দরকার? না লাগলে 0"
ASK_PRICE = "আজ কেজিতে কত টাকা পাচ্ছেন? না জানলে 0"
BAD = "বুঝতে পারিনি। আবার ডায়াল করুন।"
CASH_DAYS = 7          # "immediate cash": within a week

_planner = StoragePlanner()


def _con(text: str) -> dict:
    return {"response": "CON " + text, "screen": text, "end": False}


def _end(text: str) -> dict:
    return {"response": "END " + text, "screen": text, "end": True}


def local_price(month: int) -> float:
    """The pre-loaded local farm-gate price when the farmer is not asked for one (demo: the usual season)."""
    from src.voice.conversation import demo_price
    return demo_price(month)


def _number(part: str, lo: float, hi: float) -> Optional[float]:
    part = to_en_digits(part or "").strip()
    if not part.isdigit():
        return None
    v = float(part)
    return v if lo <= v <= hi else None


def _advice(sacks: int, cash: float, month: int, year: int, district: str) -> tuple[dict, FarmerLot]:
    lot = FarmerLot(quantity_kg=sacks * SACK_KG, price_today=local_price(month), decision_month=month,
                    decision_year=year, cash_needed_tk=cash, cash_days=CASH_DAYS if cash else 0, district=district)
    return _planner.plan(lot), lot


def _advice_screen(plan: dict) -> str:
    rec, opts, p = plan["recommendation"], plan["options"], plan["net_profit"]
    chosen = opts.get(rec["key"]) or opts["sell_now"]
    if rec["key"] == "sell_now":
        head = f"সব {fmt_num(chosen['sell_sacks_now'], 0)} বস্তা এখন বেচুন।"
    else:
        head = (f"এখন {fmt_num(chosen['sell_sacks_now'], 0)} বস্তা বেচুন, {fmt_num(chosen['store_sacks'], 0)} বস্তা "
                f"রেখে {chosen['sell_month_bn']} মাসে।")
    profit = (f"লাভ গড়ে {fmt_taka(p['with_advice'])} (এখন সব বেচলে {fmt_taka(p['sell_all_now'])})"
              if rec["key"] != "sell_now" else f"লাভ {fmt_taka(p['sell_all_now'])}")
    return (f"{head} {profit}। দাম কেজি {fmt_num(plan['inputs']['price_today'])} ধরে।\n"
            f"1 এসএমএসে বিস্তারিত\n2 হিমাগারে জায়গা\n8 নাম ছাড়া গুনুন")


def turn(text: str, phone: Optional[str] = None, month: int = 3, year: int = 2027, district: str = "Bogura",
         send_sms=None) -> dict:
    """One USSD turn. `text` is everything entered in this session, joined by '*' (the gateway's format)."""
    parts = [p for p in (text or "").split("*")] if text else []
    if not parts:
        return _con(MENU)
    choice, rest = parts[0], parts[1:]

    if choice == "1":                                     # store or sell: two numbers
        if not rest:
            return _con(ASK_SACKS)
        sacks = _number(rest[0], 1, 100_000)
        if sacks is None:
            return _end(BAD)
        if len(rest) == 1:
            return _con(ASK_CASH)
        cash = _number(rest[1], 0, 10_000_000)
        if cash is None:
            return _end(BAD)
        plan, lot = _advice(int(sacks), cash, month, year, district)
        if len(rest) == 2:
            return _con(_advice_screen(plan))
        action = rest[2]
        if action == "1":
            from src.voice.conversation import advice_sms
            sms = advice_sms(plan)
            sent = send_sms(phone, sms) if (send_sms and phone) else None
            return {**_end("বিস্তারিত এসএমএসে পাঠানো হলো। ধন্যবাদ।"), "sms_text": sms, "sms_result": sent}
        if action == "2":
            rec = plan["recommendation"]
            store = (plan["options"].get(rec["key"]) or {}).get("store_sacks") or lot.sacks
            ev = events.record("cold_storage_booking", f"{store} বস্তা আলু রাখার অনুরোধ (ইউএসএসডি)",
                               {"sacks": store, "advice": rec["title_en"], "channel": "ussd"},
                               district=district, phone=phone)
            return _end(f"{fmt_num(store, 0)} বস্তার জায়গা চাওয়া হলো, নম্বর {to_bn_digits(ev['ref'])}। "
                        f"হিমাগার ফোন করবে।")
        if action == "8":
            farmer_signals.record(district, month, year, lot.sacks, lot.cash_needed_tk, lot.cash_days, "no",
                                  plan["recommendation"]["key"], "ussd")
            return _end("ধন্যবাদ। নাম ও নম্বর ছাড়া জেলার হিসাবে গোনা হলো।")
        return _end(BAD)

    if choice == "2":                                     # price outlook
        if not rest:
            return _con(ASK_PRICE)
        price = _number(rest[0], 0, 200)
        if price is None:
            return _end(BAD)
        price = price or local_price(month)
        o = outlook(price, month, year, horizon=max(0, 12 - month))
        last = o["months"][-1]
        return _end(f"{last['month_bn']} মাসে দাম কেজি {fmt_num(last['low'], 0)}-{fmt_num(last['high'], 0)} টাকা হতে "
                    f"পারে (১০ বারে ৮ বার)। আজ {fmt_num(price)}। নিশ্চিত নয়।")

    if choice == "3":                                     # a loan against stored sacks
        if not rest:
            return _con("হিমাগারে কত বস্তা?")
        sacks = _number(rest[0], 1, 100_000)
        if sacks is None:
            return _end(BAD)
        price = local_price(month)
        months = max(1, 12 - month) if month != 12 else 1
        rows = financing.compare_banks(int(sacks), price, month, year, min(months, 9))
        banks = [r for r in rows if r["bank"]["id"] != "cold-storage-advance" and not r["problems"] and r["max_loan"] > 0]
        if not banks:
            return _end("ডেমো ব্যাংকের ঋণ মিলছে না; হিমাগারের অগ্রিম দেখুন। সহকারী ফোন করবেন।")
        best = min(banks, key=lambda r: r["bank"]["rate_year"])
        from src import demo_data
        name = demo_data.bank(best["bank"]["id"])["name_bn"]
        return _end(f"{name} সর্বোচ্চ প্রায় {fmt_taka(best['max_loan'])} টাকা দিতে পারে, সুদ প্রায় "
                    f"{fmt_taka(best['interest'])}। হিমাগারের রসিদ নম্বর লাগবে। (ডেমো)")

    if choice == "4":                                     # group storage and group selling
        pools = group_storage.pools(district)
        if not pools:
            return _end("আপনার জেলায় এখনো দল নেই। সহকারী ফোন করবেন।")
        pool = pools[0]
        if not rest:
            sale = group_storage.group_sale(pool["id"], local_price(month))
            name = group_storage._pool(pool["id"]).get("name_bn") or pool["name"]
            return _con(f"{name}: {fmt_num(pool['total_sacks'], 0)} বস্তা। দলে বেচলে বস্তায় প্রায় "
                        f"{fmt_taka(sale['gain_per_sack'], rounded=False)} টাকা বেশি।\nকত বস্তা যোগ করবেন?")
        sacks = _number(rest[0], 1, 100_000)
        if sacks is None:
            return _end(BAD)
        joined = group_storage.join(pool["id"], "USSD caller", int(sacks), phone)
        return _end(f"দলে যোগ হলো, নম্বর {to_bn_digits(joined['ref'])}। দলে এখন "
                    f"{fmt_num(joined['pool']['total_sacks'], 0)} বস্তা। (ডেমো)")

    return _end(BAD)
