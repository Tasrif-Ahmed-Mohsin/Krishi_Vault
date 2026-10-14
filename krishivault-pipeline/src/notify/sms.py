"""
Bangla SMS through the REVE Systems gateway (the account Awaj's support set up; smpp.revesms.com)
================================================================================================
Ported from Mati Kohon's sms.ts (reference/mati_kohon_code/).

  SMS_API_KEY, SMS_SECRET_KEY  from the REVE panel; never commit them
  SMS_SENDER_ID                the sender ID on the account
  SMS_BASE_URL                 default https://smpp.revesms.com:7790 (the HTTPS API port in REVE's notes)
  SMS_LIVE=1                   the switch that turns dry runs into real, billed messages

Without them every send returns the request it would make ({"dry_run": True, ...}) with the keys masked.
The API is GET /sendtext?apikey&secretkey&callerID&toUser&messageContent; numbers go as 8801XXXXXXXXX.
"""

import os
import re

import requests

from src.notify.awaj import bd_mobile

TIMEOUT_S = 20


def base_url() -> str:
    return (os.getenv("SMS_BASE_URL") or "https://smpp.revesms.com:7790").rstrip("/")


def sms_config() -> dict:
    api_key = os.getenv("SMS_API_KEY", "")
    secret = os.getenv("SMS_SECRET_KEY", "")
    sender = os.getenv("SMS_SENDER_ID", "")
    configured = bool(api_key and secret and sender)
    return {
        "configured": configured,
        "live": os.getenv("SMS_LIVE") == "1" and configured,
        "sender": sender or None,
        "gateway": base_url(),
    }


def sms_parts(text: str) -> int:
    """Unicode Bangla goes 70 characters to a part (67 when the message is split); plain text 160 (153)."""
    unicode = re.search(r"[^\x00-\x7F]", text) is not None
    single, multi = (70, 67) if unicode else (160, 153)
    return 1 if len(text) <= single else -(-len(text) // multi)


def send_sms(phone: str, text: str) -> dict:
    cfg = sms_config()
    local = bd_mobile(phone)
    to_user = f"88{local}" if local else None
    request = {"callerID": cfg["sender"] or "<SMS_SENDER_ID>", "toUser": to_user, "messageContent": text,
               "parts": sms_parts(text)}
    masked = f"GET {cfg['gateway']}/sendtext?apikey=***&secretkey=***&callerID=…&toUser=…&messageContent=…"
    if not to_user:
        return {"dry_run": not cfg["live"], "error": "phone must be a Bangladeshi mobile number (01XXXXXXXXX)", "request": request}
    if not cfg["live"]:
        return {"dry_run": True, "endpoint": masked, "request": request}
    params = {
        "apikey": os.getenv("SMS_API_KEY"), "secretkey": os.getenv("SMS_SECRET_KEY"),
        "callerID": cfg["sender"], "toUser": to_user, "messageContent": text,
    }
    try:
        res = requests.get(f"{cfg['gateway']}/sendtext", params=params, timeout=TIMEOUT_S)
    except requests.RequestException as exc:
        # The exception text holds the full URL with the keys in it, so only its type is returned
        return {"dry_run": False, "endpoint": masked, "error": f"could not reach the SMS gateway ({type(exc).__name__})"}
    try:
        response = res.json()
    except ValueError:  # the gateway may answer in plain text
        response = res.text
    return {"dry_run": False, "endpoint": masked, "status": res.status_code, "response": response}
