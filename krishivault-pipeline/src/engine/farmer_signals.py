"""
The government screen: a glut warning and farmer figures by district
=====================================================================
What DAM, DAE or the Ministry would see (the plan's "ground-level farmer
intelligence"):

1. **Glut warning (real data):** this season's crop against its trend (BBS) and
   how strongly prices are expected to rise (the price outlook). A big crop
   means prices may stay flat all year, as in 2016-17 and 2024-25.
2. **Cold-storage fill (DEMO):** space booked against capacity, from the demo
   cold storages, and the requests and receipts made through KrishiVault.
3. **Farmer figures (from farmers who agreed):** how many needed cash within
   7 days of the harvest, how much, and what the engine advised, by district.

**Consent and anonymity:** a farmer's answers are counted only if the farmer
agrees (press 8 in the call; a ticked box on the dashboard). Nothing with a
name or phone number is kept here, and a district with fewer than 5 farmers is
not shown, so no one can be picked out. The claim to make is "direct,
farmer-originated, timestamped data with an auditable trail", not "data no one
can manipulate": checks, sampling and human verification still matter.
"""

from __future__ import annotations

import statistics
from datetime import datetime
from typing import Optional

from src import demo_data, events
from src.engine.facts import MONTHS_EN
from src.engine.storage_plan import is_glut
from src.models.price_outlook import rise_strength, season_for_decision

MIN_GROUP = 5          # a district with fewer farmers is not shown
CASH_SOON_DAYS = 7     # "needed cash within 7 days of the harvest"


def record(district: str, month: int, year: int, sacks: int, cash_needed_tk: float, cash_days: int,
           stored: str, advice_key: str, source: str) -> dict:
    """One farmer's answers, kept without a name or phone number. Call only after the farmer agreed."""
    return demo_data.append("farmer_signals", {
        "district": district or "Unknown", "month": int(month), "year": int(year), "sacks": int(sacks),
        "cash_needed_tk": round(float(cash_needed_tk or 0)), "cash_days": int(cash_days or 0),
        "stored": stored, "advice": advice_key, "source": source, "consent": True,
    })


def _share(n: int, total: int) -> float:
    return round(n / total, 2) if total else 0.0


def district_figures(min_group: int = MIN_GROUP) -> list[dict]:
    rows = [r for r in demo_data.load_list("farmer_signals") if r.get("consent")]
    by = {}
    for r in rows:
        by.setdefault(r["district"], []).append(r)
    out = []
    for district, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        n = len(rs)
        if n < min_group:
            out.append({"district": district, "farmers": n, "shown": False,
                        "why": f"fewer than {min_group} farmers: not shown, so no one can be picked out"})
            continue
        harvest = [r for r in rs if r["stored"] == "no"]
        cash = [r for r in harvest if r["cash_needed_tk"] > 0]
        soon = [r for r in cash if r["cash_days"] <= CASH_SOON_DAYS]
        advice = {k: _share(sum(1 for r in rs if r["advice"] == k), n) for k in ("sell_now", "sell_part", "store")}
        out.append({
            "district": district, "farmers": n, "shown": True,
            "at_harvest": len(harvest),
            "need_cash_within_7_days": _share(len(soon), len(harvest)),
            "median_cash_need_tk": round(statistics.median(r["cash_needed_tk"] for r in cash)) if cash else 0,
            "median_sacks": round(statistics.median(r["sacks"] for r in rs)),
            "advised": advice,
        })
    return out


def glut_watch(month: int, year: int, gap_override_pct: Optional[float] = None) -> dict:
    season = season_for_decision(year, month)
    rs = rise_strength(season, gap_override_pct=gap_override_pct, decision_year=year, decision_month=month)
    gap, k = rs["gap_pct"], rs["k"]
    if is_glut(rs):
        level, say = "high", "A big crop: prices may stay flat for most of the year. Expect pressure to sell early and gluts at the haats."
    elif gap <= -3:
        level, say = "low", "A small crop: prices are likely to rise after the harvest; watch for hoarding."
    else:
        level, say = "normal", "About a normal crop: the usual rise after the harvest is likely, with a range."
    return {"season": f"{season}-{str(season + 1)[-2:]}", "crop_gap_pct": gap, "crop_gap_range_pct": rs["gap_sd_pct"],
            "rise_strength": k, "level": level, "say": say,
            "basis": "BBS production against its trend (estimated from planted area at the harvest) and the "
                     "price outlook's rise strength (1 = the usual rise, 0 = flat)"}


def free_sacks(cs: dict) -> int:
    """Space left in a cold storage: capacity less booked sacks, KrishiVault receipts and earlier requests."""
    evs = events.recent(limit=500)
    requested = sum(int((e.get("details") or {}).get("sacks") or 0) for e in evs
                    if e["kind"] == "cold_storage_booking" and (e.get("details") or {}).get("cold_storage") == cs["name"]
                    and not (e.get("details") or {}).get("no_space"))
    received = sum(r["sacks"] for r in demo_data.load_list("storage_receipts") if r["cold_storage"]["id"] == cs["id"])
    return cs["capacity_sacks"] - cs["booked_sacks"] - received - requested


def no_space_share() -> dict:
    """The plan's signal: how many farmers who asked for cold-storage space could not get it, by district."""
    by = {}
    for e in events.recent(limit=500):
        if e["kind"] != "cold_storage_booking":
            continue
        d = by.setdefault(e.get("district") or "Unknown", {"requests": 0, "no_space": 0})
        d["requests"] += 1
        d["no_space"] += 1 if (e.get("details") or {}).get("no_space") else 0
    return {k: {**v, "share": _share(v["no_space"], v["requests"])} for k, v in by.items()}


def storage_fill() -> list[dict]:
    """Space booked against capacity (DEMO cold storages), with requests and receipts made on KrishiVault."""
    evs = events.recent(limit=500)
    recs = demo_data.load_list("storage_receipts")
    rows = []
    for cs in demo_data.partners()["cold_storages"]:
        requested = sum(int((e.get("details") or {}).get("sacks") or 0) for e in evs
                        if e["kind"] == "cold_storage_booking" and (e.get("details") or {}).get("cold_storage") == cs["name"])
        received = sum(r["sacks"] for r in recs if r["cold_storage"]["id"] == cs["id"])
        rows.append({"cold_storage": cs["name"], "district": cs["district"], "upazila": cs["upazila"],
                     "generator": bool(cs.get("generator")),
                     "separate_seed_table_chambers": bool(cs.get("separate_seed_table_chambers")),
                     "capacity_sacks": cs["capacity_sacks"], "booked_sacks": cs["booked_sacks"] + received,
                     "fill": round((cs["booked_sacks"] + received) / cs["capacity_sacks"], 2),
                     "requested_on_krishivault": requested, "receipts_on_krishivault": received,
                     "rent_per_sack": cs["rent_per_sack"], "demo": True})
    return rows


def government_view(month: int, year: int, gap_override_pct: Optional[float] = None) -> dict:
    fill = storage_fill()
    return {
        "when": f"{MONTHS_EN[month]} {year}",
        "glut": glut_watch(month, year, gap_override_pct),
        "storage": fill,
        "average_rent_per_sack": round(statistics.mean(r["rent_per_sack"] for r in fill)) if fill else None,
        "farmers": district_figures(),
        "space_requests": no_space_share(),
        "consent": "Counted only with the farmer's agreement; no names or phone numbers; districts with fewer "
                   f"than {MIN_GROUP} farmers are not shown.",
        "made": datetime.now().isoformat(timespec="seconds"),
    }
