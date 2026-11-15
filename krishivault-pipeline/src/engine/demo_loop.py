"""
The plan's whole loop in one go (a walkthrough for demos)
=========================================================
The screens show each step of the plan's loop on its own partner screen. This runs the steps
for one farmer, with the same engine and the same demo partners, so a visitor sees the loop
end to end in one click:

1. The harvest call: the store-or-sell answer (sell some now for the cash need, store the rest).
2. The digital receipt: a verified demo cold storage records the stored sacks; with it, the hold plan
   ("do not sell before", and the price that makes an earlier sale pay).
3. The bank loan: the application with the receipt; the cold storage confirms it; the bank
   approves (demo): the payout, and the hold on the receipt.
4. The price-window alert in the month the advice named.
5. The sale at the outlook's middle price: the cold storage, the bank, then the farmer; and the
   same split at the bad-case price (1 in 10), because a range is never a promise.

Every partner is DEMO and no money moves. Records are written like any other request, so the
partner screens show them. Nothing is sent: the SMS texts are shown, never sent.
"""

from __future__ import annotations

from src.engine import alerts, financing, hold_plan, receipts
from src.engine.facts import MAUND_KG, MONTHS_EN
from src.engine.storage_plan import FarmerLot, StoragePlanner
from src.voice.bangla_numbers import group_bd

_planner = StoragePlanner()

NOTE = ("A walkthrough with DEMO partners: the cold storage, the bank and the buyers are made up, and no money "
        "moves. The SMS texts are shown, not sent. Prices after the harvest are a statistical outlook with a "
        "range, not a promise.")


def _tk(x: float) -> str:
    return ("−" if x < 0 else "") + "৳" + group_bd(round(abs(x)))


