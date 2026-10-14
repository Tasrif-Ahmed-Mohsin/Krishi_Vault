"""
Tests for the number lock and for understanding the farmer (parser first, Gemini checked).
Gemini is replaced by a fake, so these run without a key or a network.
"""

from config.settings import MAUND_TO_KG
from src.voice.number_lock import check_numbers, narrate
from src.voice.understanding import understand

TEMPLATE = "পরামর্শ: এখন ২৮ মণ বিক্রি করুন। বাকি ২২ মণ হিমাগারে রাখুন। সব মিলিয়ে আনুমানিক ৮০,২০০ টাকা।"


class FakeGemini:
    def __init__(self, json_answer=None, text_answer=None):
        self.json_answer = json_answer
        self.text_answer = text_answer
        self.calls = 0

    available = True

    def json(self, prompt):
        self.calls += 1
        return self.json_answer

    def text(self, prompt, system=None):
        return self.text_answer


def test_rewording_that_keeps_numbers_passes():
    reworded = "ভাই, এখন ২৮ মণ বেচে দিন, আর ২২ মণ হিমাগারে রাখুন। সব মিলে প্রায় ৮০,২০০ টাকা আসবে।"
    result = narrate(TEMPLATE, lambda t: reworded)
    assert result["status"] == "gemini_checked"
    assert result["text"] == reworded


def test_changed_number_falls_back_to_template():
    reworded = "এখন ২৮ মণ বেচুন, বাকি ২২ মণ রাখুন। প্রায় ৮০,০০০ টাকা পাবেন।"
    result = narrate(TEMPLATE, lambda t: reworded)
    assert result["status"] == "gemini_rejected"
    assert result["text"] == TEMPLATE
    assert result["check"]["added"] == ["80000"]
    assert result["check"]["missing"] == ["80200"]


def test_number_written_as_words_still_checked():
    # "আশি হাজার" is 80000, not the engine's 80,200
    check = check_numbers(TEMPLATE, "এখন ২৮ মণ বেচুন, বাকি ২২ মণ রাখুন, পাবেন আশি হাজার টাকা।")
    assert not check.passed
    # the same figure in words passes
    check = check_numbers(TEMPLATE, "এখন ২৮ মণ বেচুন, বাকি ২২ মণ রাখুন, পাবেন আশি হাজার দুইশো টাকা।")
    assert check.passed


def test_dropped_number_and_forbidden_word_fail():
    assert not check_numbers(TEMPLATE, "এখন ২৮ মণ বেচুন, বাকিটা রাখুন। প্রায় ৮০,২০০ টাকা।").passed
    assert not check_numbers(TEMPLATE, "এখন ২৮ মণ বেচুন, ২২ মণ রাখুন, ৮০,২০০ টাকা, নিশ্চিত লাভ।").passed


def test_no_gemini_or_error_uses_template():
    assert narrate(TEMPLATE, None)["status"] == "template"

    def boom(_):
        raise RuntimeError("timeout")
    assert narrate(TEMPLATE, boom)["status"] == "gemini_failed"


def test_understand_bare_answer_fills_the_asked_slot():
    result = understand("পঞ্চাশ", expecting="quantity_kg")
    assert result["values"]["quantity_kg"]["value"] == round(50 * MAUND_TO_KG, 2)
    result = understand("জানি না", expecting="offer_per_kg")
    assert result["values"]["offer_per_kg"]["value"] == 0


def test_gemini_numbers_must_have_been_said():
    # The parser cannot place "৩০" here; Gemini says 30 maunds (said) and dadon 5000 (never said)
    fake = FakeGemini(json_answer={
        "intent": "sell",
        "quantity": {"number": 30, "unit": "maund"},
        "dadon_taka": 5000,
    })
    result = understand("আলু আছে ৩০ টার মতো, বেচতে চাই", gemini=fake)
    assert fake.calls == 1
    assert result["values"]["quantity_kg"]["source"] == "gemini"
    assert result["values"]["quantity_kg"]["value"] == round(30 * MAUND_TO_KG, 2)
    assert "dadon_tk" not in result["values"]
    assert result["rejected"][0]["slot"] == "dadon_tk"
    assert result["rejected"][0]["reason"] == "not_said"


def test_gemini_not_called_when_parser_placed_everything():
    fake = FakeGemini(json_answer={})
    result = understand("আমার ৫০ মণ আলু আছে", gemini=fake)
    assert fake.calls == 0
    assert result["gemini"] == "not_needed"


def test_gemini_price_unit_follows_the_size_of_the_number():
    # "ফড়িয়া ১৬ টেকা দিবার চায়" has no কেজি or মণ; Gemini once guessed ৳16 a maund (৳0.4 a kg)
    fake = FakeGemini(json_answer={"offer_price": {"number": 16, "per": "maund"}})
    result = understand("হামার ৮০ মণ আলু, ফড়িয়া ১৬ টেকা দিবার চায়", gemini=fake)
    assert result["values"]["offer_per_kg"]["value"] == 16
    assert result["values"]["offer_per_kg"]["source"] == "gemini"
    fake = FakeGemini(json_answer={"offer_price": {"number": 1200, "per": "kg"}})
    result = understand("হামার ৮০ মণ আলু, ফড়িয়া বারোশো দিবার চায়", gemini=fake)
    assert result["values"]["offer_per_kg"]["value"] == round(1200 / MAUND_TO_KG, 2)


def test_gemini_price_below_a_believable_price_is_rejected():
    fake = FakeGemini(json_answer={"offer_price": {"number": 2, "per": "kg"}})
    result = understand("হামার ৮০ মণ আলু, ফড়িয়া ২ টেকা দিবার চায়", gemini=fake)
    assert "offer_per_kg" not in result["values"]
    assert result["rejected"][0] == {"slot": "offer_per_kg", "number": 2, "reason": "out_of_range"}
