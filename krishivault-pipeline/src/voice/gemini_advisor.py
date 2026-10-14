"""
KrishiVault Gemini AI Advisor & Natural Dialogue Engine
======================================================
Powered by Google Gemini 3.8 Flash (from env materials).
Provides:
1. Dialect-aware intent & entity extraction from spoken Bengali farmer calls.
2. Empathetic, culturally respectful natural language guidance based on DecisionEngine results.
3. End-to-end voice synthesis pipeline via Google Cloud Text-to-Speech.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger
from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.voice.tts_generator import BengaliVoiceSynthesizer

BASE_DIR = Path(__file__).parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class GeminiFarmerAdvisor:
    """Gemini-powered conversational AI tailored for Bangladeshi smallholder farmers."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        self.client = genai.Client(api_key=self.api_key)
        self.candidate_models = ["gemini-3.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest", "gemini-3.8-flash"]
        self.tts = BengaliVoiceSynthesizer()
        logger.info(f"GeminiAdvisor initialized with primary model: {self.candidate_models[0]}")

    def extract_farmer_intents(self, transcript: str) -> Dict[str, Any]:
        """
        Extract structured parameters from colloquial Bengali audio transcript.
        Recognizes regional terms (মণ, বস্তা, ধার, দাদন, মহাজন, আড়তদার).
        """
        prompt = f"""
You are an expert agricultural assistant analyzing a call transcript from a potato farmer in Bangladesh.
Extract the following information from the transcript and return ONLY a valid JSON object:
- "quantity_maunds": float or null (total potato quantity in maunds/মণ; 1 maund ≈ 37.3 kg; if in sacks/বস্তা assume 1 sack = 1.34 maunds or 50 kg)
- "quantity_kg": float or null
- "cash_needed_tk": float or null (urgent money needed)
- "deadline_days": int (days within which money is needed, default 7)
- "current_offer_per_kg": float or null (offer given by local buyer/faria in Tk/kg)
- "has_cold_storage": bool (does farmer have access/booking to cold storage?)
- "has_dadon": bool (has the farmer taken advance loans/দাদন from local faria or arhatdar?)
- "dadon_amount_tk": float or null
- "district": string (e.g. Bogura, Rangpur, Dinajpur, Munshiganj, Rajshahi; default "Bogura")
- "variety": string ("deshi" or "holland", default "deshi")

Transcript:
\"\"\"{transcript}\"\"\"

Return ONLY the JSON. No markdown ticks, no extra text.
"""
        data = {}
        for model in self.candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                data = json.loads(response.text.strip())
                logger.info(f"Gemini ({model}) extracted intents: {data}")
                return data
            except Exception as e:
                logger.warning(f"Model {model} failed for intent extraction: {e}")

        logger.error("All Gemini candidate models failed for intent extraction.")
        return {}

    def generate_conversational_advice(
        self,
        farmer_name: str,
        district: str,
        recommendation: str,
        expected_proceeds_tk: float,
        best_scenario_explanation: str,
        runner_up_scenario: Optional[str] = None,
        runner_up_proceeds_tk: Optional[float] = None,
        has_dadon: bool = False,
        dadon_amount_tk: float = 0.0,
        synthesize_audio: bool = True
    ) -> Dict[str, Any]:
        """
        Generate warm, conversational spoken Bengali advice and optionally synthesize to MP3.
        """
        system_instruction = (
            "তুমি 'কৃষিভল্ট' (KrishiVault) এর একজন বিশ্বস্ত এবং অভিজ্ঞ কৃষি পরামর্শক। "
            "বাংলাদেশের বগুড়া ও রংপুরের গ্রামীণ আলু চাষীদের সাথে ফোনের মাধ্যমে কথা বলছো। "
            "তোমার ভাষা হবে অত্যন্ত আন্তরিক, সহজ-সরল এবং স্পষ্ট বাংলা (গ্রাম্য কৃষকের বোধগম্য)। "
            "কোনো জটিল ইংরেজি পরিভাষা ব্যবহার করবে না। টাকা ও মণ এর হিসাবগুলো স্পষ্ট করে বলবে। "
            "বক্তব্যের শেষে প্রেস ১, প্রেস ২ ইত্যাদি আইভিআর নির্দেশনা দেবে।"
        )

        prompt = f"""
চাষীর নাম: {farmer_name} ভাই
এলাকা: {district}
আমাদের গাণিতিক অপ্টিমাইজেশন ফলাফল:
- সেরা সিদ্ধান্ত: {recommendation}
- সম্ভাব্য মোট নিট আয়: ৳{expected_proceeds_tk:,.0f} টাকা
- সিদ্ধান্তের বিশদ কারণ: {best_scenario_explanation}
- বিকল্প দ্বিতীয় সুযোগ: {runner_up_scenario} (সম্ভাব্য আয়: ৳{runner_up_proceeds_tk:,.0f} টাকা)
- দাদন বা ঋণের তথ্য: {'দাদন আছে ' + str(dadon_amount_tk) + ' টাকা' if has_dadon else 'দাদন নেই'}

কৃষককে ফোনে শোনানোর জন্য ৩ থেকে ৪ বাক্যের একটি সংক্ষিপ্ত, স্পষ্ট এবং আন্তরিক অডিও বক্তব্য তৈরি করো।
বক্তব্যে অবশ্যই টাকার হিসাব এবং করণীয় পরিষ্কার থাকবে।
"""
        speech_text = None
        used_model = None

        for model in self.candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.3
                    )
                )
                speech_text = response.text.strip()
                used_model = model
                logger.info(f"Gemini ({model}) synthesized advice:\n{speech_text}")
                break
            except Exception as e:
                logger.warning(f"Model {model} failed for advice generation: {e}")

        if not speech_text:
            speech_text = f"{farmer_name} ভাই, আপনার জন্য সেরা পরামর্শ: {recommendation}। সম্ভাব্য আয় ৳{expected_proceeds_tk:,.0f} টাকা।"
            used_model = "fallback"

        audio_file = None
        if synthesize_audio and self.tts.ready:
            audio_filename = f"advice_{farmer_name.lower().replace(' ', '_')}.mp3"
            audio_file = self.tts.synthesize_speech(speech_text, audio_filename)

        return {
            "spoken_bangla_text": speech_text,
            "audio_path": str(audio_file) if audio_file else None,
            "model_used": used_model
        }


