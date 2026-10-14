"""
Export market intelligence
==========================
For exporters: where to buy potatoes in Bangladesh, and which foreign
markets pay after every cost.

- **Sourcing:** districts with a large crop (BBS) and low prices (WFP
  regional index): real data.
- **Markets:** foreign prices, freight and duties are **demo figures** until
  replaced with real quotes (`data/demo/demo_partners.json`).
- **The check that matters:** a high quoted price is not a profit. We add
  sorting and packing, the truck to the port, port papers and plant-health
  certificates, sea freight, insurance, import duty and the share rejected,
  and show the margin left.
"""

from __future__ import annotations

from typing import Optional

from src.demo_data import partners
from src.models.price_outlook import regional_index
from src.models.production_forecast import district_supply

# Approximate road distance (km) to Chattogram port and to Banglabandha land port (for Nepal)
DISTANCE_KM = {
    "Bogura": (450, 330), "Rangpur": (550, 200), "Dinajpur": (580, 150), "Thakurgaon": (630, 100),
    "Panchagarh": (680, 55), "Joypurhat": (490, 260), "Rajshahi": (500, 380), "Naogaon": (490, 300),
    "Nilphamari": (610, 160), "Gaibandha": (520, 260), "Lalmonirhat": (600, 210), "Kurigram": (580, 250),
    "Munshiganj": (250, 520), "Cumilla": (150, 600), "Jamalpur": (410, 380), "Chapai Nawabganj": (540, 400),
    "Natore": (450, 360), "Sirajganj": (360, 380), "Pabna": (400, 400), "Manikganj": (290, 470),
    "Narayanganj": (240, 520), "Dhaka": (250, 500),
}
DEFAULT_KM = (450, 400)


def sourcing(top: int = 12) -> list[dict]:
    """Districts ranked for buying: big crop first, then lower price."""
    idx = {r["district"]: r for r in regional_index()}
    rows = []
    for d in district_supply():
        r = idx.get(d["district"])
        km = DISTANCE_KM.get(d["district"], DEFAULT_KM)
        rows.append({**d, "price_index": r["index"] if r else None,
                     "price_reports": r["reports"] if r else 0, "km_to_chattogram": km[0],
                     "km_to_banglabandha": km[1], "distance_approx": d["district"] not in DISTANCE_KM})
    return rows[:top]


def evaluate(market_id: str, farmgate_price: float, source_district: str = "Bogura",
             quantity_t: float = 26.0, costs: Optional[dict] = None, quote_usd_t: Optional[float] = None) -> dict:
    """Cost build-up per kg for one market, and the margin left after every cost."""
    c = {**partners()["export_costs"], **(costs or {})}
    m = next(x for x in partners()["export_markets"] if x["id"] == market_id)
    fx = c["usd_to_bdt"]
    quote = (quote_usd_t or m["quote_usd_t"]) * fx / 1000           # ৳/kg at destination
    km = DISTANCE_KM.get(source_district, DEFAULT_KM)
    road_km = km[1] if "road" in m["route"] else km[0]
    reject = c["reject_pct"] / 100
    lines = [
        ("Buy from farmers (farm gate)", farmgate_price / (1 - reject)),
        ("Sort, grade and pack", c["sort_pack_per_kg"]),
        (f"Truck to {'Banglabandha' if 'road' in m['route'] else 'Chattogram port'} ({road_km} km)",
         c["truck_per_kg_km"] * road_km),
        ("Port, customs and plant-health papers", c["port_docs_per_kg"]),
        ("Freight", m["freight_usd_t"] * fx / 1000),
    ]
    before_duty = sum(v for _, v in lines)
    lines.append(("Insurance", before_duty * c["insurance_pct"] / 100))
    lines.append((f"Import duty ({m['duty_pct']}%)", quote * m["duty_pct"] / 100))
    landed = sum(v for _, v in lines)
    margin = quote - landed
    margin_pct = margin / quote * 100 if quote else 0
    verdict = "profitable" if margin_pct >= 5 else "thin" if margin_pct >= 0 else "loss"
    return {
        "market": m["country"], "id": m["id"], "route": m["route"], "requirements": m["requirements"],
        "quote_per_kg": round(quote, 2), "quote_usd_t": quote_usd_t or m["quote_usd_t"],
        "quote_vs_farmgate": round(quote / farmgate_price, 2) if farmgate_price else None,
        "cost_lines": [{"item": k, "per_kg": round(v, 2)} for k, v in lines],
        "landed_cost_per_kg": round(landed, 2), "margin_per_kg": round(margin, 2),
        "margin_pct": round(margin_pct, 1), "verdict": verdict,
        "margin_per_container": round(margin * c["container_t"] * 1000),
        "margin_total": round(margin * quantity_t * 1000),
        "demo_figures": True,
    }


def evaluate_all(farmgate_price: float, source_district: str = "Bogura", quantity_t: float = 26.0) -> dict:
    rows = [evaluate(m["id"], farmgate_price, source_district, quantity_t) for m in partners()["export_markets"]]
    rows.sort(key=lambda r: -r["margin_per_kg"])
    highest = max(rows, key=lambda r: r["quote_per_kg"])
    return {
        "source_district": source_district, "farmgate_price": farmgate_price, "markets": rows,
        "highest_quote": highest["market"], "best_margin": rows[0]["market"] if rows else None,
        "lesson": (f"{highest['market']} quotes the most (৳{highest['quote_per_kg']}/kg), "
                   f"but {rows[0]['market']} leaves the most after costs (৳{rows[0]['margin_per_kg']}/kg)."
                   if highest["market"] != rows[0]["market"] else
                   f"{highest['market']} quotes the most and also leaves the most after costs."),
        "note": "Foreign prices, freight and duties are demo figures until replaced with real quotes.",
    }


def domestic_gaps(national_price: float, min_reports: int = 5) -> list[dict]:
    """Price gaps between districts (WFP), for traders moving potatoes inside Bangladesh."""
    rows = [r for r in regional_index() if r["reports"] >= min_reports]
    if len(rows) < 2:
        return []
    low, high = rows[0], rows[-1]
    gap = (high["index"] - low["index"]) * national_price
    return [{"buy_in": low["district"], "sell_in": high["district"], "price_gap_per_kg": round(gap, 2),
             "note": "Before transport costs"}]
