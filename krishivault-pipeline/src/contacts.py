"""
Phone numbers kept only to send a farmer an SMS (or a call) later
=================================================================
A receipt, a loan approval or a price alert reaches the farmer after the moment they gave their
number. The number is kept here, apart from every record the screens show (those keep it masked), and
no API returns it. `data/runtime/contacts.json` (not committed); KV_RUNTIME_DIR overrides the folder.

`voice` is the farmer's choice, made once (usually at the cold storage): "I cannot read an SMS, call me".
Every later message (the loan decision, the price-window alerts) then also goes as a call.
"""

from typing import Optional

from src import demo_data


def save(key: str, phone: Optional[str], voice: bool = False) -> None:
    if not phone:
        return
    items = [c for c in demo_data.load_list("contacts") if c.get("key") != key]
    items.append({"key": key, "phone": phone, "voice": bool(voice)})
    demo_data.save_list("contacts", items)


def _find(key: str) -> Optional[dict]:
    return next((c for c in demo_data.load_list("contacts") if c.get("key") == key), None)


def get(key: str) -> Optional[str]:
    c = _find(key)
    return c["phone"] if c else None


def prefers_voice(key: str) -> bool:
    c = _find(key)
    return bool(c and c.get("voice"))
