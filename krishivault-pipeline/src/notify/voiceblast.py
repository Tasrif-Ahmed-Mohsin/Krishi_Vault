"""
KrishiVault VoiceBlast Voice Telephony Client
=============================================
Automates outbound voice calls through the SysTech VoiceBlast platform (http://voice.smsvaults.work)
using session authentication, without requiring an external API key.

- Encodes Bengali speech into G.711 u-law 8kHz mono WAV (telephony standard).
- Uploads audio files to the File Library (POST /customer/library/upload).
- Dispatches direct phone calls through caller DID 09612010692 (POST /customer/campaigns/demo-call).
- Tracks live call outcome status (Answered, Failed, Busy) from /customer/demo-history.
"""

import io
import os
import re
import struct
from pathlib import Path
from typing import Optional, List, Dict, Any

import requests
from bs4 import BeautifulSoup
from loguru import logger
from dotenv import load_dotenv

# Ensure environment is loaded
BASE_DIR = Path(__file__).parent.parent.parent
load_dotenv(BASE_DIR / ".env")

try:
    import audioop
except ImportError:
    audioop = None


def _linear_to_ulaw_byte(sample: int) -> int:
    """Fallback 16-bit linear PCM to 8-bit G.711 u-law byte conversion."""
    BIAS = 0x84
    CLIP = 32635
    sign = (sample >> 8) & 0x80
    if sign:
        sample = -sample
    if sample > CLIP:
        sample = CLIP
    sample += BIAS
    exponent = 7
    for exp, mask in enumerate([0x4000, 0x2000, 0x1000, 0x0800, 0x0400, 0x0200, 0x0100]):
        if sample & mask:
            exponent = 7 - exp
            break
    mantissa = (sample >> (exponent + 3)) & 0x0F
    ulaw = ~(sign | (exponent << 4) | mantissa) & 0xFF
    return ulaw


def make_g711_wav(pcm_16bit_8k: bytes) -> bytes:
    """
    Encodes raw 16-bit signed PCM audio at 8,000 Hz mono into standard G.711 u-law WAV.
    Format Code 7 (WAVE_FORMAT_MULAW), 8000 Hz, 8-bit mono.
    """
    if audioop is not None:
        ulaw_data = audioop.lin2ulaw(pcm_16bit_8k, 2)
    else:
        count = len(pcm_16bit_8k) // 2
        samples = struct.unpack(f"<{count}h", pcm_16bit_8k)
        ulaw_data = bytes(_linear_to_ulaw_byte(s) for s in samples)

    data_len = len(ulaw_data)
    out = io.BytesIO()

    # RIFF header
    out.write(b"RIFF")
    out.write(struct.pack("<I", 36 + 2 + data_len))
    out.write(b"WAVE")

    # fmt subchunk
    out.write(b"fmt ")
    out.write(struct.pack("<I", 18))  # 18 bytes for format 7 with cbSize
    out.write(struct.pack("<H", 7))   # 7 = WAVE_FORMAT_MULAW
    out.write(struct.pack("<H", 1))   # 1 channel (mono)
    out.write(struct.pack("<I", 8000))  # 8000 Hz sample rate
    out.write(struct.pack("<I", 8000))  # 8000 bytes/sec
    out.write(struct.pack("<H", 1))   # block align (1 byte per sample)
    out.write(struct.pack("<H", 8))   # 8 bits per sample
    out.write(struct.pack("<H", 0))   # cbSize = 0

    # data subchunk
    out.write(b"data")
    out.write(struct.pack("<I", data_len))
    out.write(ulaw_data)

    return out.getvalue()


def bd_mobile(raw: Any) -> Optional[str]:
    """Clean phone number into Bangladeshi standard 01XXXXXXXXX."""
    digits = re.sub(r"\D", "", str(raw or ""))
    digits = re.sub(r"^88(?=01)", "", digits)
    return digits if re.fullmatch(r"01[3-9]\d{8}", digits) else None


def _is_login_page(html: str) -> bool:
    """Return True if the HTML looks like the VoiceBlast login form."""
    h = html.lower()
    return (
        "<form" in h and ("password" in h or "login" in h)
        and "dashboard" not in h
    )


