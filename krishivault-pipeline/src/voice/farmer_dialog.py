"""
KrishiVault Farmer Voice Dialog Generator
=========================================
Generates natural, spoken Bangla dialog prompts for IVR/voice calls with farmers.
Translates mathematical optimizations into clear, empathetic advice.
"""

from typing import Dict, Any, List
from src.engine.decision_engine import DecisionOutput, ScenarioResult
from config.settings import MAUND_TO_KG

class FarmerVoiceDialog:
    """Generates Bengali spoken voice prompts and SMS/audio scripts for farmers."""

    @staticmethod
    def generate_greeting(farmer_name: str = None, district: str = "বগুড়া") -> str:
        """Greeting script."""
        name_str = f"{farmer_name} ভাই, " if farmer_name else "ভাই, "
        return (
            f"আসসালামু আলাইকুম {name_str}কৃষিভল্ট এ আপনাকে স্বাগতম। "
            f"আমরা আপনার এলাকার আজকের আলুর বাজার দর এবং লাভজনক সিদ্ধান্তের হিসাব জানাচ্ছি।"
        )

    @staticmethod
    def format_market_summary_bn(
        district: str,
        current_price: float,
        pred_7d: float,
        pred_30d: float,
        trend: str
    ) -> str:
        """Spoken summary of market prices and trend."""
        trend_bn = "বাড়তির দিকে" if trend == "up" else ("কমার দিকে" if trend == "down" else "স্থিতিশীল")
        return (
            f"আজ {district} বাজারে প্রতি কেজি আলুর পাইকারি দর প্রায় ৳{current_price:.1f} টাকা। "
            f"আমাদের পূর্বাভাস অনুযায়ী আগামী ৭ দিনে দাম হতে পারে প্রায় ৳{pred_7d:.1f} টাকা "
            f"এবং আগামী এক মাসে দাম {trend_bn} থাকার সম্ভাবনা রয়েছে (প্রায় ৳{pred_30d:.1f} টাকা)।"
        )

    @staticmethod
    def format_decision_advice_bn(
        output: DecisionOutput,
        farmer_name: str = None
    ) -> Dict[str, Any]:
        """
        Create complete voice script and SMS summary based on Decision Engine output.
        """
        rec = output.recommended
        total_proceeds = rec.expected_proceeds_tk if rec else 0.0

        scripts = []
        name_prefix = f"{farmer_name} ভাই, " if farmer_name else ""

        if not rec:
            scripts.append(f"{name_prefix}আপনার তথ্যের ভিত্তিতে আমরা কোনো উপযুক্ত সিদ্ধান্ত নিশ্চিত করতে পারিনি।")
        elif rec.scenario == "sell_now":
            scripts.append(
                f"{name_prefix}আপনার বর্তমান নগদ টাকার প্রয়োজন এবং বাজার পরিস্থিতি বিবেচনায় "
                f"আমাদের পরামর্শ হলো: এখনই আপনার সম্পূর্ণ আলু বিক্রি করে দেওয়া সবচেয়ে নিরাপদ।"
            )
            scripts.append(
                f"এতে পরিবহন খরচ বাদ দিয়ে আপনার মোট সম্ভাব্য আয় হবে প্রায় ৳{total_proceeds:,.0f} টাকা।"
            )
        elif rec.scenario == "sell_part":
            sell_maunds = round(rec.sell_quantity_kg / MAUND_TO_KG, 1)
            store_maunds = round(rec.store_quantity_kg / MAUND_TO_KG, 1)
            scripts.append(
                f"{name_prefix}আপনার জন্য সবচেয়ে লাভজনক পরামর্শ হলো আংশিক বিক্রি।"
            )
            scripts.append(
                f"জরুরি নগদ টাকা মেটানোর জন্য এখনই মাত্র {sell_maunds} মণ আলু বিক্রি করুন, "
                f"আর বাকি {store_maunds} মণ আলু হিমাগারে সংরক্ষণ করুন।"
            )
            scripts.append(
                f"পরবর্তীতে দাম বাড়লে বিক্রি করলে সব মিলিয়ে আপনার মোট সম্ভাব্য আয় হবে প্রায় ৳{total_proceeds:,.0f} টাকা, "
                f"যা এখনই সব বিক্রির চেয়ে অনেক বেশি লাভজনক।"
            )
        elif rec.scenario in ["store", "store_review"]:
            scripts.append(
                f"{name_prefix}আমাদের বিশ্লেষণ অনুযায়ী আলু হিমাগারে সংরক্ষণ করা আপনার জন্য লাভজনক হবে।"
            )
            scripts.append(
                f"হিমাগারের ভাড়া ও অপচয় বাদ দিয়েও আগামী ৩০ দিনে আপনার সম্ভাব্য নিট লাভ হবে প্রায় ৳{total_proceeds:,.0f} টাকা।"
            )
        elif rec.scenario == "group_sell":
            scripts.append(
                f"{name_prefix}আপনার জন্য সেরা সুযোগ হলো যৌথ বিক্রয় বা গ্রুপ সেল।"
            )
            scripts.append(
                f"আপনার এলাকার অন্যান্য কৃষকদের সাথে এক সাথে বড় ক্রেতার কাছে সরবরাহ করলে "
                f"কেজি প্রতি বাড়তি দর পাবেন। এতে আপনার মোট সম্ভাব্য আয় হবে ৳{total_proceeds:,.0f} টাকা।"
            )

        # Alternative option note
        alt_note = ""
        if rec:
            other_valid = [s for s in output.scenarios if s.feasible and s.scenario != rec.scenario]
            if other_valid:
                runner_up = other_valid[0]
                alt_name_bn = {
                    "sell_now": "এখনই সব বিক্রি",
                    "sell_part": "অর্ধেক বিক্রি ও অর্ধেক সংরক্ষণ",
                    "store": "হিমাগারে রাখা",
                    "group_sell": "গ্রুপে বিক্রি"
                }.get(runner_up.scenario, runner_up.scenario)
                alt_note = f"এছাড়া দ্বিতীয় বিকল্প হিসেবে আপনি '{alt_name_bn}' বিবেচনা করতে পারেন (সম্ভাব্য আয় ৳{runner_up.expected_proceeds_tk:,.0f} টাকা)।"

        # Interactive touchtone options for IVR
        ivr_options = [
            "১ চাপুন - আমাদের নিবন্ধিত সরাসরি ক্রেতার সাথে যোগাযোগ করতে।",
            "২ চাপুন - স্থানীয় হিমাগারের খালি জায়গা বুকিং করতে।",
            "৩ চাপুন - পার্শ্ববর্তী কৃষকদের সাথে গ্রুপ সেলে যোগ দিতে।",
            "৪ চাপুন - এই তথ্যগুলো এসএমএসে পেতে।"
        ]

        full_speech = " ".join(scripts)
        if alt_note:
            full_speech += " " + alt_note

        full_speech += " আপনার পরবর্তী পদক্ষেপের জন্য: " + " ".join(ivr_options)

        # Concise SMS summary
        scenario_name = rec.scenario if rec else "N/A"
        sms_text = (
            f"কৃষিভল্ট পরামর্শ: {scenario_name.upper()}। "
            f"প্রত্যাশিত নিট আয়: ৳{total_proceeds:,.0f} টাকা। "
            f"সহায়তার জন্য কল করুন 16123 বা যোগাযোগ করুন কৃষিভল্ট প্রতিনিধির সাথে।"
        )

        return {
            "primary_scenario": scenario_name,
            "expected_net_proceeds_tk": total_proceeds,
            "confidence_pct": round((rec.confidence * 100), 1) if rec else 0.0,
            "speech_text_bn": full_speech,
            "sms_summary_bn": sms_text,
            "ivr_options": ivr_options
        }
