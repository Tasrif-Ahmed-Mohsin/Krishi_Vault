"""
Phone numbers kept only to send a farmer an SMS later
=====================================================
A receipt, a loan approval or a price alert reaches the farmer by SMS after the moment they gave their
number. The number is kept here, apart from every record the screens show (those keep it masked), and
no API returns it. `data/runtime/contacts.json` (not committed); KV_RUNTIME_DIR overrides the folder.
"""

from typing import Optional

from src import demo_data


def save(key: str, phone: Optional[str]) -> None:
    if not phone:
        return
    items = [c for c in demo_data.load_list("contacts") if c.get("key") != key]
    items.append({"key": key, "phone": phone})
    demo_data.save_list("contacts", items)


def get(key: str) -> Optional[str]:
    return next((c["phone"] for c in demo_data.load_list("contacts") if c.get("key") == key), None)
