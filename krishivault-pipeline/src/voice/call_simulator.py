"""
KrishiVault Voice Call Simulator
================================
Interactive phone call simulator connecting the voice dialog manager,
database models, price prediction signals, and decision engine.

Demonstrates the real user experience for a Bangladeshi farmer calling KrishiVault.
"""

import sys
from pathlib import Path
from loguru import logger

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database import init_database, MarketPrice, Farmer, ColdStorage, Buyer
from src.engine.decision_engine import (
    FarmerSituation, MarketContext, DecisionEngine, BuyerOffer
)
from src.voice.intent_parser import FarmerIntentParser
from src.voice.farmer_dialog import FarmerVoiceDialog
from config.settings import DATABASE_URL, MAUND_TO_KG

def simulate_farmer_call(
    farmer_phone: str,
    raw_utterances: list[str]
):
    """
    Simulate an entire phone call session:
    1. Identify farmer profile from DB or register caller.
    2. Extract parameters from voice utterances using FarmerIntentParser.
    3. Retrieve local market prices, cold storages, and buyer network offers from DB.
    4. Compute 7d/14d/30d market forecast context.
    5. Run DecisionEngine across all 4 scenarios.
    6. Generate spoken Bengali response with IVR choices.
    """
    engine, Session = init_database(DATABASE_URL)
    session = Session()

    try:
        farmer = session.query(Farmer).filter_by(phone_number=farmer_phone).first()
        farmer_name = farmer.name if farmer else "চাষী ভাই"
        district = farmer.district if farmer else "Bogura"

        print("=" * 65)
        print(f"📞 [INCOMING CALL] Phone: {farmer_phone} | Farmer: {farmer_name} | District: {district}")
        print("=" * 65)

        # 1. Voice Greeting
        greeting = FarmerVoiceDialog.generate_greeting(farmer_name, district)
        print(f"\n🤖 [IVR System]: {greeting}\n")

        # 2. Parse farmer utterances
        parsed_quantity = None
        parsed_cash = None
        parsed_deadline = 7
        parsed_storage = False
        parsed_offer = 0.0

        for idx, utterance in enumerate(raw_utterances, 1):
            print(f"👨‍🌾 [Farmer Response {idx}]: \"{utterance}\"")

            q = FarmerIntentParser.parse_quantity(utterance)
            if q:
                parsed_quantity = q

            c = FarmerIntentParser.parse_cash_needed(utterance)
            if c:
                parsed_cash = c

            d = FarmerIntentParser.parse_deadline_days(utterance)
            if d != 7 or 'দিন' in utterance or 'কাল' in utterance or 'আজ' in utterance:
                parsed_deadline = d

            if 'হিমাগার' in utterance or 'স্টোরেজ' in utterance:
                parsed_storage = FarmerIntentParser.parse_storage_access(utterance)

            o = FarmerIntentParser.parse_offer_price(utterance)
            if o:
                parsed_offer = o

        # Fallbacks for defaults if not spoken
        quantity_kg = parsed_quantity or (50 * MAUND_TO_KG)
        cash_needed = parsed_cash or 20000.0
        deadline_days = parsed_deadline or 5
        has_storage = parsed_storage if farmer is None else farmer.has_cold_storage_access
        offer_price = parsed_offer or 20.0

        print("\n" + "-" * 65)
        print(f"📋 [Extracted Situation]:")
        print(f"   • Harvest Quantity: {quantity_kg / MAUND_TO_KG:.1f} maunds ({quantity_kg:.1f} kg)")
        print(f"   • Cash Urgency: ৳{cash_needed:,.0f} within {deadline_days} days")
        print(f"   • Local Offer: ৳{offer_price:.2f}/kg")
        print(f"   • Cold Storage Access: {'Yes' if has_storage else 'No'}")
        print("-" * 65)

        # 3. Retrieve DB context
        # Get latest market price in district
        latest_price_rec = session.query(MarketPrice).filter_by(district=district).order_by(MarketPrice.date.desc()).first()
        base_market_price = latest_price_rec.retail_avg if latest_price_rec else 22.0

        # Cold storage rate from DB
        cs = session.query(ColdStorage).filter_by(district=district).first()
        storage_rate = cs.actual_rate_per_kg if cs else 6.50

        # Buyer offers from DB
        db_buyers = session.query(Buyer).filter(Buyer.district.in_([district, "Dhaka"])).all()
        buyer_offers = [
            BuyerOffer(
                buyer_name=b.name,
                buyer_type=b.buyer_type,
                price_per_kg=b.current_offer_per_kg or (base_market_price + 1.5),
                min_quantity_kg=b.min_quantity_kg or 1000.0,
                payment_days=b.payment_days or 3,
                district=b.district
            )
            for b in db_buyers
        ]

        # 4. Formulate Market Context (trend: up, e.g. approaching post-harvest storage period)
        market_ctx = MarketContext(
            current_price_per_kg=base_market_price,
            predicted_7d_price=round(base_market_price * 1.05, 2),
            predicted_14d_price=round(base_market_price * 1.12, 2),
            predicted_30d_price=round(base_market_price * 1.25, 2),
            price_trend="up",
            confidence_7d=0.88,
            confidence_14d=0.82,
            confidence_30d=0.78,
            volatility_30d=0.03
        )

        situation = FarmerSituation(
            crop="potato",
            quantity_kg=quantity_kg,
            district=district,
            cash_needed_tk=cash_needed,
            deadline_days=deadline_days,
            current_offer_per_kg=offer_price,
            has_cold_storage=has_storage,
            storage_cost_per_kg=storage_rate,
            transport_cost_per_kg=0.50
        )

        # 5. Run Decision Engine
        engine_inst = DecisionEngine()
        outcome = engine_inst.evaluate(
            farmer=situation,
            market=market_ctx,
            buyer_offers=buyer_offers
        )

        # 6. Generate Voice Dialog
        dialog_output = FarmerVoiceDialog.format_decision_advice_bn(outcome, farmer_name)

        print("\n🎙️ [KRISHIVAULT SPOKEN BANGLA RESPONSE]:")
        print(f"\"{dialog_output['speech_text_bn']}\"\n")
        print(f"📱 [SMS SENT TO FARMER]:")
        print(f"\"{dialog_output['sms_summary_bn']}\"")
        print("=" * 65)

    finally:
        session.close()

if __name__ == "__main__":
    # Test call 1: Abdur Rahim from Bogura
    simulate_farmer_call(
        farmer_phone="+8801711998877",
        raw_utterances=[
            "আমার প্রায় ৮০ মণ আলু উঠছে জমিতে।",
            "বাচ্চাদের পড়ার খরচ আর সার কেনার জন্য জরুরি ২৫ হাজার টাকা লাগবে ৫ দিনের মধ্যে।",
            "স্থানীয় ব্যাপারী বলছে ১৮ টাকা কেজি দেবে।",
            "মহাস্থানগড়ের হিমাগারে আমার কিছু রাখার জায়গা আছে।"
        ]
    )
