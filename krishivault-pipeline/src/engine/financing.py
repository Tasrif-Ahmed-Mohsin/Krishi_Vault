"""
Crop-backed financing: a loan against potatoes in cold storage
==============================================================
KrishiVault does not lend money. It gives the bank what it needs to decide,
and helps the farmer apply:

1. **Proof the potatoes are there:** the cold storage confirms the receipt
   (number of sacks) on its KrishiVault screen.
2. **What they are worth:** the sacks' weight after storage loss, valued at a
   careful price: the lower of today's price and the low end of the outlook
   (1 path in 10 is lower) when the loan ends.
3. **Who is paid first:** the cold storage holds the sacks, so its rent and any
   advance it gave come off first.
4. **Repayment risk:** the chance, over 2,000 simulated price paths, that the
   potatoes are worth less than the loan plus interest when it ends.

The bank sets its own loan share (loan-to-value) and rate and decides; the
figures here are for the bank's review, subject to its rules and the law.
"""

from __future__ import annotations

import math
import uuid
from typing import Optional

import numpy as np

from src import demo_data, events
from src.engine.facts import StorageTerms, MONTHS_EN, month_after
from src.models.price_outlook import rise_strength, simulate, season_for_decision


def _band(p: float) -> str:
    return "Low" if p < 0.03 else "Medium" if p < 0.10 else "High"


def loan_estimate(sacks: int, price_today: float, decision_month: int, decision_year: int, months: int,
                  bank_id: str = "bank-a", amount: Optional[float] = None, rent_due: bool = True,
                  cs_advance_taken_per_sack: float = 0.0, terms: Optional[StorageTerms] = None,
                  gap_override_pct: Optional[float] = None) -> dict:
    t = terms or StorageTerms()
    b = demo_data.bank(bank_id)
    months = max(1, min(int(months), b["max_months"]))
    kg = sacks * t.sack_kg
    season = season_for_decision(decision_year, decision_month)
    rs = rise_strength(season, gap_override_pct=gap_override_pct, decision_year=decision_year,
                       decision_month=decision_month)
    paths = simulate(decision_month, months, rs["k"], rs["k_sd"]) * price_today
    end_prices = paths[:, months]
    kept_kg = kg * (1 - t.monthly_weight_loss) ** months * (1 - t.exit_sorting_loss)
    careful_price = min(price_today, float(np.percentile(end_prices, 10)))
    claims = sacks * ((t.rent_per_sack if rent_due else 0) + cs_advance_taken_per_sack + t.sell_from_store_per_sack)
    collateral = kept_kg * careful_price - claims
    max_loan = max(0.0, math.floor(b["ltv"] * collateral / 100) * 100)
    principal = float(amount) if amount else max_loan
    interest = principal * b["rate_year"] * months / 12
    fee = principal * b["processing_fee_pct"] / 100
    repay = principal + interest
    value_at_end = kept_kg * end_prices - claims
    shortfall = float((value_at_end < repay).mean()) if principal > 0 else 0.0
    mid_price = float(np.median(end_prices))
    sack_net = t.sack_kg * (1 - t.monthly_weight_loss) ** months * (1 - t.exit_sorting_loss) * mid_price \
        - (t.rent_per_sack if rent_due else 0) - t.sell_from_store_per_sack
    sacks_to_repay = math.ceil(repay / sack_net) if sack_net > 0 else None
    end_month = month_after(decision_month, months)
    problems = []
    if sacks < b["min_sacks"]:
        problems.append(f"{b['name']} lends from {b['min_sacks']} sacks; join a group or try another lender.")
    if principal > max_loan:
        problems.append(f"Asked ৳{principal:,.0f}, above the most this crop supports (৳{max_loan:,.0f}).")
    return {
        "bank": {"id": b["id"], "name": b["name"], "ltv": b["ltv"], "rate_year": b["rate_year"],
                 "processing_fee_pct": b["processing_fee_pct"], "needs": b["needs"], "demo": True},
        "crop": {"sacks": sacks, "kg": round(kg), "kg_at_end": round(kept_kg), "price_today": price_today,
                 "value_today": round(kg * price_today), "season": rs.get("season", f"{season}-{str(season + 1)[-2:]}")},
        "months": months, "ends": MONTHS_EN[end_month],
        "careful_price": round(careful_price, 2),
        "price_at_end": {"low": round(float(np.percentile(end_prices, 10)), 2), "mid": round(mid_price, 2),
                         "high": round(float(np.percentile(end_prices, 90)), 2)},
        "paid_first_to_cold_storage": round(claims),
        "collateral_value": round(collateral),
        "max_loan": round(max_loan),
        "loan": round(principal), "interest": round(interest), "fee": round(fee), "repay": round(repay),
        "chance_crop_worth_less_than_repayment": round(shortfall, 3),
        "risk": _band(shortfall),
        "cover": round(float(np.median(value_at_end)) / repay, 2) if repay else None,
        "sacks_to_repay": sacks_to_repay, "repay_month": end_month,
        "repayment_plan": (f"Sell about {sacks_to_repay} of {sacks} sacks in {MONTHS_EN[end_month]} to repay"
                           if sacks_to_repay else "The crop does not cover the loan"),
        "problems": problems,
    }