if __name__ == "__main__":
    advisor = GeminiFarmerAdvisor()

    # 1. Test colloquial transcript extraction
    sample_transcript = (
        "হামার শিবগঞ্জের জমিতে ৮০ মণ আলু উঠছে বাহে। পোলাপানের স্কুলের বেতন আর মহাজনের সার বাবদ "
        "জরুরি ২৫ হাজার টেকা নাগবে ৪ দিনের মইধ্যে। স্থানীয় ফড়িয়া ১৮ টেকা কেজি দিবার চায়। "
        "আড়তদারের কাছে ২০ হাজার টেকা দাদন নেওয়া আছে।"
    )
    print("Testing Intent Extraction...")
    extracted = advisor.extract_farmer_intents(sample_transcript)
    print("Extracted:", json.dumps(extracted, ensure_ascii=False, indent=2))

    # 2. Test conversational advice generation and real Google TTS
    print("\nTesting Advice Generation + Audio Synthesis...")
    advice = advisor.generate_conversational_advice(
        farmer_name="আব্দুর রহিম",
        district="বগুড়া",
        recommendation="SELL_NOW",
        expected_proceeds_tk=80247.0,
        best_scenario_explanation="স্থানীয় বাজারে এখনই বিক্রি করলে পরিবহন বাদে সর্বোচ্চ নিশ্চিত নগদ টাকা ঘরে উঠবে।",
        runner_up_scenario="আংশিক বিক্রয় ও সংরক্ষণ",
        runner_up_proceeds_tk=71424.0,
        has_dadon=True,
        dadon_amount_tk=20000.0,
        synthesize_audio=True
    )
    print("\nGenerated Bengali Spoken Text:")
    print(advice["spoken_bangla_text"])
    print("\nAudio file:", advice["audio_path"])
