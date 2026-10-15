"""
Digital storage receipts, the bank's hold, and the split when the potatoes are sold
==================================================================================
Steps 2 to 4 of the plan's loop (harvest call → cold storage → loan → sale):

1. **The receipt (e-receipt):** the cold storage weighs and grades the farmer's
   sacks, records them on its KrishiVault screen, and the farmer gets the
   receipt number by SMS. The number is the proof a bank loan needs.
2. **The hold:** when a bank approves a loan against the receipt, the receipt is
   "held for the bank": the cold storage releases the sacks only with the
   bank's agreement.
3. **The split at sale:** the sale pays, in this order, the cold storage (rent
   and its own advance with interest), the bank (loan and interest), and then
   the farmer. The hold ends.

KrishiVault does not lend and does not hold money: it works out the split; in a
pilot the money moves through the bank or a mobile-money account. Every receipt
here is DEMO. Records live in `data/runtime/storage_receipts.json` (not committed).
"""

from __future__ import annotations

from typing import Optional

from src import contacts, demo_data, events
from src.engine.facts import StorageTerms
from src.voice.bangla_numbers import group_bd, to_bn_digits, to_en_digits

GRADES = {"table": ("table potato", "খাবার আলু"), "seed": ("seed potato", "বীজ আলু")}


def _code(cold_storage_id: str) -> str:
    """'cs-a' -> 'CSA': the start of the receipt number."""
    return "".join(ch for ch in cold_storage_id.upper() if ch.isalnum())[:6] or "CS"


def _fmt(n: float) -> str:
    return to_bn_digits(group_bd(round(n)))


def receipt_sms(r: dict) -> str:
    """The receipt as one SMS, built from the record (never from the page)."""
    return (f"কৃষিভল্ট রসিদ নং {r['no']}। {r['cold_storage']['name_bn']}: আপনার "
            f"{_fmt(r['sacks'])} বস্তা {GRADES[r['grade']][1]} ({_fmt(r['kg'])} কেজি) জমা হয়েছে। "
            f"ভাড়া বস্তাপ্রতি {_fmt(r['rent_per_sack'])} টাকা। ঋণের জন্য এই নম্বর বলুন। (ডেমো)")


def partner_check(cs: dict) -> list[str]:
    """The plan's rule for partner cold storages: a backup generator, and separate seed and table chambers."""
    missing = []
    if not cs.get("generator"):
        missing.append("a backup generator")
    if not cs.get("separate_seed_table_chambers"):
        missing.append("separate seed and table chambers")
    return missing


def issue(cold_storage_id: str, farmer_name: str, phone: Optional[str], sacks: int,
          kg_weighed: Optional[float] = None, grade: str = "table", advance_per_sack: float = 0.0,
          month: int = 3, year: int = 2027) -> dict:
    """The cold storage records weighed and graded sacks; returns the receipt with its SMS text."""
    cs = demo_data.cold_storage(cold_storage_id)
    missing = partner_check(cs)
    if missing:
        raise ValueError(f"{cs['name']} is not a KrishiVault partner yet: it needs {' and '.join(missing)} (plan rule)")
    if grade not in GRADES:
        raise ValueError("grade must be 'table' or 'seed'")
    if advance_per_sack > cs["advance_per_sack"]:
        raise ValueError(f"{cs['name']} advances at most ৳{cs['advance_per_sack']} a sack")
    t = StorageTerms()
    kg = float(kg_weighed) if kg_weighed else sacks * t.sack_kg
    existing = [r for r in all_receipts() if r["cold_storage"]["id"] == cs["id"]]
    no = f"{_code(cs['id'])}-{len(existing) + 1:04d}"
    record = {
        "no": no, "cold_storage": {"id": cs["id"], "name": cs["name"], "name_bn": cs["name_bn"]},
        "district": cs["district"], "farmer": farmer_name, "phone": events.mask_phone(phone),
        "sacks": int(sacks), "kg": round(kg), "kg_per_sack": round(kg / sacks, 1), "grade": grade,
        "rent_per_sack": cs["rent_per_sack"], "rent_paid": False,
        "advance": round(advance_per_sack * sacks), "advance_rate_year": cs["advance_rate_year"],
        "status": "in store", "hold": None, "stored_month": int(month), "stored_year": int(year), "demo": True,
    }
    record["sms"] = receipt_sms(record)
    event = events.record("storage_receipt", f"{farmer_name}: {sacks} বস্তা আলু জমা, রসিদ দেওয়া হয়েছে",
                          {"receipt": no, "sacks": int(sacks), "kg": round(kg), "grade": grade,
                           "cold_storage": cs["name"]}, district=cs["district"], phone=phone)
    record["ref"] = event["ref"]
    contacts.save(f"receipt:{no}", phone)        # for the loan and price-window SMS later; never shown
    return demo_data.append("storage_receipts", record)


