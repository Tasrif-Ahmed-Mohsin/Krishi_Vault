"""
Unit Tests for FarmerIntentParser
=================================
Tests Bengali numeral normalization, quantity units (মণ, বস্তা, কেজি),
cash urgency, deadline days, and storage availability.
"""

import pytest
from src.voice.intent_parser import FarmerIntentParser, normalize_bn_numbers
from config.settings import MAUND_TO_KG

def test_normalize_bn_numbers():
    assert normalize_bn_numbers("১২৩৪৫৬৭৮৯০") == "1234567890"
    assert normalize_bn_numbers("৫০ মণ") == "50 মণ"

def test_parse_quantity_maund():
    # 20 maunds
    qty = FarmerIntentParser.parse_quantity("আমার ২০ মণ আলু আছে")
    assert qty == round(20 * MAUND_TO_KG, 2)

    # English digits with Bangla maund
    qty2 = FarmerIntentParser.parse_quantity("50 maund potato")
    assert qty2 == round(50 * MAUND_TO_KG, 2)

def test_parse_quantity_sacks():
    # 10 sacks (50 kg each)
    qty = FarmerIntentParser.parse_quantity("আমার ১০ বস্তা আলু")
    assert qty == 500.0

def test_parse_quantity_kg():
    qty = FarmerIntentParser.parse_quantity("আমার 1500 কেজি আলু")
    assert qty == 1500.0

def test_parse_cash_needed():
    # Thousand / হাজার
    assert FarmerIntentParser.parse_cash_needed("জরুরি ২০ হাজার টাকা লাগবে") == 20000.0
    # Lakh / লাখ
    assert FarmerIntentParser.parse_cash_needed("১.৫ লাখ টাকা প্রয়োজন") == 150000.0
    # Disambiguation: unit price should NOT match as cash needed
    assert FarmerIntentParser.parse_cash_needed("স্থানীয় ব্যাপারী ২০ টাকা কেজি দেবে") is None

def test_parse_deadline_days():
    assert FarmerIntentParser.parse_deadline_days("৩ দিনের মধ্যে টাকা লাগবে") == 3
    assert FarmerIntentParser.parse_deadline_days("আজকেই বিক্রি করতে হবে") == 1
    assert FarmerIntentParser.parse_deadline_days("২ সপ্তাহ পর লাগবে") == 14

def test_parse_storage_access():
    assert FarmerIntentParser.parse_storage_access("হিমাগারে রাখার জায়গা আছে") is True
    assert FarmerIntentParser.parse_storage_access("হিমাগারে কোনো সুবিধা নাই") is False
    assert FarmerIntentParser.parse_storage_access("স্টোরেজ নেই") is False

def test_parse_offer_price():
    assert FarmerIntentParser.parse_offer_price("২২ টাকা কেজি দিতে চাইছে") == 22.0
    assert FarmerIntentParser.parse_offer_price("৮০০ টাকা মণ বলেছে") == round(800.0 / MAUND_TO_KG, 2)
