"""
Tests for the farmer's call (the conversation state machine), with keypad and speech.
Events go to a temporary file; Gemini is off unless a fake is given.
"""

import pytest

from config.settings import DATABASE_URL
from src import events
from src.database import init_database
from src.voice.bangla_numbers import extract_numbers
from src.voice.conversation import CLOSING, Conversation, HELP, OFFICER

_, Session = init_database(DATABASE_URL)


@pytest.fixture(autouse=True)
def temp_events(tmp_path, monkeypatch):
    monkeypatch.setenv("KV_EVENTS_PATH", str(tmp_path / "events.jsonl"))


class Call:
    def __init__(self, gemini=None):
        self.conv = Conversation(Session, gemini=gemini)
        self.last = self.conv.turn(None, {"kind": "start"})

    def press(self, digits):
        self.last = self.conv.turn(self.last["state"], {"kind": "keypad", "digits": digits})
        return self.last

    def say(self, text):
        self.last = self.conv.turn(self.last["state"], {"kind": "speech", "text": text})
        return self.last

    @property
    def step(self):
        return self.last["state"]["step"]


def keypad_call_to_advice(call):
    call.press("1")
    call.press("50#")      # maunds
    call.press("20000#")   # cash needed
    call.press("3#")       # within days
    call.press("18#")      # trader's offer per kg
    call.press("0#")       # no dadon
    assert call.step == "sell_confirm"
    assert "৫০ মণ আলু" in call.last["say"] and "২০,০০০ টাকা" in call.last["say"]
    return call.press("1")


def test_greeting_has_consent_and_menu():
    call = Call()
    assert "পরামর্শ দিতে ব্যবহার হবে" in call.last["say"]
    assert call.last["expects"] == "menu"
    assert call.last["keys"] == ["1", "2", "3", "9"]


def test_keypad_call_gives_taka_advice_and_ends_with_repeat_and_officer():
    call = Call()
    reply = keypad_call_to_advice(call)
    assert call.step == "sell_advice"
    assert reply["say"].endswith(CLOSING)
    assert reply["decision"]["recommended"] in ("sell_now", "sell_part", "store_review", "group_sell")
    assert reply["narration"]["status"] == "template"  # Gemini is off in tests
    assert reply["sms_text"].startswith("কৃষিভল্ট:")


def test_every_advice_number_is_from_the_engine_or_the_farmer():
    call = Call()
    reply = keypad_call_to_advice(call)
    template = reply["narration"]["template"]
    allowed = set()
    for s in reply["decision"]["scenarios"]:
        for key in ("expected_proceeds_tk", "price_per_kg", "sell_maunds", "store_maunds"):
            allowed.update(extract_numbers(str(s[key])))
            allowed.update(extract_numbers(str(round(s[key], -2))))
            allowed.update(extract_numbers(str(round(s[key], 1))))
    allowed.update(["50", "20000", "3", "18"])
    for s in reply["decision"]["scenarios"]:  # totals are read rounded to the nearest 100 taka
        allowed.add(str(int(round(s["expected_proceeds_tk"] / 100) * 100)))
    assert set(extract_numbers(template)) <= allowed


def test_action_press_records_event_for_partner():
    call = Call()
    keypad_call_to_advice(call)
    assert "2" in call.last["keys"]
    reply = call.press("2")
    assert call.step == "sell_done"
    event = reply["event"]
    assert event["for"] in ("buyer", "cold_storage")
    assert event["demo"] is True
    assert events.recent(5)[0]["ref"] == event["ref"]
    assert "(ডেমো)" in reply["sms_text"]


def test_dialect_speech_fills_all_values_then_correction_is_read_back():
    call = Call()
    call.say(
        "হামার শিবগঞ্জের জমিতে ৮০ মণ আলু উঠছে বাহে। পোলাপানের স্কুলের বেতন আর মহাজনের সার বাবদ "
        "জরুরি ২৫ হাজার টেকা নাগবে ৪ দিনের মইধ্যে। স্থানীয় ফড়িয়া ১৮ টেকা কেজি দিবার চায়। "
        "আড়তদারের কাছে ২০ হাজার টেকা দাদন নেওয়া আছে।"
    )
    assert call.step == "sell_confirm"
    assert "দাদন ২০,০০০ টাকা" in call.last["say"]
    call.say("না, ৯০ মণ")
    assert call.step == "sell_confirm"
    assert "৯০ মণ আলু" in call.last["say"]
    call.say("হ্যাঁ ঠিক আছে")
    assert call.step == "sell_advice"


def test_two_failures_offer_officer_callback():
    call = Call()
    call.say("ইয়ে মানে")
    assert call.step == "menu"
    call.say("কী জানি")
    assert call.step == "help"
    assert call.last["say"] == HELP
    reply = call.press("9")
    assert reply["say"] == OFFICER
    assert reply["done"] is True
    assert reply["event"]["kind"] == "officer_callback"


def test_not_ready_menus_are_honest_and_return():
    call = Call()
    call.press("2")
    assert "চালু হয়নি" in call.last["say"]
    call.press("0")
    assert call.step == "menu"


def test_no_cash_need_skips_deadline_question():
    call = Call()
    call.press("1")
    call.press("40#")
    call.press("0#")
    assert call.last["state"]["asking"] == "offer_per_kg"


def test_star_returns_to_menu_while_answering():
    call = Call()
    call.press("1")
    call.press("*")
    assert call.step == "menu"


def test_rejected_gemini_rewording_falls_back_to_template():
    class Rewords:
        available = True
        model_used = "fake"

        def json(self, prompt):
            return None

        def text(self, prompt, system=None):
            return "এখনই বেচে দিন, এক লাখ টাকা পাবেন।"  # a number the engine never gave

    call = Call(gemini=Rewords())
    reply = keypad_call_to_advice(call)
    assert reply["narration"]["status"] == "gemini_rejected"
    assert reply["say"].startswith(reply["narration"]["template"])
