"""
KrishiVault Bengali Text-to-Speech (TTS) Generator
==================================================
Uses Google Cloud Text-to-Speech with Service Account credentials
from env materials to generate high-fidelity Bengali voice audio for farmers.
"""

import os
from pathlib import Path
from typing import Optional
from loguru import logger
from dotenv import load_dotenv

# Ensure credentials loaded
BASE_DIR = Path(__file__).parent.parent.parent
load_dotenv(BASE_DIR / ".env")

try:
    from google.cloud import texttospeech
    GCP_TTS_AVAILABLE = True
except ImportError:
    GCP_TTS_AVAILABLE = False


class BengaliVoiceSynthesizer:
    """Generates natural Bengali spoken audio files for KrishiVault voice telephony."""

    def __init__(self, credentials_path: Optional[str] = None):
        self.cred_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if self.cred_path and os.path.exists(self.cred_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.cred_path
            self.client = texttospeech.TextToSpeechClient()
            self.ready = True
            logger.info("Google Cloud TTS initialized successfully.")
        else:
            self.client = None
            self.ready = False
            logger.warning(f"Google Cloud TTS credentials not found at: {self.cred_path}")

    def synthesize_speech(
        self,
        text: str,
        output_filename: str = "farmer_advice.mp3",
        voice_gender: str = "MALE",
        speaking_rate: float = 0.95  # Slightly slower for clarity over rural phone lines
    ) -> Optional[Path]:
        """
        Synthesize text into a Bengali MP3 audio file.
        
        Args:
            text: Bengali text to be spoken
            output_filename: Name of the generated MP3
            voice_gender: "MALE" or "FEMALE"
            speaking_rate: Audio speed (0.95 = clear and natural)
            
        Returns:
            Path to generated MP3 file, or None if failed
        """
        if not self.ready:
            logger.error("TTS client is not initialized.")
            return None

        audio_dir = BASE_DIR / "data" / "audio_out"
        audio_dir.mkdir(parents=True, exist_ok=True)
        output_path = audio_dir / output_filename

        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)

            gender_enum = (
                texttospeech.SsmlVoiceGender.FEMALE
                if voice_gender.upper() == "FEMALE"
                else texttospeech.SsmlVoiceGender.MALE
            )

            # Use standard Bengali voice (bn-IN or bn-BD)
            voice = texttospeech.VoiceSelectionParams(
                language_code="bn-IN",
                ssml_gender=gender_enum
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
                pitch=0.0
            )

            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            with open(output_path, "wb") as out:
                out.write(response.audio_content)

            logger.success(f"Generated Bengali speech audio: {output_path} ({len(response.audio_content)} bytes)")
            return output_path

        except Exception as e:
            logger.error(f"Failed to synthesize speech: {e}")
            return None


if __name__ == "__main__":
    synthesizer = BengaliVoiceSynthesizer()
    sample_text = (
        "আসসালামু আলাইকুম রহিম ভাই। কৃষিভল্ট এ স্বাগতম। "
        "আজ আপনার এলাকায় আলুর বাজার দর স্থিতিশীল রয়েছে। "
        "আমাদের পরামর্শ হলো জরুরি টাকা পরিশোধে এখনই অর্ধেক বিক্রি করুন এবং বাকি আলু হিমাগারে সংরক্ষণ করুন।"
    )
    result = synthesizer.synthesize_speech(sample_text, "test_bengali_greeting.mp3")
    if result:
        print(f"Audio generated at: {result}")
