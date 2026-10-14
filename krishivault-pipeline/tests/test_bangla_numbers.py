"""
Tests for Bangla number words, number formatting and the clause-by-clause parser.
"""

import pytest
from config.settings import MAUND_TO_KG
from src.voice.bangla_numbers import words_to_digits, extract_numbers, fmt_taka, fmt_num, group_bd
from src.voice.intent_parser import FarmerIntentParser as P


@pytest.mark.parametrize("spoken, digits", [
    ("পঞ্চাশ মণ আলু", "50 মণ আলু"),
    ("বিশ হাজার টাকা লাগবে", "20000 টাকা লাগবে"),
    ("২০,০০০ টাকা", "20000 টাকা"),
    ("১.৫ লাখ টাকা", "150000 টাকা"),
    ("দেড় লাখ", "150000"),
    ("সাড়ে তিন হাজার", "3500"),
    ("দুই হাজার পাঁচশো", "2500"),
    ("এক লাখ বিশ হাজার", "120000"),
    ("আটশো টাকা মণ", "800 টাকা মণ"),
    ("পঞ্চাশটা বস্তা", "50 বস্তা"),
    ("এক মণ", "1 মণ"),
])
def test_words_to_digits(spoken, digits):
    assert words_to_digits(spoken) == digits


def test_ambiguous_words_stay_words():
    # এক = "a", নয় = "is not": numbers only before a unit
    assert words_to_digits("একটা কথা") == "একটা কথা"
    assert words_to_digits("এটা ঠিক নয়") == "এটা ঠিক নয়"
    # two plain numbers in a row are a range, not a sum
    assert extract_numbers("বিশ পঁচিশ মণ") == ["20", "25"]


def test_formatting():
    assert group_bd(120000) == "1,20,000"
    assert fmt_taka(80247.3) == "৮০,২০০"
    assert fmt_taka(845) == "৮৪০"
    assert fmt_num(18.0) == "১৮"
    assert fmt_num(18.46) == "১৮.৫"


def test_parse_all_dialect_sentence():
    said = (
        "হামার শিবগঞ্জের জমিতে ৮০ মণ আলু উঠছে বাহে। পোলাপানের স্কুলের বেতন আর মহাজনের সার বাবদ "
        "জরুরি ২৫ হাজার টেকা নাগবে ৪ দিনের মইধ্যে। স্থানীয় ফড়িয়া ১৮ টেকা কেজি দিবার চায়। "
        "আড়তদারের কাছে ২০ হাজার টেকা দাদন নেওয়া আছে।"
    )
    found = P.parse_all(said)
    assert found["quantity_kg"]["value"] == round(80 * MAUND_TO_KG, 2)
    assert found["cash_needed_tk"]["value"] == 25000
    assert found["deadline_days"]["value"] == 4
    assert found["offer_per_kg"]["value"] == 18
    assert found["dadon_tk"]["value"] == 20000


def test_parse_all_number_words_and_no():
    found = P.parse_all("আমার পঞ্চাশ মণ আলু আছে, বিশ হাজার টাকা লাগবে তিন দিনের মধ্যে")
    assert found["quantity_kg"]["value"] == round(50 * MAUND_TO_KG, 2)
    assert found["cash_needed_tk"]["value"] == 20000
    assert found["deadline_days"]["value"] == 3
    assert P.parse_all("টাকা লাগবে না")["cash_needed_tk"]["value"] == 0
    assert P.parse_all("দাদন নেই")["dadon_tk"]["value"] == 0


def test_quantity_in_kg_is_not_a_price():
    found = P.parse_all("আমার ১৫০০ কেজি আলু, পাইকার কেজিতে ১৯ টাকা দিতে চায়")
    assert found["quantity_kg"]["value"] == 1500
    assert found["offer_per_kg"]["value"] == 19


def test_yes_no_and_menu_words():
    assert P.parse_yes_no("হ্যাঁ ঠিক আছে") is True
    assert P.parse_yes_no("না, ভুল") is False
    assert P.parse_yes_no("আলু") is None
    assert P.parse_menu_choice("আলু বেচতে চাই") == "advice"
    assert P.parse_menu_choice("হিমাগারে রাখব না বেচব") == "advice"
    assert P.parse_menu_choice("দাম কেমন হবে সামনে") == "outlook"
    assert P.parse_menu_choice("সবাই মিলে একসাথে রাখতে চাই") == "group"
    assert P.parse_menu_choice("বস্তা জামানত রেখে লোন পাব?") == "loan"
    assert P.parse_menu_choice("কর্মকর্তার সাথে কথা বলব") == "helper"


def test_in_storage():
    assert P.parse_in_storage("আলু হিমাগারে রাখছি") is True
    assert P.parse_in_storage("কোল্ডে রাখা আছে") is True
    assert P.parse_in_storage("হিমাগারে রাখি নাই") is False
    assert P.parse_in_storage("আলু এখনো ঘরে") is False
    assert P.parse_in_storage("৫০ মণ আলু") is None
