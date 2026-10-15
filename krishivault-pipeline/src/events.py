"""
Event log: what happened in farmers' calls that a partner must act on
=====================================================================
A cold-storage booking, a lot sent to buyers, a group-storage join, a loan application, a helper callback.
Each is one JSON line in data/runtime/events.jsonl (not committed), so the partner screens can show it
straight after the call. Phone numbers are stored masked.

KV_EVENTS_PATH overrides the file (the tests use a temporary one).
"""

import json
import os
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import DATA_DIR
from src.voice.bangla_numbers import to_bn_digits

# Who acts on each kind of event
PARTNER_FOR = {
    "cold_storage_booking": "cold_storage",
    "group_storage_join": "cold_storage",
    "buyer_lot": "buyer",
    "loan_application": "bank",
    "helper_callback": "helper",
}


def events_path() -> Path:
    return Path(os.getenv("KV_EVENTS_PATH") or (DATA_DIR / "runtime" / "events.jsonl"))


def mask_phone(phone: Optional[str]) -> Optional[str]:
    """'01711998877' -> '01711-XXX877'. Several numbers (comma or space separated) are masked one by one."""
    masked = []
    for part in re.split(r"[,;/]+|\s{2,}|\s(?=\+?(?:88)?01)", phone or ""):
        digits = re.sub(r"\D", "", part)
        if len(digits) >= 6:
            masked.append(f"{digits[-11:-6]}-XXX{digits[-3:]}")
    return ", ".join(masked) or None


def new_reference() -> str:
    """A short number a farmer can say back on the phone (4 digits)."""
    return str(random.randint(1000, 9999))


def record(kind: str, summary_bn: str, details: dict, district: str = "", phone: Optional[str] = None) -> dict:
    event = {
        "ref": new_reference(),
        "time": datetime.now().isoformat(timespec="seconds"),
        "kind": kind,
        "for": PARTNER_FOR.get(kind, "helper"),
        "district": district,
        "phone": mask_phone(phone),
        "summary_bn": to_bn_digits(summary_bn),
        "details": details,
        "demo": True,
    }
    path = events_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def recent(limit: int = 50, partner: Optional[str] = None) -> list[dict]:
    path = events_path()
    if not path.exists():
        return []
    events = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if partner is None or e.get("for") == partner:
                events.append(e)
    return list(reversed(events))[:limit]
