"""
Price-window alerts: step 4 of the plan's loop
==============================================
"When KrishiVault's AI detects an optimal price window, it alerts the farmer and connects them to
verified wholesalers and processors." For every receipt still in a cold storage, the engine is run
again for today (the potatoes are already stored, so the rent is owed either way):

- if it says **sell now** (or sell part now), the farmer gets an SMS with how many sacks to sell and the
  buyer that leaves the most money in hand; a sack held for a bank is sold through the bank, which is
  repaid first;
- otherwise the alert says **hold**, until which month, and the price at which holding stops paying.

Every number comes from the engine and the buyer ranking. SMS stays a dry run unless SMS_LIVE=1.
"""

from __future__ import annotations

from typing import Optional

from src import contacts
from src.engine import market_access, receipts
from src.engine.facts import MONTHS_EN
from src.engine.storage_plan import FarmerLot, StoragePlanner
from src.voice.bangla_numbers import fmt_num, fmt_taka

_planner = StoragePlanner()


def _alert_sms(r: dict, sell: int, plan: dict, buyer: Optional[dict]) -> str:
    if sell:
        text = (f"কৃষিভল্ট: রসিদ {r['no']}। এখন দাম ভালো: {fmt_num(sell, 0)} বস্তা বেচুন")
        text += (f"; সবচেয়ে বেশি হাতে আসবে {buyer['name_bn']}-এর কাছে, প্রায় {fmt_taka(buyer['money_total'])} টাকা।"
                 if buyer else "।")
        if r.get("hold"):
            text += " ব্যাংকের ঋণ আগে শোধ হবে।"
        return text + " (ডেমো)"
    best = plan["best_month"]
    return (f"কৃষিভল্ট: রসিদ {r['no']}। এখনই বেচবেন না: {best['month_bn']} পর্যন্ত রাখলে গড়ে বেশি পাওয়ার সম্ভাবনা। "
            f"দাম বদলালে আবার জানাব। (ডেমো)")


def price_window(month: int, year: int, price_today: float) -> list[dict]:
    """One alert per receipt still in store: sell now (how many, to whom) or hold (until when)."""
    out = []
    for r in receipts.all_receipts():
        if r["status"].startswith("sold"):
            continue
        lot = FarmerLot(quantity_kg=r["kg"], price_today=price_today, decision_month=month, decision_year=year,
                        stored="cold", stored_since_month=r.get("stored_month", 3), district=r["district"])
        plan = _planner.plan(lot)
        rec = plan["recommendation"]
        chosen = plan["options"].get(rec["key"]) or plan["options"]["sell_now"]
        sell = r["sacks"] if rec["key"] == "sell_now" else chosen.get("sell_sacks_now", 0)
        if rec["key"] == "store":
            sell = 0
        buyer = None
        if sell:
            offers = market_access.compare_offers(sell * r["kg"] / r["sacks"], price_today)
            best = offers["best"]
            if best:
                buyer = {"id": best["id"], "name": best["name"], "name_bn": _buyer_bn(best),
                         "money_total": best["money_total"], "demo": best["demo"]}
        out.append({
            "receipt": r["no"], "farmer": r["farmer"], "phone": r["phone"], "sacks": r["sacks"],
            "action": "sell" if sell else "hold", "sell_sacks": sell,
            "advice": rec["title_en"], "advice_bn": rec["title_bn"],
            "hold_until": None if sell else plan["best_month"]["month_en"] if plan["best_month"] else None,
            "buyer": buyer, "held_for_bank": bool(r.get("hold")),
            "months_left": plan["months_left"], "when": f"{MONTHS_EN[month]} {year}",
            "sms": _alert_sms(r, sell, plan, buyer),
        })
    return out


def send(alerts: list[dict], send_sms) -> list[dict]:
    """Send each alert by SMS to the number the farmer gave at the cold storage (dry run unless SMS_LIVE=1)."""
    for a in alerts:
        phone = contacts.get(f"receipt:{a['receipt']}")
        a["sms_result"] = send_sms(phone, a["sms"]) if phone else {"error": "no phone number on the receipt"}
    return alerts


def _buyer_bn(offer: dict) -> str:
    return {"b-haat": "হাটের ব্যাপারী", "b-retail": "স্থানীয় দোকান", "b-wholesale": "ডেমো পাইকার এ",
            "b-processor": "ডেমো চিপস কারখানা বি", "b-supermarket": "ডেমো সুপারমার্কেট সি",
            "b-exporter": "ডেমো রপ্তানিকারক ডি"}.get(offer["id"], offer["name"])