class VoiceBlastClient:
    """Session-based client for SysTech VoiceBlast voice calls."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        caller_id: Optional[str] = None,
        default_audio_id: Optional[int] = None,
        live: Optional[bool] = None,
    ):
        self.base_url = (base_url or os.getenv("VOICEBLAST_BASE_URL", "http://voice.smsvaults.work")).rstrip("/")
        self.username = username or os.getenv("VOICEBLAST_USER", "")
        self.password = password or os.getenv("VOICEBLAST_PASSWORD", "")
        self.caller_id = caller_id or os.getenv("VOICEBLAST_CALLER_ID", "")
        def_id = default_audio_id or os.getenv("VOICEBLAST_DEFAULT_AUDIO_ID", "1106")
        self.default_audio_id = int(def_id) if str(def_id).isdigit() else 1106
        self.live = live if live is not None else (os.getenv("VOICEBLAST_LIVE", "0") == "1")

        self.session = requests.Session()
        self._logged_in = False

    def login(self) -> bool:
        """
        Authenticate session with VoiceBlast portal.

        After the POST we fetch /customer/dashboard to confirm we really landed on
        the dashboard and are not still looking at the login form.  Any redirect to
        the login page or a login-form body means the credentials were rejected.
        """
        if not (self.username and self.password):
            logger.warning("VoiceBlast username or password not configured.")
            return False
        self._logged_in = False  # reset before each attempt
        try:
            res = self.session.post(
                f"{self.base_url}/login",
                data={"username": self.username, "password": self.password},
                timeout=12,
                allow_redirects=True,
            )
            # Confirm we are on the dashboard, not still on the login page
            check = self.session.get(f"{self.base_url}/customer/dashboard", timeout=10)
            if _is_login_page(check.text):
                logger.error(
                    "VoiceBlast login failed: credentials rejected (dashboard returned login form). "
                    f"HTTP {res.status_code} after POST, then {check.status_code} on dashboard."
                )
                return False
            # Quick sanity: look for something that only appears when logged in
            if "dashboard" not in check.url.lower() and "dashboard" not in check.text.lower():
                logger.error(
                    f"VoiceBlast login uncertain: dashboard URL is '{check.url}', "
                    "no 'dashboard' keyword found in body. Treating as failed."
                )
                return False
            self._logged_in = True
            logger.info(f"VoiceBlast authenticated successfully as '{self.username}'.")
            return True
        except Exception as exc:
            logger.error(f"VoiceBlast connection error during login: {exc}")
            return False

    def _ensure_session(self) -> bool:
        """Ensure active authenticated session."""
        if self._logged_in:
            return True
        return self.login()

    def _handle_response(self, res: requests.Response, context: str) -> Optional[dict]:
        """
        Parse a JSON response safely.  If we get a login page or non-JSON body,
        reset _logged_in and return None with a descriptive log message.
        Returns the parsed dict on success, or None on failure.
        """
        # Detect session expiry / redirect back to login
        if _is_login_page(res.text):
            logger.warning(
                f"VoiceBlast session expired ({context}): response was the login page "
                f"(HTTP {res.status_code}). Resetting session."
            )
            self._logged_in = False
            return None
        if res.status_code in (401, 403):
            logger.warning(
                f"VoiceBlast auth error ({context}): HTTP {res.status_code}. Resetting session."
            )
            self._logged_in = False
            return None
        try:
            return res.json()
        except Exception:
            body_preview = res.text[:200].replace("\n", " ")
            logger.error(
                f"VoiceBlast non-JSON response ({context}): HTTP {res.status_code}, "
                f"body: {body_preview!r}"
            )
            return None

    def _request_with_retry(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Make a request; if the response looks like a login page or a 401/403,
        re-login once and retry once.
        """
        try:
            res = getattr(self.session, method)(url, **kwargs)
        except Exception as exc:
            logger.error(f"VoiceBlast network error ({method.upper()} {url}): {exc}")
            return None

        if _is_login_page(res.text) or res.status_code in (401, 403):
            logger.info("VoiceBlast session lost; re-logging in and retrying once...")
            self._logged_in = False
            if not self.login():
                return res  # return the failed response so caller can surface the error
            try:
                res = getattr(self.session, method)(url, **kwargs)
            except Exception as exc:
                logger.error(f"VoiceBlast retry network error: {exc}")
                return None
        return res

    def get_balance(self) -> Optional[str]:
        """Fetch current prepaid balance."""
        if not self._ensure_session():
            return None
        try:
            res = self._request_with_retry("get", f"{self.base_url}/customer/dashboard", timeout=10)
            if res is None:
                return None
            soup = BeautifulSoup(res.text, "html.parser")
            pill = soup.find(class_="balance-pill")
            if pill:
                return pill.text.strip()
            # Some layouts show balance in a different element; try a broader search
            for tag in soup.find_all(string=re.compile(r"balance|Balance|৳", re.I)):
                parent = tag.parent
                if parent:
                    txt = parent.get_text(strip=True)
                    if re.search(r"[\d৳]", txt):
                        return txt[:60]
            return None
        except Exception as exc:
            logger.warning(f"Failed to fetch VoiceBlast balance: {exc}")
            return None

    def get_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """Fetch recent demo call logs and statuses."""
        if not self._ensure_session():
            return []
        try:
            res = self._request_with_retry("get", f"{self.base_url}/customer/demo-history", timeout=10)
            if res is None:
                return []
            soup = BeautifulSoup(res.text, "html.parser")
            table = soup.find("table")
            if not table:
                return []
            rows = table.find_all("tr")
            history = []
            for tr in rows[1 : limit + 1]:
                cells = [td.text.strip() for td in tr.find_all("td")]
                if len(cells) >= 5 and "No demo calls" not in cells[0]:
                    history.append({
                        "phone": cells[0],
                        "caller_id": cells[1],
                        "status": cells[2],
                        "cause": cells[3],
                        "time": cells[4],
                    })
            return history
        except Exception as exc:
            logger.warning(f"Failed to fetch VoiceBlast demo history: {exc}")
            return []

    def upload_audio(self, file_path: Path, filename: Optional[str] = None) -> Optional[int]:
        """Upload a G.711 WAV audio file to the File Library and return its audio_file_id."""
        if not self._ensure_session():
            return None
        path = Path(file_path)
        if not path.is_file():
            logger.error(f"Audio file does not exist: {path}")
            return None

        fn = filename or path.name
        try:
            with open(path, "rb") as f:
                res = self._request_with_retry(
                    "post",
                    f"{self.base_url}/customer/library/upload",
                    files={"file": (fn, f, "audio/wav")},
                    data={"file_type": "audio"},
                    timeout=30,
                )
            if res is None:
                return None
            data = self._handle_response(res, "upload_audio")
            if data is None:
                # session expired mid-upload; retry after re-login
                if self.login():
                    with open(path, "rb") as f:
                        res2 = self.session.post(
                            f"{self.base_url}/customer/library/upload",
                            files={"file": (fn, f, "audio/wav")},
                            data={"file_type": "audio"},
                            timeout=30,
                        )
                    data = self._handle_response(res2, "upload_audio_retry")
            if not data or not data.get("success"):
                logger.error(f"VoiceBlast audio upload failed: {data}")
                return None

            lib_res = self._request_with_retry("get", f"{self.base_url}/customer/library", timeout=10)
            if lib_res is None:
                return self.default_audio_id
            soup = BeautifulSoup(lib_res.text, "html.parser")
            for card in soup.find_all(class_="file-card"):
                card_text = card.text.strip()
                if fn in card_text:
                    cid = card.get("id", "")
                    if cid.startswith("file-"):
                        file_id = int(cid.replace("file-", ""))
                        logger.info(f"Uploaded audio '{fn}' with ID: {file_id}")
                        return file_id
            return self.default_audio_id
        except Exception as exc:
            logger.error(f"Error uploading audio to VoiceBlast: {exc}")
            return None

    def send_call(
        self,
        phone: str,
        audio_file_id: Optional[int] = None,
        caller_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches a live voice call to a Bangladeshi mobile number.

        Args:
            phone: Target phone number (e.g. '01712345678')
            audio_file_id: Specific uploaded audio ID; defaults to standard welcome audio.
            caller_id: Outbound DID caller ID; defaults to account assigned DID.
        """
        mobile = bd_mobile(phone)
        cid = caller_id or self.caller_id
        aid = audio_file_id or self.default_audio_id

        if not mobile:
            return {
                "success": False,
                "error": "Phone number must be a valid Bangladeshi mobile (01XXXXXXXXX)",
            }

        if not self.live:
            logger.info(f"[DRY-RUN] Voice call would dial {mobile} via {cid} with audio ID {aid}")
            return {
                "success": True,
                "dry_run": True,
                "phone": mobile,
                "caller_id": cid,
                "audio_file_id": aid,
                "message": f"[DRY-RUN] Outbound call to {mobile} simulated.",
            }

        if not self._ensure_session():
            return {"success": False, "error": "Could not authenticate with voice platform"}

        payload = {
            "phone": mobile,
            "caller_id": cid,
            "audio_file_id": str(aid),
        }

        try:
            logger.info(f"Dialing {mobile} via VoiceBlast caller ID {cid} (Audio ID: {aid})...")
            res = self._request_with_retry(
                "post",
                f"{self.base_url}/customer/campaigns/demo-call",
                json=payload,
                timeout=15,
            )
            if res is None:
                return {"success": False, "error": "No response from VoiceBlast (network error)"}

            data = self._handle_response(res, "send_call")
            if data is None:
                return {
                    "success": False,
                    "error": f"VoiceBlast returned a non-JSON or login-page response (HTTP {res.status_code}). "
                             "Session may have expired or credentials may be wrong.",
                }
            if data.get("success"):
                logger.info(f"Voice call successfully initiated to {mobile}!")
                return {
                    "success": True,
                    "phone": mobile,
                    "caller_id": cid,
                    "audio_file_id": aid,
                    "message": data.get("message", "Demo call initiated!"),
                }
            logger.warning(f"Voice call rejected by platform: {data}")
            return {"success": False, "error": data.get("error", "Call request failed")}
        except Exception as exc:
            logger.error(f"Error executing voice call: {exc}")
            return {"success": False, "error": f"Connection error: {type(exc).__name__}: {exc}"}


# ============================================================ Official REST Broadcast API (103.174.214.170)

class BroadcastApiClient:
    """
    Official SysTech Voice Broadcast REST API client (http://103.174.214.170:7002/broadcast).
    Documented in 'APIs for Voice Broadcast.pdf'.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        caller_id: Optional[str] = None,
        live: Optional[bool] = None,
    ):
        import json
        self._json = json
        self.base_url = (base_url or os.getenv("BROADCAST_BASE_URL", "http://103.174.214.170:7002/broadcast/index.php/api")).rstrip("/")
        self.username = username or os.getenv("BROADCAST_USER", "")
        self.password = password or os.getenv("BROADCAST_PASS", "")
        self.caller_id = caller_id or os.getenv("BROADCAST_CALLER_ID", "")
        self.live = live if live is not None else (os.getenv("BROADCAST_LIVE", "0") == "1")

    def _headers(self) -> Dict[str, str]:
        return {"user": self.username, "pass": self.password}

    def get_balance(self) -> Optional[str]:
        """Check voice balance via POST /api/get_balance_info."""
        try:
            res = requests.post(f"{self.base_url}/get_balance_info", headers=self._headers(), timeout=10)
            data = res.json()
            if data.get("success"):
                return str(data.get("balance", ""))
            return None
        except Exception as exc:
            logger.warning(f"Broadcast API balance error: {exc}")
            return None

    def send_broadcast(
        self,
        phone: str,
        audio_file_path: Path,
        retry: int = 0,
        caller_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Starts an outbound voice broadcast call via POST /api/do_blast.
        Directly uploads the G.711 WAV audio and dispatches the call.
        """
        mobile = bd_mobile(phone)
        cid = caller_id or self.caller_id
        if not mobile:
            return {"success": False, "error": "Phone number must be a valid Bangladeshi mobile (01XXXXXXXXX)"}

        path = Path(audio_file_path)
        if not path.is_file():
            return {"success": False, "error": f"Voice audio file not found: {path}"}

        dst = f"88{mobile}"
        if not self.live:
            logger.info(f"[DRY-RUN] Broadcast call would dial {dst} via {cid} with audio {path.name}")
            return {
                "success": True,
                "dry_run": True,
                "phone": mobile,
                "caller_id": cid,
                "audio_file": path.name,
                "message": f"[DRY-RUN] Broadcast to {dst} simulated.",
            }

        try:
            logger.info(f"Dispatching broadcast call to {dst} via {cid} with audio {path.name}...")
            with open(path, "rb") as f:
                files = {"voice": (path.name, f, "audio/wav")}
                data = {
                    "callerid": cid,
                    "retry": str(retry),
                    "arr_dst": self._json.dumps([dst]),
                }
                res = requests.post(f"{self.base_url}/do_blast", headers=self._headers(), data=data, files=files, timeout=30)
            result = res.json()
            if result.get("success"):
                logger.info(f"Broadcast call queued! Blast ID: {result.get('blast_id')}")
                return {
                    "success": True,
                    "blast_id": result.get("blast_id"),
                    "phone": mobile,
                    "caller_id": cid,
                    "dst_count": result.get("dst_count"),
                    "message": result.get("msg", "Blast started successfully"),
                }
            return {"success": False, "error": result.get("msg", "Broadcast request failed")}
        except Exception as exc:
            logger.error(f"Broadcast API call error: {exc}")
            return {"success": False, "error": f"Broadcast API error: {type(exc).__name__}"}

    def get_report(self, blast_id: int) -> Dict[str, Any]:
        """Fetch delivery report (DLR) for a broadcast via POST /api/get_report."""
        try:
            res = requests.post(
                f"{self.base_url}/get_report",
                headers=self._headers(),
                data={"blast_id": str(blast_id)},
                timeout=12,
            )
            return res.json()
        except Exception as exc:
            logger.warning(f"Broadcast API report error: {exc}")
            return {"success": False, "error": str(exc)}


# Global singleton instances
_voiceblast_instance: Optional[VoiceBlastClient] = None
_broadcast_api_instance: Optional[BroadcastApiClient] = None


def get_voiceblast_client() -> VoiceBlastClient:
    global _voiceblast_instance
    if _voiceblast_instance is None:
        _voiceblast_instance = VoiceBlastClient()
    return _voiceblast_instance


def get_broadcast_api_client() -> BroadcastApiClient:
    global _broadcast_api_instance
    if _broadcast_api_instance is None:
        _broadcast_api_instance = BroadcastApiClient()
    return _broadcast_api_instance