def compare_banks(sacks: int, price_today: float, decision_month: int, decision_year: int, months: int,
                  amount: Optional[float] = None, **kw) -> list[dict]:
    rows = []
    for b in demo_data.partners()["banks"]:
        e = loan_estimate(sacks, price_today, decision_month, decision_year, months, b["id"], amount, **kw)
        rows.append(e)
    # cold storage's own advance, for comparison
    t = kw.get("terms") or StorageTerms()
    adv = sacks * t.cs_advance_per_sack
    rows.append({"bank": {"id": "cold-storage-advance", "name": "Cold-storage advance", "ltv": None,
                          "rate_year": t.cs_advance_rate_year, "demo": False,
                          "needs": ["Sacks in that cold storage"]},
                 "max_loan": round(adv), "loan": round(min(amount or adv, adv)),
                 "interest": round(min(amount or adv, adv) * t.cs_advance_rate_year * months / 12),
                 "risk": None, "problems": [] if not amount or amount <= adv else
                 [f"Only ৳{t.cs_advance_per_sack:,.0f} a sack (৳{adv:,.0f} for {sacks} sacks)"]})
    return sorted(rows, key=lambda r: (len(r["problems"]) > 0, r["bank"]["rate_year"]))


# ------------------------------------------------------------- applications

STATUS = ["waiting for the cold storage to confirm the receipt", "receipt confirmed, with the bank",
          "approved by the bank (demo)", "declined by the bank (demo)"]


def apply(farmer_name: str, phone: Optional[str], district: str, cold_storage_id: str, receipt_no: str,
          sacks: int, price_today: float, decision_month: int, decision_year: int, months: int,
          bank_id: str, amount: Optional[float] = None) -> dict:
    est = loan_estimate(sacks, price_today, decision_month, decision_year, months, bank_id, amount)
    cs = demo_data.cold_storage(cold_storage_id)
    app_id = uuid.uuid4().hex[:8]
    event = events.record("loan_application", f"{sacks} বস্তা জামানতে ঋণের আবেদন, রসিদ {receipt_no}",
                          {"application": app_id, "bank": est["bank"]["name"], "loan": est["loan"]},
                          district=district, phone=phone)
    return demo_data.append("loan_applications", {
        "id": app_id, "ref": event["ref"], "farmer": farmer_name, "phone": events.mask_phone(phone),
        "district": district, "cold_storage": {"id": cs["id"], "name": cs["name"]},
        "receipt_no": receipt_no, "sacks": sacks, "status": STATUS[0], "estimate": est, "demo": True,
    })


def applications() -> list[dict]:
    return list(reversed(demo_data.load_list("loan_applications")))


def confirm_receipt(app_id: str, sacks_found: int) -> Optional[dict]:
    app = next((a for a in demo_data.load_list("loan_applications") if a["id"] == app_id), None)
    if not app:
        return None
    ok = sacks_found >= app["sacks"]
    return demo_data.update("loan_applications", "id", app_id, {
        "status": STATUS[1] if ok else f"receipt shows {sacks_found} sacks, not {app['sacks']}",
        "receipt_checked": {"sacks_found": sacks_found, "matches": ok}})


def bank_decision(app_id: str, approve: bool) -> Optional[dict]:
    return demo_data.update("loan_applications", "id", app_id, {"status": STATUS[2] if approve else STATUS[3]})
