"""
What a trader's advance (dadon) really costs
============================================
The plan's first ground-level challenge: before the harvest a faria or bepari lends the farmer cash
(dadon) and is repaid in potatoes at harvest, at a price below the market. No interest is named, so
the farmer never sees the cost. This works it out:

    hidden cost  = (market price - trader's price) x kg promised    (+ any fee or interest on top)
    rate         = cost / advance, for the months it was held; a year's rate = rate x 12 / months

and puts it beside the same amount from a bank against stored sacks (demo bank) and from the cold
storage's own advance. Pure arithmetic: no forecast. KrishiVault does not lend: the bank decides.
"""

from __future__ import annotations

from src import demo_data
from src.engine.facts import MAUND_KG, StorageTerms
from src.voice.bangla_numbers import fmt_num, fmt_taka

NOTE = ("A bank loan against the sacks comes only once they are in a partner cold storage, and a trader may "
        "want potatoes, not cash. This shows what the advance costs, so the farmer can bargain, repay in cash "
        "from a cheaper loan, or promise fewer sacks next time. Demo bank.")


def true_cost(advance_tk: float, months: float, promised_kg: float, trader_price: float, market_price: float,
              extra_tk: float = 0.0, bank_id: str = "bank-a") -> dict:
    """The advance's cost in taka and as a yearly rate, beside a bank loan and a cold-storage advance."""
    if advance_tk <= 0 or months <= 0 or promised_kg <= 0:
        raise ValueError("advance, months and the potatoes promised must be more than 0")
    discount = max(market_price - trader_price, 0.0)
    hidden = discount * promised_kg
    cost = hidden + max(extra_tk, 0.0)
    yearly = cost / advance_tk * 12 / months

    terms = StorageTerms()
    bank = demo_data.bank(bank_id)
    bank_cost = advance_tk * bank["rate_year"] * months / 12 + advance_tk * bank["processing_fee_pct"] / 100
    sacks_needed = -(-advance_tk // terms.cs_advance_per_sack)          # ceiling: the advance is per sack
    cs_cost = advance_tk * terms.cs_advance_rate_year * months / 12
    return {
        "advance": round(advance_tk), "months": months, "promised_kg": round(promised_kg),
        "promised_maunds": round(promised_kg / MAUND_KG, 1),
        "trader_price": trader_price, "market_price": market_price,
        "discount_per_kg": round(discount, 2), "hidden_cost": round(hidden), "extra": round(max(extra_tk, 0.0)),
        "cost": round(cost), "rate_period": round(cost / advance_tk, 4), "rate_year": round(yearly, 4),
        "bank": {"name": bank["name"], "rate_year": bank["rate_year"], "fee_pct": bank["processing_fee_pct"],
                 "cost": round(bank_cost), "demo": True},
        "cold_storage": {"rate_year": terms.cs_advance_rate_year, "per_sack": terms.cs_advance_per_sack,
                         "sacks_needed": int(sacks_needed), "cost": round(cs_cost)},
        "saving_with_bank": round(cost - bank_cost),
        "say_bn": say_bn(advance_tk, months, promised_kg, trader_price, market_price, cost, yearly, bank_cost),
        "note": NOTE,
    }


def say_bn(advance: float, months: float, kg: float, trader: float, market: float, cost: float, yearly: float,
           bank_cost: float) -> str:
    """The same in plain Bangla, every number from the sums above."""
    if cost <= 0:
        return (f"ফড়িয়ার {fmt_taka(advance, rounded=False)} টাকা দাদনে লুকানো খরচ নেই: বাজারের দামের চেয়ে কম "
                f"দামে দিতে হচ্ছে না।")
    return (f"ফড়িয়ার {fmt_taka(advance, rounded=False)} টাকা দাদনের জন্য {fmt_num(kg / MAUND_KG, 0)} মণ আলু "
            f"কেজিতে {fmt_num(trader)} টাকায় দিতে হলে, বাজারের {fmt_num(market)} টাকার চেয়ে প্রায় "
            f"{fmt_taka(cost)} টাকা কম পাবেন। {fmt_num(months, 0)} মাসের জন্য এটা বছরে প্রায় "
            f"{fmt_num(round(yearly * 100), 0)} শতাংশ সুদের সমান। একই টাকা হিমাগারের বস্তা জামানতে ব্যাংক থেকে নিলে "
            f"খরচ প্রায় {fmt_taka(bank_cost)} টাকা।")