def run(maunds: float = 80, price_today: float = 16, cash_needed_tk: float = 25_000, cash_days: int = 4,
        month: int = 3, year: int = 2027, district: str = "Bogura", cold_storage_id: str = "cs-a",
        bank_id: str = "bank-a", farmer_name: str = "Demo farmer (loop)") -> dict:
    lot = FarmerLot(quantity_kg=maunds * MAUND_KG, price_today=price_today, decision_month=month,
                    decision_year=year, cash_needed_tk=cash_needed_tk, cash_days=cash_days, district=district)
    plan = _planner.plan(lot)
    rec = plan["recommendation"]
    chosen = plan["options"].get(rec["key"]) or plan["options"]["sell_now"]
    sacks = plan["inputs"]["sacks"]
    store = 0 if rec["key"] == "sell_now" else int(chosen.get("store_sacks") or 0)
    profit = plan.get("net_profit") or {}

    call = [f"{group_bd(sacks)} sacks ({group_bd(round(maunds))} maunds) at ৳{price_today:g} a kg"
            + (f"; needs {_tk(cash_needed_tk)} within {cash_days} days" if cash_needed_tk else "")]
    if store:
        call.append(f"Selling {chosen['sell_sacks_now']} sacks now puts {_tk(chosen['cash_now'])} in hand")
        call.append(f"In all, about {_tk(chosen['money_mean'])} on average (bad case {_tk(chosen['money_low'])}): "
                    f"{_tk(chosen['gain_vs_now'])} more than selling every sack now; storing beats selling now "
                    f"in {round(chosen['chance_beats_now'] * 100)}% of price paths")
    else:
        call.append(f"About {_tk(chosen['money_mean'])} after costs, for certain at today's price")
    if profit.get("with_advice") is not None:
        call.append(f"Net profit after the growing cost (৳{profit['growing_cost_per_kg']:g} a kg): about "
                    f"{_tk(profit['with_advice'])}, against {_tk(profit['sell_all_now'])} selling everything now")
    steps = [{"step": 1, "who": "Farmer (phone call or USSD)", "screen": "call",
              "title": "The harvest call: store or sell, and until when?",
              "headline": rec["title_en"], "headline_bn": rec["title_bn"], "lines": call}]
    if not store:
        return {"season": f"{MONTHS_EN[month]} {year}", "steps": steps, "demo": True, "note": NOTE,
                "stopped": "The engine says sell now, so nothing goes into cold storage and no loan is needed. "
                           "In a big-crop year that is the honest answer."}

    # 2. The receipt from a verified demo cold storage, and the hold plan against selling in fear
    r = receipts.issue(cold_storage_id, farmer_name, None, store, month=month, year=year)
    hold = hold_plan.build(plan)
    receipt_lines = [f"Rent ৳{r['rent_per_sack']:g} a sack for the season, paid from the sale",
                     "Only partner cold storages with a backup generator and separate seed and table "
                     "chambers can issue receipts (the plan's rule)"]
    if hold:
        early = ", ".join(f"{c['month_en']} ৳{c['sell_only_above']:g}" for c in hold["checkpoints"])
        receipt_lines.append(f"With it, a hold plan: sell in {hold['sell_month_en']}"
                             + (f"; not before {hold['not_before_en']} (earlier months lose money on average)"
                                if hold["losing_months"] else "")
                             + (f"; an earlier sale pays only above {early} a kg" if early else ""))
    steps.append({"step": 2, "who": f"{r['cold_storage']['name']} (DEMO)", "screen": "cold_storage",
                  "title": "The cold storage weighs the sacks and issues a digital receipt",
                  "headline": f"Receipt {r['no']}: {store} sacks, {group_bd(r['kg'])} kg",
                  "lines": receipt_lines, "sms_bn": r["sms"], "hold_sms_bn": hold["sms"] if hold else None})

    # 3. The bank lends against the receipt; KrishiVault verifies and values, the bank decides
    months = max(1, min(9, int(chosen.get("months") or 6)))
    app = financing.apply(farmer_name, None, district, cold_storage_id, r["no"], store, price_today,
                          month, year, months, bank_id)
    financing.confirm_receipt(app["id"], store)
    approved = financing.bank_decision(app["id"], True)
    est = approved["estimate"]
    steps.append({"step": 3, "who": f"{est['bank']['name']} (DEMO)", "screen": "bank",
                  "title": "The bank lends against the receipt",
                  "headline": f"Loan {_tk(est['loan'])}, repaid from the sale in {est['ends']}",
                  "lines": [f"Valued with care: ৳{est['careful_price']:g} a kg (the bad-case price) after "
                            f"{est['crop']['shrinkage_buffer'] * 100:.2f}% weight loss; the cold storage's "
                            f"{_tk(est['paid_first_to_cold_storage'])} comes off first",
                            f"Risk {est['risk'].lower()}: a {round(est['chance_crop_worth_less_than_repayment'] * 100)}% "
                            f"chance the crop is worth less than the {_tk(est['repay'])} repayment",
                            f"Receipt {r['no']} is held for the bank: the sacks leave only with its agreement",
                            "The bank pays the farmer's bank or mobile-money account; KrishiVault never holds money"],
                  "sms_bn": financing.decision_sms(approved)})

    # 4. The price-window alert in the month the advice named, at the outlook's middle price
    when = next((m for m in plan["by_month"] if m["h"] == chosen.get("months")), plan["by_month"][-1])
    sale_month, sale_year = when["month"], year + (1 if when["month"] < month else 0)
    alert = next(iter(alerts.price_window(sale_month, sale_year, when["price_mid"], receipt_no=r["no"])), None)
    if alert:
        to = f" to {alert['buyer']['name']}" if alert.get("buyer") else ""
        headline = (f"Sell {alert['sell_sacks']} sacks now{to}" if alert["action"] == "sell"
                    else f"Hold until {alert['hold_until']}")
        steps.append({"step": 4, "who": "Field agent (SMS to the farmer)", "screen": "helper",
                      "title": f"{MONTHS_EN[sale_month]} {sale_year}: the price-window alert",
                      "headline": headline,
                      "lines": [f"The engine runs again for the receipt at ৳{when['price_mid']:g} a kg, the middle "
                                f"of the outlook (8 in 10 paths between ৳{when['price_low']:g} and "
                                f"৳{when['price_high']:g})"],
                      "sms_bn": alert["sms"]})

    # 5. The sale pays the cold storage, the bank, then the farmer; and the same at the bad-case price.
    # Sold to the alert's buyer, at what it leaves in hand per kg (after grading and the wait for payment)
    buyer = (alert or {}).get("buyer") or {}
    price, sold_to = when["price_mid"], "at the middle-path price"
    if buyer.get("net_per_kg"):
        price, sold_to = buyer["net_per_kg"], f"to {buyer['name']}, after its grading and payment terms"
    bank_owed = {"loan": est["loan"], "interest": est["interest"]}
    bad = receipts.sale_split(receipts.get(r["no"]), when["price_low"], months_stored=est["months"], bank=bank_owed)
    sale = financing.settle_sale(app["id"], price)
    steps.append({"step": 5, "who": "Buyer, cold storage, bank, farmer", "screen": "bank",
                  "title": "The sale pays the cold storage, then the bank, then the farmer",
                  "headline": f"The farmer gets {_tk(sale['farmer_gets'])} from the stored sacks",
                  "split": sale["lines"],
                  "lines": [f"Sold {group_bd(sale['kg_sold'])} kg {sold_to}: ৳{price:g} a kg in hand",
                            f"At the bad-case price (1 in 10), ৳{when['price_low']:g} a kg with no buyer's "
                            f"premium: the farmer gets "
                            f"{_tk(bad['farmer_gets'])}"
                            + ("; the loan is still covered" if bad["covered"]
                               else f"; {_tk(bad['unpaid'])} of the loan stays unpaid"),
                            sale["note"]]})
    return {"season": f"{MONTHS_EN[month]} {year}", "steps": steps, "demo": True, "note": NOTE,
            "ids": {"receipt": r["no"], "application": app["id"]}}
