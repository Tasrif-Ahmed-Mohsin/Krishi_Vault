"""
call_audio.py — Pre-warm and cache Bangla advice audio for VoiceBlast calls.

Usage::
    from src.notify.call_audio import prewarm, voiceblast_audio_id, is_advice, call_text

The main entry points are:
- ``call_text(advice)``       Build the full call script from advice text.
- ``prepare(advice, tts)``    Synthesise and cache a G.711 WAV; return the Path.
- ``voiceblast_audio_id(advice, vb, tts)``  Upload once, cache the ID.
- ``prewarm(advice, vb, tts)``  Do the above in a background daemon thread.
- ``is_advice(say)``          True when the text looks like store-or-sell advice.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from loguru import logger

if TYPE_CHECKING:
    from src.notify.voiceblast import VoiceBlastClient
    from src.voice.tts_generator import BengaliVoiceSynthesizer

# ------------------------------------------------------------------ paths
_BASE = Path(__file__).parent.parent.parent
CACHE_DIR = _BASE / "data" / "audio_out" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
VB_IDS_FILE = CACHE_DIR / "voiceblast_ids.json"
_ids_lock = threading.Lock()

# ------------------------------------------------------------------ helpers

# Keypad menu suffixes that must be stripped before the call
_KEYPAD_PATTERNS = re.compile(
    r"[।.]*\s*("
    r"আরও জানতে \d চাপুন"
    r"|চাইতে \d চাপুন"
    r"|নাম ও নম্বর ছাড়া.*"
    r"|আবার শুনতে \d"
    r"|মূল মেনুতে যেতে \d"
    r"|বিস্তারিত জানতে \d"
    r"|সম্মত হলে \d চাপুন"
    r").*$",
    re.DOTALL,
)


def call_text(advice: str) -> str:
    """
    Build the full telephone call script from the engine's advice text.

    - Prepends a standard greeting.
    - Cuts everything from the first keypad-choice sentence onward.
    - Appends a closing "ধন্যবাদ।".
    - Never changes any number in the text.
    """
    greeting = "আসসালামু আলাইকুম, কৃষিভল্ট থেকে বলছি। "
    # Strip keypad menu lines that should not be read in a voice call
    body = _KEYPAD_PATTERNS.sub("", advice).strip()
    # Also strip trailing sentence fragment that begins with কৃষিভল্ট-specific nav
    body = re.sub(
        r"\s*(এখন|এরপর|তারপর)?\s*\*\s+.*$", "", body, flags=re.DOTALL
    ).strip()
    closing = " ধন্যবাদ।"
    return greeting + body + closing


def is_advice(say: str) -> bool:
    """
    Return True when the text looks like a store-or-sell advice (contains a
    quantity in sacks and a sell/store recommendation).
    """
    return "বস্তা" in say and ("বেচুন" in say or "রাখুন" in say)


def _sha1_prefix(text: str, length: int = 16) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:length]


def _wav_cache_path(text: str) -> Path:
    return CACHE_DIR / f"{_sha1_prefix(text)}.wav"


def _synth_google(tts: "BengaliVoiceSynthesizer", text: str, out: Path) -> bool:
    """Synthesise via Google Cloud TTS → G.711 WAV; return True on success."""
    try:
        from google.cloud import texttospeech
        from src.notify.voiceblast import make_g711_wav

        s_input = texttospeech.SynthesisInput(text=text[:4800])
        voice = texttospeech.VoiceSelectionParams(
            language_code="bn-BD",
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
        )
        audio_cfg = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=8000,
        )
        resp = tts.client.synthesize_speech(
            input=s_input, voice=voice, audio_config=audio_cfg, timeout=20
        )
        # Google LINEAR16 at 8 kHz returns a WAV file; skip the 44-byte header
        pcm = resp.audio_content[44:]
        wav = make_g711_wav(pcm)
        out.write_bytes(wav)
        logger.info(f"call_audio: Google TTS → {out.name} ({len(wav)} bytes)")
        return True
    except Exception as exc:
        logger.warning(f"call_audio: Google TTS failed: {exc}")
        return False


def _synth_gtts_fallback(text: str, out: Path) -> bool:
    """Synthesise via gTTS + miniaudio → G.711 WAV; return True on success."""
    try:
        import io as _io
        import miniaudio
        from gtts import gTTS
        from src.notify.voiceblast import make_g711_wav

        buf = _io.BytesIO()
        gTTS(text=text, lang="bn", slow=False).write_to_fp(buf)
        buf.seek(0)

        # Decode the mp3 to 16-bit mono 8 kHz PCM
        decoded = miniaudio.decode(
            buf.read(), output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=1, sample_rate=8000
        )
        pcm = bytes(decoded.samples)
        wav = make_g711_wav(pcm)
        out.write_bytes(wav)
        logger.info(f"call_audio: gTTS fallback → {out.name} ({len(wav)} bytes)")
        return True
    except Exception as exc:
        logger.warning(f"call_audio: gTTS fallback failed: {exc}")
        return False


def prepare(advice: str, tts_service: "BengaliVoiceSynthesizer") -> Optional[Path]:
    """
    Synthesise the call audio for *advice* and cache it as a G.711 WAV.

    Returns the Path to the cached WAV, or None on total failure.
    The cache key is SHA-1(call_text(advice))[:16] so the same text always
    reuses the same file.
    """
    text = call_text(advice)
    out = _wav_cache_path(text)
    if out.exists():
        return out

    # Try Google Cloud TTS first; fall back to gTTS + miniaudio
    if tts_service is not None and getattr(tts_service, "ready", False):
        if _synth_google(tts_service, text, out):
            return out
    if _synth_gtts_fallback(text, out):
        return out

    logger.error("call_audio: both TTS methods failed; no audio prepared.")
    return None


# ------------------------------------------------------------------ VoiceBlast ID cache

def _load_ids() -> dict:
    if VB_IDS_FILE.exists():
        try:
            return json.loads(VB_IDS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_ids(ids: dict) -> None:
    try:
        VB_IDS_FILE.write_text(json.dumps(ids, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning(f"call_audio: could not save voiceblast_ids.json: {exc}")


def voiceblast_audio_id(
    advice: str,
    vb: "VoiceBlastClient",
    tts_service: "BengaliVoiceSynthesizer",
) -> Optional[int]:
    """
    Return the VoiceBlast audio_file_id for *advice*, uploading at most once
    per unique text.  The id is cached in data/audio_out/cache/voiceblast_ids.json
    (thread-safe).
    """
    text = call_text(advice)
    key = _sha1_prefix(text)

    with _ids_lock:
        ids = _load_ids()
        if key in ids:
            logger.debug(f"call_audio: reusing VoiceBlast audio ID {ids[key]} for key {key}")
            return ids[key]

    # Synthesise
    wav_path = prepare(advice, tts_service)
    if wav_path is None:
        logger.error("call_audio: could not prepare audio; cannot upload to VoiceBlast.")
        return None

    # Upload
    audio_id = vb.upload_audio(wav_path, filename=f"kv_{key}.wav")
    if audio_id is None:
        logger.error("call_audio: VoiceBlast upload returned None.")
        return None

    with _ids_lock:
        ids = _load_ids()
        ids[key] = audio_id
        _save_ids(ids)

    logger.info(f"call_audio: uploaded and cached VoiceBlast audio ID {audio_id} for key {key}")
    return audio_id


def prewarm(
    advice: str,
    vb: "VoiceBlastClient",
    tts_service: "BengaliVoiceSynthesizer",
) -> None:
    """
    Pre-warm the audio for *advice* in a daemon thread so the dial endpoint
    can use the cached ID immediately.  Errors are logged but do not propagate.
    """
    def _run() -> None:
        try:
            voiceblast_audio_id(advice, vb, tts_service)
        except Exception as exc:
            logger.error(f"call_audio.prewarm: unexpected error: {exc}")

    t = threading.Thread(target=_run, daemon=True, name="call_audio_prewarm")
    t.start()
