"""The USSD menu (the plan's Grameenphone USSD channel), played as a gateway would send it."""

import pytest

from src.engine import farmer_signals
from src.voice import ussd


@pytest.fixture(autouse=True)
def temp_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("KV_EVENTS_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.setenv("KV_RUNTIME_DIR", str(tmp_path))


SESSIONS = ["", "1", "1*36", "1*36*25000", "1*36*25000*1", "1*36*25000*2", "1*36*25000*8",
            "2", "2*16", "2*0", "3", "3*36", "4", "4*40"]


def test_two_numbers_give_the_split():
    assert ussd.turn("")["response"].startswith("CON ")
    r = ussd.turn("1*36*25000", month=3, year=2027)
    assert r["response"].startswith("CON ") and "১৯ বস্তা বেচুন" in r["screen"] and "লাভ" in r["screen"]
    assert ussd.turn("1*36*25000*2")["end"]


def test_screens_stay_short():
    for t in SESSIONS:
        assert len(ussd.turn(t)["screen"]) <= 160, t


def test_counting_needs_the_key_and_keeps_no_number():
    ussd.turn("1*36*25000", phone="01711998877")
    assert farmer_signals.district_figures(min_group=1) == []
    ussd.turn("1*36*25000*8", phone="01711998877")
    assert farmer_signals.district_figures(min_group=1)[0]["farmers"] == 1


def test_sms_goes_only_when_asked():
    sent = []
    ussd.turn("1*36*25000*1", phone="01711998877", send_sms=lambda p, t: sent.append((p, t)) or {"dry_run": True})
    assert sent and sent[0][0] == "01711998877" and "কৃষিভল্ট" in sent[0][1]


def test_bad_input_ends_politely():
    for t in ("9", "1*x", "1*0", "2*999"):
        r = ussd.turn(t)
        assert r["end"] and r["screen"] == ussd.BAD
