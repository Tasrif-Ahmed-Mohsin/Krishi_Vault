"""
KrishiVault Voice Intent & Entity Parser
========================================
Parses farmer voice inputs (transcripts from Bengali ASR or IVR touchtone/text)
into structured FarmerSituation parameters.

Handles:
- Bengali numerals (০-৯) and English numerals (0-9)
- Local agricultural units: মণ (maund ~ 37.32 kg), বস্তা (sack ~ 50 or 85 kg), কেজি (kg)
- Currency terms: টাকা (Tk), হাজার (thousand), লাখ (lakh)
- Time deadlines: দিন (days), সপ্তাহ (weeks), কাল/পরশু (tomorrow/day after)
- Storage access: হিমাগার/কোল্ড স্টোরেজ আছে/নাই
"""

import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
from config.settings import MAUND_TO_KG

# Mapping Bengali digits to English digits
BN_TO_EN_DIGITS = {
    '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
    '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'
}

def normalize_bn_numbers(text: str) -> str:
    """Convert Bengali numbers to standard ASCII digits."""
    for bn, en in BN_TO_EN_DIGITS.items():
        text = text.replace(bn, en)
    return text

class FarmerIntentParser:
    """Extracts situational entities from spoken farmer transcripts."""

    @staticmethod
    def parse_quantity(text: str) -> Optional[float]:
        """
        Extract total harvest in KG.
        Handles '২০ মণ', '50 maund', '৮০ বস্তা', '1000 kg'.
        """
        text_norm = normalize_bn_numbers(text.lower())

        # Check for maund / মণ
        maund_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:মণ|মন|maund|mounds?)', text_norm)
        if maund_match:
            maunds = float(maund_match.group(1))
            return round(maunds * MAUND_TO_KG, 2)

        # Check for sacks / বস্তা (assume 50 kg per standard modern potato sack in BD)
        sack_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:বস্তা|ব্যাগ|sack|bag)', text_norm)
        if sack_match:
            sacks = float(sack_match.group(1))
            return round(sacks * 50.0, 2)

        # Check for KG / কেজি
        kg_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:কেজি|কেজী|kg|kilo)', text_norm)
        if kg_match:
            return float(kg_match.group(1))

        # Bare number fallback if context implies quantity
        num_match = re.search(r'\b(\d+(?:\.\d+)?)\b', text_norm)
        if num_match and ('আলু' in text or 'potato' in text_norm):
            val = float(num_match.group(1))
            # If smaller than 300, usually maunds
            if val <= 300:
                return round(val * MAUND_TO_KG, 2)
            return val

        return None

    @staticmethod
    def parse_cash_needed(text: str) -> Optional[float]:
        """
        Extract urgent cash requirements in BDT.
        Handles '১০ হাজার টাকা', '10000 tk', '১ লাখ টাকা', '৫০,০০০'.
        """
        text_norm = normalize_bn_numbers(text.lower())

        # Check for Lakh / লাখ
        lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:লাখ|লক্ষ|lakh)', text_norm)
        if lakh_match:
            return float(lakh_match.group(1)) * 100000.0

        # Check for Thousand / হাজার
        hazar_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:হাজার|hazar|k\b)', text_norm)
        if hazar_match:
            return float(hazar_match.group(1)) * 1000.0

        # Ignore if text is purely an offer rate (e.g., "১৮ টাকা কেজি", "৮০০ টাকা মণ") without need indicators
        is_rate_context = bool(re.search(r'(?:কেজি|কেজী|kg|মণ|মন|বস্তা)', text_norm))
        has_need_context = any(k in text_norm for k in ['লাগবে', 'দরকার', 'প্রয়োজন', 'জরুরি', 'ধার', 'ঋণ', 'খরচ'])

        # Direct money amount with Tk (prevent matching '18 টাকা কেজি' as cash needed)
        tk_match = re.search(r'(\d[\d,]*)\s*(?:টাকা|টাকার|tk|taka)(?!\s*(?:কেজি|কেজী|kg|মণ|মন|বস্তা))', text_norm)
        if tk_match:
            cleaned = tk_match.group(1).replace(',', '')
            val = float(cleaned)
            if val >= 500 or has_need_context:
                return val

        return None

    @staticmethod
    def parse_deadline_days(text: str) -> int:
        """
        Extract urgency deadline in days.
        Defaults to 7 days if unmentioned or flexible.
        """
        text_norm = normalize_bn_numbers(text.lower())

        if 'আজ' in text or 'today' in text_norm:
            return 1
        if 'কাল' in text or 'tomorrow' in text_norm:
            return 1
        if 'পরশু' in text:
            return 2

        day_match = re.search(r'(\d+)\s*(?:দিন|দিনের|days?)', text_norm)
        if day_match:
            return int(day_match.group(1))

        week_match = re.search(r'(\d+)\s*(?:সপ্তাহ|weeks?)', text_norm)
        if week_match:
            return int(week_match.group(1)) * 7

        month_match = re.search(r'(\d+)\s*(?:মাস|months?)', text_norm)
        if month_match:
            return int(month_match.group(1)) * 30

        return 7

    @staticmethod
    def parse_storage_access(text: str) -> bool:
        """Check if farmer has access or booking in a cold storage."""
        text_l = text.lower()
        positive_keywords = ['আছে', 'বুকিং আছে', 'রাখতে পারব', 'সুবিধা আছে', 'yes', 'হিমাগারে দিতে পারব']
        negative_keywords = ['নাই', 'নেই', 'না', 'পারব না', 'সুবিধা নাই', 'no', 'দূরে']

        for neg in negative_keywords:
            if neg in text_l:
                return False

        for pos in positive_keywords:
            if pos in text_l:
                return True

        return False

    @staticmethod
    def parse_offer_price(text: str) -> Optional[float]:
        """Extract current buyer/faria offer per KG or Maund."""
        text_norm = normalize_bn_numbers(text.lower())

        # e.g., '২২ টাকা কেজি' or '22 tk/kg'
        per_kg_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:টাকা)?\s*(?:কেজি|কেজী|kg)', text_norm)
        if per_kg_match:
            return float(per_kg_match.group(1))

        # e.g., '৮০০ টাকা মণ'
        per_maund_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:টাকা)?\s*(?:মণ|মন|maund)', text_norm)
        if per_maund_match:
            price_maund = float(per_maund_match.group(1))
            return round(price_maund / MAUND_TO_KG, 2)

        return None
