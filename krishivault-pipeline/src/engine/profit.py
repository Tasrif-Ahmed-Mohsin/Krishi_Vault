"""
Profit calculator: what the farmer spent, earned and kept
=========================================================
A farmer often knows the selling price but not the profit after every cost.
This adds up:
- growing costs: seed, fertilizer, pesticide, labour, irrigation, ploughing, land rent, harvesting;
- after-harvest costs: sacks, transport, cold-storage rent, loading, loan interest, selling costs;
- every sale (kilos x price), and potatoes still in store at an estimated price;
and shows the profit per kg, per sack (84 kg), per maund and for the whole harvest,
with the price needed just to cover costs.

The example figures are for one bigha of potato in Bogura and are only a
starting point: the farmer replaces them with his own.
"""

from __future__ import annotations

from typing import Optional

from src.engine.facts import MAUND_KG, SACK_KG, StorageTerms

BIGHA_HA = 0.1338          # Bogura bigha: 33 decimals
ACRE_HA = 0.4047
DECIMAL_HA = 0.004047

GROWING_LINES = ["seed", "fertilizer", "pesticide", "labour", "irrigation", "ploughing", "land_rent", "harvest", "other"]
AFTER_LINES = ["sacks", "transport", "storage_rent", "loading", "interest", "selling"]

LABELS = {
    "seed": ("Seed potato", "বীজ আলু"), "fertilizer": ("Fertilizer", "সার"), "pesticide": ("Pesticide", "কীটনাশক"),
    "labour": ("Labour", "শ্রমিক"), "irrigation": ("Irrigation", "সেচ"), "ploughing": ("Ploughing", "চাষ"),
    "land_rent": ("Land rent or lease", "জমির খাজনা/লিজ"), "harvest": ("Harvesting", "আলু তোলা"),
    "other": ("Other", "অন্যান্য"), "sacks": ("Sacks", "বস্তা"), "transport": ("Transport", "পরিবহন"),
    "storage_rent": ("Cold-storage rent", "হিমাগার ভাড়া"), "loading": ("Loading and unloading", "লোড-আনলোড"),
    "interest": ("Loan interest", "ঋণের সুদ"), "selling": ("Selling costs", "বিক্রির খরচ"),
}

# Example only: one bigha of potato in Bogura. Replace with the farmer's own figures.
EXAMPLE_BIGHA = {
    "land": {"amount": 1, "unit": "bigha"},
    "harvest_kg": 3000,
    "growing": {"seed": 11000, "fertilizer": 6500, "pesticide": 2500, "labour": 6500, "irrigation": 1800,
                "ploughing": 1500, "land_rent": 5000, "harvest": 2500, "other": 700},
    "after": {"sacks": 960, "transport": 1320, "storage_rent": 6000, "loading": 360, "interest": 0, "selling": 120},
    "sales": [{"month": "March", "kg": 1000, "price_per_kg": 14},
              {"month": "November", "kg": 1950, "price_per_kg": 24}],
}


def land_hectares(amount: float, unit: str) -> float:
    return amount * {"bigha": BIGHA_HA, "acre": ACRE_HA, "decimal": DECIMAL_HA, "hectare": 1.0}.get(unit, BIGHA_HA)


def calculate(harvest_kg: float, growing: dict, after: dict, sales: list[dict],
              land_amount: float = 1.0, land_unit: str = "bigha",
              unsold_price_per_kg: Optional[float] = None, harvest_price_per_kg: Optional[float] = None) -> dict:
    growing = {k: float(growing.get(k) or 0) for k in GROWING_LINES}
    after = {k: float(after.get(k) or 0) for k in AFTER_LINES}
    grow_total, after_total = sum(growing.values()), sum(after.values())
    sold_kg = sum(float(s.get("kg") or 0) for s in sales)
    revenue = sum(float(s.get("kg") or 0) * float(s.get("price_per_kg") or 0) for s in sales)
    unsold_kg = max(0.0, harvest_kg - sold_kg)
    unsold_value = unsold_kg * unsold_price_per_kg if unsold_price_per_kg else 0.0
    total_cost = grow_total + after_total
    income = revenue + unsold_value
    profit = income - total_cost
    per = lambda x: x / harvest_kg if harvest_kg else 0.0   # noqa: E731
    ha = land_hectares(land_amount, land_unit)

    result = {
        "land": {"amount": land_amount, "unit": land_unit, "hectares": round(ha, 3)},
        "harvest_kg": round(harvest_kg), "yield_t_ha": round(harvest_kg / 1000 / ha, 1) if ha else None,
        "sacks": round(harvest_kg / SACK_KG, 1), "maunds": round(harvest_kg / MAUND_KG, 1),
        "lines": [{"key": k, "group": "growing", "label_en": LABELS[k][0], "label_bn": LABELS[k][1], "tk": round(v)}
                  for k, v in growing.items()] +
                 [{"key": k, "group": "after", "label_en": LABELS[k][0], "label_bn": LABELS[k][1], "tk": round(v)}
                  for k, v in after.items()],
        "growing_cost": round(grow_total), "after_harvest_cost": round(after_total), "total_cost": round(total_cost),
        "growing_cost_per_kg": round(per(grow_total), 2), "cost_per_kg": round(per(total_cost), 2),
        "cost_per_sack": round(per(total_cost) * SACK_KG), "cost_per_maund": round(per(total_cost) * MAUND_KG),
        "sold_kg": round(sold_kg), "revenue": round(revenue),
        "unsold_kg": round(unsold_kg), "unsold_value": round(unsold_value),
        "income": round(income), "profit": round(profit),
        "profit_per_kg": round(per(profit), 2), "profit_per_sack": round(per(profit) * SACK_KG),
        "profit_per_maund": round(per(profit) * MAUND_KG),
        "margin_pct": round(profit / income * 100, 1) if income else None,
        "break_even_price": round(per(total_cost), 2),
        "average_price": round(revenue / sold_kg, 2) if sold_kg else None,
    }
    if harvest_price_per_kg:
        # everything sold at the field at harvest: no sacks, storage, loading or interest
        sell_now_costs = harvest_kg / SACK_KG * StorageTerms().sell_now_per_sack
        all_now = harvest_kg * harvest_price_per_kg - grow_total - sell_now_costs
        result["if_all_sold_at_harvest"] = {
            "price_per_kg": harvest_price_per_kg, "profit": round(all_now),
            "difference": round(profit - all_now),
            "note": "Everything sold at the field at harvest: no sacks, storage or loading costs.",
        }
    return result


def example() -> dict:
    e = EXAMPLE_BIGHA
    return calculate(e["harvest_kg"], e["growing"], e["after"], e["sales"], e["land"]["amount"], e["land"]["unit"],
                     harvest_price_per_kg=14)
