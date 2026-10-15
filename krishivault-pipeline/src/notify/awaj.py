"""
Awaj Digital voice calls (https://awajdigital.com/api-docs)
==========================================================
Calls that read Bangla text aloud (Direct TTS Broadcast), calls that play our own audio, keypad surveys,
and their results. Ported from Mati Kohon's awaj.ts (reference/mati_kohon_code/).

Nothing is dialled unless all three are set:
  AWAJ_API_TOKEN  the Bearer token from the Awaj dashboard (Profile -> API Tokens); never commit it
  AWAJ_SENDER     an active caller number on the account (senders() lists them)
  AWAJ_LIVE=1     the switch that turns dry runs into real, billed calls
Without them every function returns the exact request it would send ({"dry_run": True, ...}).
Awaj needs the "direct broadcast" and "AI TTS" permissions on the account for Direct TTS.

Keypad surveys play recorded voices: record the menu, upload it with upload_voice and wait for Awaj to
approve it, then name it in a survey. Awaj posts the pressed keys to the survey's webhook URL.
"""

import os
import re
import uuid
from pathlib import Path
from typing import Optional

import requests

TIMEOUT_S = 20


def base_url() -> str:
    return (os.getenv("AWAJ_BASE_URL") or "https://api.awajdigital.com/api").rstrip("/")


def awaj_config() -> dict:
    token = os.getenv("AWAJ_API_TOKEN", "")
    sender = os.getenv("AWAJ_SENDER") or os.getenv("AWAJ_SENDER_NUMBER", "")  # either name works
    return {
        "base_url": base_url(),
        "token_set": bool(token),
        "sender": sender or None,
        "live": os.getenv("AWAJ_LIVE") == "1" and bool(token) and bool(sender),
        "voice": "male" if os.getenv("AWAJ_VOICE") == "male" else "female",
    }


def bd_mobile(raw) -> Optional[str]:
    """'+8801712345678', '8801712345678', '01712-345678' -> '01712345678'; None if not a Bangladeshi mobile."""
    digits = re.sub(r"\D", "", str(raw or ""))
    digits = re.sub(r"^88(?=01)", "", digits)
    return digits if re.fullmatch(r"01[3-9]\d{8}", digits) else None


def _numbers(phone_numbers: list) -> list[str]:
    out: list[str] = []
    for p in phone_numbers:
        n = bd_mobile(p)
        if n and n not in out:
            out.append(n)
    return out


def _request_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"[:64]  # Awaj wants 16-64 characters


def _call(method: str, path: str, body: Optional[dict] = None) -> dict:
    headers = {"Authorization": f"Bearer {os.getenv('AWAJ_API_TOKEN', '')}", "Accept": "application/json"}
    try:
        res = requests.request(method, f"{base_url()}{path}", headers=headers, json=body, timeout=TIMEOUT_S)
    except requests.RequestException as exc:
        return {"status": None, "ok": False, "data": f"could not reach Awaj ({type(exc).__name__})"}
    try:
        data = res.json()
    except ValueError:
        data = res.text
    return {"status": res.status_code, "ok": res.ok, "data": data}


def _send(path: str, body: dict, numbers: list) -> dict:
    cfg = awaj_config()
    endpoint = f"POST {base_url()}{path}"
    if not numbers:
        return {"dry_run": not cfg["live"], "error": "No valid Bangladeshi mobile number (01XXXXXXXXX)", "request": body}
    if not cfg["live"]:
        return {"dry_run": True, "endpoint": endpoint, "request": body}
    return {"dry_run": False, "endpoint": endpoint, "request_id": body.get("request_id"), "response": _call("POST", path, body)}


def send_tts_call(phone_numbers: list, texts: list, metadata: Optional[dict] = None) -> dict:
    """Read Bangla text aloud to up to 999 numbers (POST /broadcasts/direct-tts). Rate limit: 1 request a second."""
    cfg = awaj_config()
    numbers = _numbers(phone_numbers)
    body = {
        "request_id": _request_id("kv_tts"),
        "sender": cfg["sender"] or "<AWAJ_SENDER>",
        "phone_numbers": numbers,
        "texts": [t[:5000] for t in texts][:10],
        "voice": cfg["voice"],
        "language_code": "bn-BD",
        "metadata": metadata or {},
    }
    return _send("/broadcasts/direct-tts", body, numbers)


