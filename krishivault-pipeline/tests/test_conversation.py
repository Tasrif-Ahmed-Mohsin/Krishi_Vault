"""
The farmer's call (call preview), with keypad and speech.
Events and saved records go to a temporary folder; Gemini is off unless a fake is given.
"""

import pytest

from src.voice.bangla_numbers import extract_numbers, fmt_taka, to_en_digits
from src.voice.conversation import CLOSING, HELP, HELPER, Conversation, receipt_sms


@pytest.fixture(autouse=True)
def temp_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("KV_EVENTS_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.setenv("KV_RUNTIME_DIR", str(tmp_path))


class Call:
    def __init__(self, gemini=None, **start):
        self.conv = Conversation(gemini=gemini)
        self.last = self.conv.turn(None, {"kind": "start", **start})

    def press(self, digits):
        self.last = self.conv.turn(self.last["state"], {"kind": "keypad", "digits": digits})
        return self.last

    def say(self, text):
        self.last = self.conv.turn(self.last["state"], {"kind": "speech", "text": text})
        return self.last

    @property
    def step(self):
        return self.last["state"]["step"]


def test_greeting_has_consent_and_the_new_menu():
    call = Call()
    assert "পরামর্শ দিতে ব্যবহার হবে" in call.last["say"]
    assert call.last["keys"] == ["1", "2", "3", "4", "9"]
    assert "জামানতে" in call.last["say"]


def test_keypad_advice_at_harvest_with_cash_need():
    call = Call(month=3, year=2027)
    call.press("1")
    call.press("80#")       # maunds
    call.press("16#")       # price today
    call.press("25000#")    # cash needed (no "in cold storage?" question at harvest)
    call.press("4#")        # within days
    assert call.step == "confirm"
    assert "৮০ মণ আলু" in call.last["say"] and "২৫,০০০ টাকা" in call.last["say"]
    r = call.press("1")
    assert call.step == "result"
    assert r["result"]["key"] == "sell_part"
    assert r["say"].endswith(CLOSING)
    assert "বস্তা বেচুন" in r["say"] and "২৫,০০০ টাকার দরকার মিটবে" in r["say"]
    assert {o["key"] for o in r["result"]["options"]} == {"sell_now", "store", "sell_part"}
    assert len(r["result"]["by_month"]) == 10


def test_big_crop_year_says_sell_now_from_speech():
    call = Call(month=3, year=2025)
    r = call.say("হামার ৮০ মণ আলু উঠছে, পাইকার কেজিতে ১৪ টেকা দিবার চায়, ২৫ হাজার টেকা নাগবে ৪ দিনের মইধ্যে")
    assert call.step == "confirm"
    assert r["heard"]["values"]["quantity_kg"]["source"] == "parser"
    r = call.say("হ্যাঁ ঠিক আছে")
    assert r["result"]["key"] == "sell_now"
    assert "ফলন বেশি" in r["say"]


def test_numbers_said_come_from_the_engine():
    call = Call(month=3, year=2024)
    call.press("1"); call.press("80#"); call.press("18#"); call.press("0#")
    r = call.press("1")
    key = r["result"]["key"]
    assert key in ("store", "sell_part")
    chosen = next(o for o in r["result"]["options"] if o["key"] == key)
    said = extract_numbers(r["say"])
    if key == "store":
        assert "250" in said      # the flat rent
    for field in ("money_mean", "gain_vs_now", "money_low"):
        assert to_en_digits(fmt_taka(chosen[field])).replace(",", "") in said


def test_already_in_cold_storage_question_outside_harvest():
    call = Call(month=10, year=2026)
    call.press("1"); call.press("80#"); call.press("22#")
    assert call.last["state"]["asking"] == "in_storage"
    assert call.last["keys"] == ["1", "2"]
    call.press("1"); call.press("0#")
    assert "হিমাগারে আছে" in call.last["say"]
    r = call.press("1")
    assert r["result"]["months_left"] == 2


def test_booking_after_advice_is_saved_and_sms_signed():
    call = Call(month=3, year=2024)
    call.press("1"); call.press("80#"); call.press("18#"); call.press("0#"); call.press("1")
    r = call.press("2")
    assert call.step == "done"
    assert r["event"]["kind"] == "cold_storage_booking"
    sms = receipt_sms(r["state"])
    assert sms and "কৃষিভল্ট" in sms and "(ডেমো)" in sms


def test_tampered_sms_text_is_not_sent():
    call = Call(month=3, year=2024)
    call.press("1"); call.press("80#"); call.press("18#"); call.press("0#")
    r = call.press("1")
    state = dict(r["state"], sms="free gift, call 0000")
    assert receipt_sms(state) is None


def test_tampered_action_is_refused():
    call = Call(month=3, year=2024)
    call.press("1"); call.press("80#"); call.press("18#"); call.press("0#")
    r = call.press("1")
    r["state"]["result"]["next"]["sacks"] = 99999
    out = call.conv.turn(r["state"], {"kind": "keypad", "digits": "2"})
    assert out["event"] is None and "বুঝতে পারিনি" in out["say"]


def test_price_outlook_then_advice():
    call = Call(month=3, year=2027)
    call.press("2"); call.press("16#")
    r = call.press("1")
    assert r["result"]["flow"] == "outlook" and len(r["result"]["months"]) == 10
    assert "নিশ্চিত নয়" in r["say"]
    r = call.press("2")                 # go to the store-or-sell advice, price kept
    assert r["state"]["flow"] == "advice" and "offer_per_kg" in r["state"]["slots"]


def test_group_storage_join():
    call = Call()
    call.press("3"); call.press("40#")
    assert "৪০ বস্তা" in call.last["say"]
    r = call.press("1")
    assert "শিবগঞ্জ" in r["say"] and "রাজি হলে" in r["say"]
    r = call.press("2")
    assert r["event"]["kind"] == "group_storage_join"


def test_loan_flow_applies_to_a_demo_bank():
    call = Call(month=10, year=2026)
    call.press("4"); call.press("40#"); call.press("20#")
    r = call.press("1")
    assert r["result"]["flow"] == "loan" and "ডেমো" in r["say"]
    r = call.press("2")
    assert r["event"]["kind"] == "loan_application"


def test_unknown_price_uses_a_labelled_demo_price():
    call = Call(month=3, year=2027)
    call.press("1"); call.press("50#"); call.press("0#"); call.press("0#")
    r = call.press("1")
    assert "নমুনা হিসেবে" in r["say"] and r["result"]["price_assumed"] is True


def test_correction_at_read_back():
    call = Call()
    call.press("1"); call.press("50#"); call.press("16#"); call.press("0#")
    r = call.say("না, ৬০ মণ")
    assert call.step == "confirm" and "৬০ মণ আলু" in r["say"]


def test_two_failures_lead_to_help_then_helper():
    call = Call()
    call.press("7")
    r = call.press("8")
    assert r["say"] == HELP
    r = call.press("9")
    assert r["say"] == HELPER and r["done"] and r["event"]["kind"] == "helper_callback"


def test_menu_by_speech():
    call = Call()
    r = call.say("দাম কেমন হবে সামনে?")
    assert r["state"]["flow"] == "outlook"


def test_back_to_menu_with_zero():
    call = Call()
    call.press("2"); call.press("16#"); call.press("1")
    r = call.press("0")
    assert call.step == "menu" and r["keys"] == ["1", "2", "3", "4", "9"]


def test_bad_state_from_the_browser_is_cleaned():
    conv = Conversation()
    r = conv.turn({"step": "ask", "asking": "nonsense", "month": "x", "slots": {"a": 1}}, {"kind": "keypad", "digits": "1"})
    assert r["state"]["month"] == 3 and r["state"]["flow"] == "advice"


def test_press_8_counts_the_answer_without_name_or_number():
    from src.engine import farmer_signals
    call = Call(month=3, year=2027, phone="01711998877")
    call.press("1"); call.press("80#"); call.press("16#"); call.press("25000#"); call.press("4#")
    r = call.press("1")
    assert "৮ চাপুন" in r["say"] and "8" in r["keys"]
    assert farmer_signals.district_figures() == []            # nothing is counted without the key
    r = call.press("8")
    assert "গোনা হলো" in r["say"] and "8" not in r["keys"] and call.step == "result"
    assert "৮ চাপুন" not in call.press("1")["say"]             # the repeat no longer asks
    rows = farmer_signals.district_figures(min_group=1)
    assert rows[0]["district"] == "Bogura" and rows[0]["need_cash_within_7_days"] == 1.0
    import json, os
    saved = open(os.path.join(os.environ["KV_RUNTIME_DIR"], "farmer_signals.json"), encoding="utf-8").read()
    assert "01711" not in saved and "998877" not in saved and "phone" not in json.loads(saved)[0]


def test_other_answers_do_not_ask_to_count():
    call = Call(month=3, year=2027)
    call.press("2"); call.press("16#")
    r = call.press("1")
    assert "8" not in r["keys"] and "৮ চাপুন" not in r["say"]