def all_receipts(cold_storage_id: Optional[str] = None) -> list[dict]:
    items = demo_data.load_list("storage_receipts")
    return [r for r in items if cold_storage_id is None or r["cold_storage"]["id"] == cold_storage_id]


def _norm(no: str) -> str:
    return to_en_digits(no or "").strip().upper()


def get(no: str) -> Optional[dict]:
    no = _norm(no)
    return next((r for r in all_receipts() if r["no"] == no), None)


def place_hold(no: str, bank_name: str, application_id: str, loan: float) -> Optional[dict]:
    """The bank approved a loan: the sacks leave the cold storage only with the bank's agreement."""
    return demo_data.update("storage_receipts", "no", _norm(no), {
        "status": "held for the bank: released only with the bank's agreement",
        "hold": {"bank": bank_name, "application": application_id, "loan": round(loan)}})


# ------------------------------------------------------------------ the split at sale

def split_sale(sale_value: float, selling_costs: float, cold_storage: dict, bank: dict) -> dict:
    """
    Who is paid from a sale, in order: selling costs, the cold storage, the bank, then the farmer.
    `cold_storage` and `bank` map a line name to taka. If the sale does not cover everything, what is
    left unpaid is shown (the bank's shortfall); the farmer then gets nothing from this sale.
    """
    left = sale_value
    lines = [{"to": "buyer pays", "line": "Sale", "tk": round(sale_value)}]
    unpaid = 0.0
    for who, items in (("selling", {"Carrying and selling": selling_costs}), ("cold storage", cold_storage),
                       ("bank", bank)):
        for name, amount in items.items():
            if amount <= 0:
                continue
            paid = min(amount, max(left, 0.0))
            left -= paid
            unpaid += amount - paid
            lines.append({"to": who, "line": name, "tk": -round(paid),
                          **({"unpaid": round(amount - paid)} if paid < amount else {})})
    farmer = max(left, 0.0)
    lines.append({"to": "farmer", "line": "To the farmer", "tk": round(farmer)})
    return {"lines": lines, "farmer_gets": round(farmer), "unpaid": round(unpaid),
            "covered": unpaid == 0,
            "note": "KrishiVault works out the split; the bank or a mobile-money account pays it. "
                    "KrishiVault never holds the money."}


def settle(no: str, price_per_kg: float, kg_sold: Optional[float] = None, months_stored: int = 9,
           bank: Optional[dict] = None) -> Optional[dict]:
    """
    The receipt's potatoes are sold: pay the cold storage, then the bank (if a loan holds the receipt),
    then the farmer, and end the hold. `bank` is {"loan", "interest"} from the loan application.
    Without `kg_sold`, the receipt's weight less the season's storage loss (8.65%) is used.
    """
    r = get(no)
    if not r:
        return None
    t = StorageTerms()
    kg = float(kg_sold) if kg_sold else r["kg"] * (1 - t.season_loss())
    cold = {"Rent": 0 if r["rent_paid"] else r["sacks"] * r["rent_per_sack"]}
    if r["advance"]:
        cold["Cold-storage advance"] = r["advance"]
        cold["Advance interest"] = r["advance"] * r["advance_rate_year"] * months_stored / 12
    owed = {}
    if bank and bank.get("loan"):
        owed = {"Bank loan": bank["loan"], "Bank interest": bank.get("interest", 0)}
    out = split_sale(kg * price_per_kg, r["sacks"] * t.sell_from_store_per_sack, cold, owed)
    out.update({"receipt": r["no"], "kg_sold": round(kg), "price_per_kg": price_per_kg})
    demo_data.update("storage_receipts", "no", r["no"], {
        "status": "sold; the cold storage and bank paid from the sale (demo)" if owed else "sold (demo)",
        "hold": None, "settlement": out})
    return out
