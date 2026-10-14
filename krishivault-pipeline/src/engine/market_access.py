"""
Market access: compare buyers' offers by the money left in the farmer's hand
============================================================================
A higher quoted price is not always a better deal. For each buyer we count:
- the price (today's local price plus the buyer's premium, or a price the farmer enters),
- the farmer's transport, any commission,
- the share the buyer rejects at grading (sold back at the haat for less),
- the wait for payment (money later is worth less: interest at the bank's rate),
- the buyer's minimum and maximum: below the minimum, a group lot is needed.

**No paid placement:** offers are ranked only by the money in the farmer's
hand. A partner's fee to KrishiVault never changes the order.
"""

from __future__ import annotations

from typing import Optional

from src.demo_data import partners

REJECT_PRICE_SHARE = 0.7   # rejected potatoes sell at the haat for about 70% of the price


def _offer_value(quantity_kg: float, price_today: float, b: dict, rate_year: float) -> dict:
    price = b.get("price_per_kg") or (price_today + b.get("price_premium_per_kg", 0.0))
    min_kg, max_kg = b.get("min_kg") or 0, b.get("max_kg")
    if quantity_kg < min_kg:
        return {"eligible": False, "price_per_kg": round(price, 2),
                "why_not": f"needs at least {min_kg:,.0f} kg: join a group lot"}
    to_buyer = min(quantity_kg, max_kg) if max_kg else quantity_kg
    rest = quantity_kg - to_buyer
    accepted = to_buyer * (1 - b.get("reject_pct", 0.0))
    rejected = to_buyer - accepted
    money = (accepted * price * (1 - b.get("commission_pct", 0.0) / 100)
             + rejected * price_today * REJECT_PRICE_SHARE
             - to_buyer * b.get("farmer_transport_per_kg", 0.0))
    wait_cost = money * rate_year * b.get("payment_days", 0) / 365
    rest_money = rest * (price_today - 0.3)     # the rest goes to the haat trader
    total = money - wait_cost + rest_money
    return {
        "eligible": True, "price_per_kg": round(price, 2), "kg_to_buyer": round(to_buyer),
        "kg_rest_at_haat": round(rest), "rejected_kg": round(rejected),
        "wait_cost": round(wait_cost), "money_total": round(total),
        "net_per_kg": round(total / quantity_kg, 2) if quantity_kg else 0.0,
    }


def compare_offers(quantity_kg: float, price_today: float, extra_offers: Optional[list[dict]] = None,
                   rate_year: float = 0.11) -> dict:
    """All offers for one lot, best first. extra_offers: [{name, price_per_kg, farmer_transport_per_kg, payment_days}]."""
    buyers = [dict(b) for b in partners()["buyers"]]
    for i, o in enumerate(extra_offers or []):
        buyers.append({"id": f"own-{i + 1}", "name": o.get("name") or f"Offer {i + 1}", "type": "own offer",
                       "demo": False, "price_per_kg": float(o["price_per_kg"]),
                       "farmer_transport_per_kg": float(o.get("farmer_transport_per_kg") or 0),
                       "payment_days": int(o.get("payment_days") or 0), "reject_pct": 0.0, "min_kg": 0,
                       "max_kg": None, "conditions": "Entered by the farmer"})
    rows = []
    for b in buyers:
        v = _offer_value(quantity_kg, price_today, b, rate_year)
        rows.append({"id": b["id"], "name": b["name"], "type": b["type"], "demo": b.get("demo", True),
                     "conditions": b.get("conditions", ""), "payment_days": b.get("payment_days", 0), **v})
    eligible = sorted((r for r in rows if r["eligible"]), key=lambda r: -r["money_total"])
    others = [r for r in rows if not r["eligible"]]
    base = next((r for r in eligible if r["id"] == "b-haat"), None)
    for r in eligible:
        r["more_than_haat"] = r["money_total"] - base["money_total"] if base else None
    best = eligible[0] if eligible else None
    return {
        "quantity_kg": round(quantity_kg), "price_today": price_today,
        "ranking_rule": "Money in the farmer's hand after transport, grading losses and the wait for payment. "
                        "Partner fees never change the order.",
        "offers": eligible + others, "best": best,
        "highest_quote": max(rows, key=lambda r: r["price_per_kg"]) if rows else None,
    }
