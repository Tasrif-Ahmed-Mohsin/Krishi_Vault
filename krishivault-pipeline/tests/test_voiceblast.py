import pytest
from src.notify.voiceblast import (
    bd_mobile,
    make_g711_wav,
    VoiceBlastClient,
)


def test_bd_mobile_formatting():
    assert bd_mobile("01712345678") == "01712345678"
    assert bd_mobile("+8801812345678") == "01812345678"
    assert bd_mobile("8801912345678") == "01912345678"
    assert bd_mobile("01912-345678") == "01912345678"
    assert bd_mobile("invalid") is None
    assert bd_mobile("01234567890") is None  # 012 is not valid BD mobile prefix


def test_make_g711_wav_structure():
    # 8000 samples of silence = 1 second of 16-bit PCM at 8000Hz (16000 bytes)
    silent_pcm = b"\x00\x00" * 8000
    wav_bytes = make_g711_wav(silent_pcm)

    # Check WAV header
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"
    assert wav_bytes[12:16] == b"fmt "
    # Format code 7 = WAVE_FORMAT_MULAW
    import struct
    fmt_code, channels, sample_rate = struct.unpack("<HHI", wav_bytes[20:28])
    assert fmt_code == 7
    assert channels == 1
    assert sample_rate == 8000
    # 8-bit mono = 8000 bytes of audio data
    assert b"data" in wav_bytes
    assert len(wav_bytes) == 36 + 2 + 8 + 8000


def test_voiceblast_dry_run():
    client = VoiceBlastClient(live=False)
    res = client.send_call("01712345678")
    assert res["success"] is True
    assert res.get("dry_run") is True
    assert res["phone"] == "01712345678"


def test_voiceblast_invalid_number():
    client = VoiceBlastClient(live=False)
    res = client.send_call("12345")
    assert res["success"] is False
    assert "Bangladeshi mobile" in res["error"]
