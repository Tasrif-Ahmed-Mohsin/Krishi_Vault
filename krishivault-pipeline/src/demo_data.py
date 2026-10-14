"""
Demo partners and the prototype's saved records
===============================================
- `data/demo/demo_partners.json`: made-up cold storages, buyers, banks, group
  pools, export markets and costs. Never real businesses; every screen says DEMO.
- `data/runtime/*.json`: what people do in the prototype (a farmer joins a
  group, applies for a loan, a bank decides). Not committed. KV_RUNTIME_DIR
  overrides the folder (the tests use a temporary one).
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from config.settings import DATA_DIR

DEMO_PATH = DATA_DIR / "demo" / "demo_partners.json"
_lock = threading.Lock()


@lru_cache(maxsize=1)
def partners() -> dict:
    with open(DEMO_PATH, encoding="utf-8") as f:
        return json.load(f)


def cold_storage(cs_id: str) -> dict:
    for cs in partners()["cold_storages"]:
        if cs["id"] == cs_id:
            return cs
    raise KeyError(cs_id)


def bank(bank_id: str) -> dict:
    for b in partners()["banks"]:
        if b["id"] == bank_id:
            return b
    raise KeyError(bank_id)


def runtime_dir() -> Path:
    return Path(os.getenv("KV_RUNTIME_DIR") or (DATA_DIR / "runtime"))


def load_list(name: str) -> list:
    path = runtime_dir() / f"{name}.json"
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_list(name: str, items: list) -> None:
    path = runtime_dir() / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    tmp.replace(path)


def append(name: str, item: dict) -> dict:
    with _lock:
        items = load_list(name)
        item = {**item, "time": datetime.now().isoformat(timespec="seconds")}
        items.append(item)
        save_list(name, items)
    return item


def update(name: str, key: str, value, changes: dict) -> dict | None:
    with _lock:
        items = load_list(name)
        for it in items:
            if it.get(key) == value:
                it.update(changes)
                save_list(name, items)
                return it
    return None
