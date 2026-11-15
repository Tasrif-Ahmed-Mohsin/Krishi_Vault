"""
The hold plan: a promise to keep against selling in fear
========================================================
The field notes: farmers who store "tend to sell within 1 to 3 months, afraid the price will fall
further"; they have paid the full season's rent and sell before the price has risen. The storage
engine already knows, for every month, whether selling then beats selling at the harvest on average,
and the price above which it does ("pays above"). The hold plan turns that into three things a farmer
can keep on a slip of paper or an SMS:

- the month to sell (the advice);
- "do not sell before" the first month in which storing pays on average;
- if cash forces an earlier sale: the price per kg that makes it still worth it, month by month.

The price-window alerts re-check every month with the real price. The checkpoints are the engine's
break-even prices, not a forecast: they say what must happen for storing to have paid.
"""

from __future__ import annotations

from typing import Optional

from src.voice.bangla_numbers import fmt_num

MAX_CHECKPOINTS = 3      # an SMS a farmer can read: three months, not nine


def build(plan: dict) -> Optional[dict]:
    """The hold plan for the sacks the advice stores; None when the advice is to sell everything now."""
    rec = plan["recommendation"]
    chosen = plan["options"].get(rec["key"])
    if rec["key"] == "sell_now" or not chosen or not chosen.get("store_sacks"):
        return None
    sell_h = chosen.get("months") or (plan["best_month"] or {}).get("h")
    months = [m for m in plan["by_month"] if m["h"] >= 1 and (sell_h is None or m["h"] <= sell_h)]
    if not months:
        return None
    sell = next((m for m in months if m["h"] == sell_h), months[-1])
    first_pay = next((m for m in months if m["gain_vs_now"] >= 0), sell)
    losing = [m for m in months if m["h"] < first_pay["h"]]
    early = [m for m in months if first_pay["h"] <= m["h"] < sell["h"] and m.get("break_even_price")]
    step = max(1, -(-len(early) // MAX_CHECKPOINTS))                    # spread the checkpoints out
    checkpoints = [{"month_en": m["month_en"], "month_bn": m["month_bn"], "h": m["h"],
                    "sell_only_above": round(m["break_even_price"], 1), "price_mid": m["price_mid"]}
                   for m in early[::step][:MAX_CHECKPOINTS]]
    out = {
        "sacks": chosen["store_sacks"], "sell_month_en": sell["month_en"], "sell_month_bn": sell["month_bn"],
        "not_before_en": first_pay["month_en"], "not_before_bn": first_pay["month_bn"],
        "losing_months": [{"month_en": m["month_en"], "gain_vs_now": m["gain_vs_now"]} for m in losing],
        "checkpoints": checkpoints,
        "bad_case_vs_now": chosen.get("worst_case_vs_now"),
        "note": ("The checkpoints are the engine's break-even prices: above them, selling that month still beats "
                 "selling at the harvest after rent, weight loss and costs. KrishiVault re-checks every month with "
                 "the real price (price-window SMS)."),
    }
    out["sms"] = sms(out)
    return out


def sms(h: dict) -> str:
    """The hold plan as one SMS (Bangla digits; the numbers from the plan)."""
    text = f"কৃষিভল্ট পরিকল্পনা: {fmt_num(h['sacks'], 0)} বস্তা {h['sell_month_bn']} মাসে বেচুন।"
    if h["losing_months"]:
        text += f" {h['not_before_bn']} মাসের আগে বেচবেন না: গড়ে লোকসান।"
    if h["checkpoints"]:
        prices = ", ".join(f"{c['month_bn']} {fmt_num(c['sell_only_above'])}" for c in h["checkpoints"])
        text += f" আগে বেচতে হলে কেজির দর অন্তত: {prices} টাকা।"
    return text + " প্রতি মাসে দর জানাব। নিশ্চিত নয়।"
