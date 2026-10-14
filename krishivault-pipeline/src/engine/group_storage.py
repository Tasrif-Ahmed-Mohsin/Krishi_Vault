"""
Group storage: neighbours combine their sacks for a better rate
===============================================================
A cold storage may charge less a sack for a big order (for example 500 sacks
instead of 50). One farmer rarely has that many; a group of neighbours does.
Sharing one truck also costs less a sack than each farmer hiring a van.

Honesty rule: a discount counts only after the cold storage **agrees** to it
on its KrishiVault screen. Until then the screen shows it as a possible
saving, never as money the farmer will get.
"""

from __future__ import annotations

import math
from typing import Optional

from src import demo_data, events


def _agreed(pool_id: str) -> set:
    return {c["min_sacks"] for c in demo_data.load_list("group_agreements") if c["pool_id"] == pool_id}


def _members(pool: dict) -> list[dict]:
    joined = [j for j in demo_data.load_list("group_joins") if j["pool_id"] == pool["id"]]
    return [{**m, "demo": True} for m in pool["members"]] + [
        {"name": j["name"], "sacks": j["sacks"], "demo": False, "phone": j.get("phone")} for j in joined]


def pool_status(pool: dict, extra_sacks: int = 0) -> dict:
    cs = demo_data.cold_storage(pool["cold_storage_id"])
    transport = demo_data.partners()["transport"]
    members = _members(pool)
    total = sum(m["sacks"] for m in members) + extra_sacks
    agreed = _agreed(pool["id"])
    tiers = []
    for o in sorted(cs["group_offers"], key=lambda o: o["min_sacks"]):
        tiers.append({**o, "reached": total >= o["min_sacks"], "agreed": o["min_sacks"] in agreed,
                      "sacks_short": max(0, o["min_sacks"] - total)})
    reached = [t for t in tiers if t["reached"]]
    usable = [t for t in reached if t["agreed"]]
    rent_agreed = min((t["rent_per_sack"] for t in usable), default=cs["rent_per_sack"])
    rent_possible = min((t["rent_per_sack"] for t in reached), default=cs["rent_per_sack"])
    next_tier = next((t for t in tiers if not t["reached"]), None)
    trucks = math.ceil(total / transport["truck_sacks"]) if total else 0
    return {
        "id": pool["id"], "name": pool["name"], "district": pool["district"], "upazila": pool["upazila"],
        "cold_storage": {"id": cs["id"], "name": cs["name"], "rent_per_sack": cs["rent_per_sack"],
                         "free_sacks": cs["capacity_sacks"] - cs["booked_sacks"]},
        "members": members, "member_count": len(members), "total_sacks": total,
        "tiers": tiers, "next_tier": next_tier,
        "rent_agreed": rent_agreed, "rent_possible": rent_possible,
        "trucks": trucks, "offer_status": cs.get("offer_status", "demo offer"),
    }


def pools(district: Optional[str] = None) -> list[dict]:
    out = []
    for p in demo_data.partners()["group_pools"]:
        if district and p["district"].lower() != district.lower():
            continue
        out.append(pool_status(p))
    return out


def _pool(pool_id: str) -> dict:
    for p in demo_data.partners()["group_pools"]:
        if p["id"] == pool_id:
            return p
    raise KeyError(pool_id)


def compare(pool_id: str, sacks: int) -> dict:
    """One farmer's cost alone against joining the group."""
    pool = _pool(pool_id)
    status = pool_status(pool, extra_sacks=sacks)
    transport = demo_data.partners()["transport"]
    cs = status["cold_storage"]
    alone = sacks * (cs["rent_per_sack"] + transport["individual_per_sack"])
    group_agreed = sacks * (status["rent_agreed"] + transport["group_truck_per_sack"])
    group_possible = sacks * (status["rent_possible"] + transport["group_truck_per_sack"])
    return {
        "pool": status, "sacks": sacks,
        "alone": {"rent": cs["rent_per_sack"], "transport": transport["individual_per_sack"], "total": round(alone)},
        "group_now": {"rent": status["rent_agreed"], "transport": transport["group_truck_per_sack"],
                      "total": round(group_agreed), "saving": round(alone - group_agreed)},
        "group_if_agreed": {"rent": status["rent_possible"], "total": round(group_possible),
                            "saving": round(alone - group_possible)},
        "note": "Truck sharing saves from the start. A lower rent counts only after the cold storage agrees to it.",
    }


def join(pool_id: str, name: str, sacks: int, phone: Optional[str] = None) -> dict:
    pool = _pool(pool_id)
    entry = demo_data.append("group_joins", {"pool_id": pool_id, "name": name, "sacks": int(sacks),
                                             "phone": events.mask_phone(phone)})
    status = pool_status(pool)
    ev = events.record("group_storage_join", f"{name}: {sacks} বস্তা, {pool.get('name_bn') or pool['name']}",
                       {"pool": pool_id, "sacks": sacks, "group_total": status["total_sacks"]},
                       district=pool["district"], phone=phone)
    return {"joined": entry, "pool": status, "ref": ev["ref"], "event": ev}


def agree_offer(pool_id: str, min_sacks: int) -> dict:
    """The cold storage agrees a group rate (from its screen)."""
    pool = _pool(pool_id)
    demo_data.append("group_agreements", {"pool_id": pool_id, "min_sacks": int(min_sacks)})
    return pool_status(pool)
