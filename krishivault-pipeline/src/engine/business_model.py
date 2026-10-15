"""
The business plan: who pays, how much, and the 3-year projection
================================================================
The figures of the team's plan document (15 October 2026), worked out from
its own assumptions, so the pitch deck and the docs quote sums that add up.

**The farmer pays no fee.** KrishiVault earns only when value is created:
1. Telco VAS: the KrishiVault voice line at a value-added-service call rate
   (৳2-3 a minute), shared 50/50 with Grameenphone: about ৳30 per active farmer a year.
2. Cold storages: 4% of the ৳300 storage fee = ৳12 per bag booked through KrishiVault.
3. Banks and microfinance: 1.5% of a ৳300 loan = ৳4.50 per financed bag.
4. Buyers and processors: 1% sourcing fee, about ৳12 per bag bought.
5. Government and media: subscriptions to the cold-storage fill and glut analytics.

**No paid placement:** none of these fees changes what a farmer is advised.

Shares the plan's table implies but does not state (checked in the tests): 60%
of bags financed, 30% of bags sold to a buyer through KrishiVault, 40 bags per
farmer. `notes()` says how the plan's figures are read where it gives two.
"""

from __future__ import annotations

from src.engine.facts import RENT_PER_SACK, SACK_KG

# ------------------------------------------------------------------ the plan's assumptions
STORAGE_FEE_PER_BAG = RENT_PER_SACK   # the plan's ৳300 a bag (the engine uses the same rent)
COLD_STORAGE_COMMISSION = 0.04    # → ৳12 a bag
LOAN_PER_BAG = 300.0              # "partner banks lend ~Tk 300/bag (50% LTV on crop value)"
LOAN_FEE = 0.015                  # → ৳4.50 a financed bag
SOURCING_FEE_PER_BAG = 12.0       # "1% sourcing fee (~Tk 12 per bag)", so a bag sells for about ৳1,200
SOURCING_FEE = 0.01
VAS_PER_FARMER_YEAR = 30.0        # ৳2-3 a minute, 50/50 with Grameenphone
BAGS_PER_FARMER = 40              # "an active farmer stores an average of 40-50 bags"; the table uses 40
SHARE_FINANCED = 0.6              # implied by the table: Tk 2,16,000 = 48,000 of 80,000 bags × ৳4.50
SHARE_SOLD_TO_BUYERS = 0.3        # implied by the table: Tk 2,88,000 = 24,000 of 80,000 bags × ৳12

YEARS = [
    {"year": 1, "where": "Pilot: Bogura and Munshiganj", "farmers": 2_000, "cold_storages": 5,
     "government_media": 200_000, "opex": 1_850_000},
    {"year": 2, "where": "Scale: 4 major districts", "farmers": 15_000, "cold_storages": 35,
     "government_media": 1_200_000, "opex": 5_800_000},
    {"year": 3, "where": "National expansion", "farmers": 60_000, "cold_storages": 100,
     "government_media": 3_500_000, "opex": 14_500_000},
]

STARTUP_CAPITAL = [   # first 12 months: ৳20 lakh (about 17,000 US dollars)
    ("Tech, AI and telco integration", 700_000,
     "Price and yield outlook, cold-storage web portal, Grameenphone IVR/USSD short code"),
    ("Field operations and onboarding", 600_000,
     "Field agents in Kahaloo (Bogura) and Munshiganj; 3-5 partner cold storages; training"),
    ("Legal, bank API and compliance", 300_000,
     "Trade licence, digital warehouse-receipt framework, MoU and API with one bank or MFI"),
    ("Rural marketing and activation", 200_000, "Haat activations (Dhaper Hat, Bibir Pukur); SMS and voice at harvest"),
    ("Working capital and buffer", 200_000, "Cloud servers, contingency, travel"),
]
FUNDING = {"stage": "Pre-seed or grant, months 1-12", "amount_tk": (2_000_000, 2_500_000),
           "sources": "Grameenphone FutureMakers prize, ICT Division (iDEA) grant, or angel investors",
           "goal": "Pilot with 2,000 farmers and 5 partner cold storages",
           "break_even": "Year 2 (about month 14-16)"}


def unit_fees() -> dict:
    return {
        "cold_storage_per_bag": STORAGE_FEE_PER_BAG * COLD_STORAGE_COMMISSION,
        "bank_per_financed_bag": LOAN_PER_BAG * LOAN_FEE,
        "buyer_per_bag": SOURCING_FEE_PER_BAG,
        "implied_sale_per_bag": SOURCING_FEE_PER_BAG / SOURCING_FEE,
        "vas_per_farmer_year": VAS_PER_FARMER_YEAR,
    }


def projection() -> list[dict]:
    fees = unit_fees()
    rows = []
    for y in YEARS:
        bags = y["farmers"] * BAGS_PER_FARMER
        streams = {
            "telco_vas": y["farmers"] * fees["vas_per_farmer_year"],
            "cold_storage": bags * fees["cold_storage_per_bag"],
            "bank": bags * SHARE_FINANCED * fees["bank_per_financed_bag"],
            "buyers": bags * SHARE_SOLD_TO_BUYERS * fees["buyer_per_bag"],
            "government_media": y["government_media"],
        }
        streams = {k: round(v) for k, v in streams.items()}
        revenue = sum(streams.values())
        profit = revenue - y["opex"]
        rows.append({**y, "bags": bags, "streams": streams, "revenue": revenue, "profit": profit,
                     "margin": round(profit / revenue, 3)})
    return rows


def startup_capital() -> dict:
    total = sum(a for _, a, _ in STARTUP_CAPITAL)
    return {"total": total, "lines": [{"line": n, "tk": a, "share": round(a / total, 2), "covers": c}
                                      for n, a, c in STARTUP_CAPITAL]}


def notes(price_per_kg: float = 16.0) -> list[str]:
    """How the plan document's figures are read where it gives two (the plan is the main model)."""
    bag_value = SACK_KG * price_per_kg
    return [
        f"Rent: the plan's ৳{RENT_PER_SACK:.0f} a sack is used everywhere: in the engine, the demo cold storages and "
        f"the projection (4% = ৳{RENT_PER_SACK * COLD_STORAGE_COMMISSION:.0f} a sack).",
        f"Loan per sack: the projection uses the plan's ৳{LOAN_PER_BAG:.0f} a sack. The engine's banks lend the plan's "
        f"50-60% of a careful value (after the 8.65% loss, rent and selling costs); at ৳{price_per_kg:.0f}/kg a sack is "
        f"worth ৳{bag_value:,.0f}, so real loans can be larger and the ৳4.50 fee is a cautious figure.",
        "Calls: the farmer pays no fee to KrishiVault. Calls to the KrishiVault voice line are charged at a "
        "Grameenphone VAS rate (৳2-3 a minute), shared 50/50 with Grameenphone (the plan's first income stream).",
        "Pilot: phase 1 (months 1-4) is 50-100 farmers in Kahaloo; phase 2 (months 5-12) grows to 1,000+ farmers in "
        "Bogura and Munshiganj; the year-1 projection counts 2,000 active farmers and 5 cold storages by the end of "
        "year 1.",
    ]


def business_plan() -> dict:
    return {"unit_fees": unit_fees(), "projection": projection(), "startup_capital": startup_capital(),
            "funding": FUNDING, "notes": notes(),
            "assumptions": {"bags_per_farmer": BAGS_PER_FARMER, "share_financed": SHARE_FINANCED,
                            "share_sold_to_buyers": SHARE_SOLD_TO_BUYERS},
            "rule": "No paid placement: a partner's fee never changes what a farmer is advised."}