def send_audio_call(phone_numbers: list, audio_urls: list, metadata: Optional[dict] = None) -> dict:
    """Play our own audio (public URLs Awaj can fetch) to up to 999 numbers (POST /broadcasts/direct)."""
    cfg = awaj_config()
    numbers = _numbers(phone_numbers)
    body = {
        "request_id": _request_id("kv_audio"),
        "sender": cfg["sender"] or "<AWAJ_SENDER>",
        "phone_numbers": numbers,
        "voices": audio_urls[:10],
        "metadata": metadata or {},
    }
    return _send("/broadcasts/direct", body, numbers)


def send_keypad_survey(phone_numbers: list, question_voice: str, keys: list, officer_key: Optional[str] = None,
                       officer_number: Optional[str] = None, webhook_url: Optional[str] = None,
                       metadata: Optional[dict] = None) -> dict:
    """
    A keypad survey without a dashboard template (POST /v1/surveys/direct-order). The question is a recorded,
    approved voice from the account's library; keys 1-9. The officer key transfers the call.
    """
    cfg = awaj_config()
    numbers = _numbers(phone_numbers)
    officer = bd_mobile(officer_number) if officer_number else None
    options = [{"key": k, "option_type": "voice", "voices": []} for k in keys]
    if officer_key and officer:
        options.append({"key": officer_key, "option_type": "transfer", "transfer_numbers": [officer]})
    body = {
        "request_id": _request_id("kv_survey"),
        "sender": cfg["sender"] or "<AWAJ_SENDER>",
        "phone_numbers": numbers,
        "question_voices": [{"type": "voice", "name": question_voice}],
        "dtmf_options": options,
        "metadata": metadata or {},
        "config": {"retry_count": 1},
    }
    if webhook_url:
        body["webhook_url"] = webhook_url
    return _send("/v1/surveys/direct-order", body, numbers)


def send_template_survey(phone_numbers: list, template_name: str, webhook_url: Optional[str] = None,
                         metadata: Optional[dict] = None) -> dict:
    """A keypad survey from a template built in the Awaj dashboard (POST /surveys)."""
    cfg = awaj_config()
    numbers = _numbers(phone_numbers)
    body = {
        "request_id": _request_id("kv_tpl"),
        "template_name": template_name,
        "sender": cfg["sender"] or "<AWAJ_SENDER>",
        "phone_numbers": numbers,
        "metadata": metadata or {},
    }
    if webhook_url:
        body["webhook_url"] = webhook_url
    return _send("/surveys", body, numbers)


def upload_voice(file_path: str, name: str) -> dict:
    """Upload a recorded voice (mp3, wav, ogg, m4a, aac, webm or flac, up to 10 MB) for a keypad menu."""
    path = Path(file_path)
    size = path.stat().st_size
    live = awaj_config()["live"]
    if size > 10 * 1024 * 1024:
        return {"dry_run": not live, "error": "Awaj accepts voices up to 10 MB"}
    if not live:
        return {"dry_run": True, "endpoint": f"POST {base_url()}/voices/upload",
                "request": {"name": name, "audio": f"{path.name} ({round(size / 1024)} KB)"}}
    with open(path, "rb") as f:
        res = requests.post(
            f"{base_url()}/voices/upload",
            headers={"Authorization": f"Bearer {os.getenv('AWAJ_API_TOKEN', '')}", "Accept": "application/json"},
            data={"name": name}, files={"audio": (path.name, f)}, timeout=60,
        )
    try:
        data = res.json()
    except ValueError:
        data = None
    return {"dry_run": False, "status": res.status_code, "data": data}


def tts_status(request_id: str) -> dict:
    """Processing state of a Direct TTS request: pending, processing, completed (with broadcast_id) or failed."""
    return _call("GET", f"/broadcasts/direct-tts/{requests.utils.quote(request_id)}/status")


def broadcast_result(broadcast_id) -> dict:
    """Per-number outcome once a broadcast is complete: answered, not answered, busy, with call seconds."""
    return _call("GET", f"/broadcasts/{requests.utils.quote(str(broadcast_id))}/result")


def balance() -> dict:
    return _call("GET", "/balance")


def senders() -> dict:
    return _call("GET", "/senders")


def list_voices() -> dict:
    """The account's recorded voices and whether Awaj approved them."""
    return _call("GET", "/voices")
