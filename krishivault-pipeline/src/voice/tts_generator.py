"""
KrishiVault Bengali Text-to-Speech (TTS) Generator
==================================================
Uses Google Cloud Text-to-Speech with a service-account key (GOOGLE_APPLICATION_CREDENTIALS) to make the
Bangla voice the farmer hears.

- Language: TTS_LANGUAGE if set; otherwise Bangladeshi Bangla (bn-BD) is tried first and Indian Bangla
  (bn-IN) second; the first that works is remembered.
- speak(text) caches the MP3 by its text, so "আবার শুনুন" (hear it again) does not call Google again.
- Without a key, ready is False and the conversation screen uses the phone's own voice instead.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional
from loguru import logger
from dotenv import load_dotenv

# Ensure credentials loaded
BASE_DIR = Path(__file__).parent.parent.parent
load_dotenv(BASE_DIR / ".env")
AUDIO_DIR = BASE_DIR / "data" / "audio_out"
CLOUD_KEY_FILE = "/tmp/gcp-tts.json"  # written by .claude/hooks/session-start.sh

try:
    from google.cloud import texttospeech
    GCP_TTS_AVAILABLE = True
except ImportError:
    GCP_TTS_AVAILABLE = False


class BengaliVoiceSynthesizer:
    """Generates natural Bengali spoken audio files for KrishiVault voice telephony."""

    def __init__(self, credentials_path: Optional[str] = None):
        # The configured path first; then the file the cloud SessionStart hook writes from GOOGLE_TTS_JSON_B64,
        # so a wrong GOOGLE_APPLICATION_CREDENTIALS in the cloud settings does not switch the voice off
        candidates = [credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), CLOUD_KEY_FILE]
        self.cred_path = next((p for p in candidates if p and os.path.isfile(p)), candidates[0])
        configured = os.getenv("TTS_LANGUAGE", "").strip()
        self.languages = [configured] if configured else ["bn-BD", "bn-IN"]
        self.language_used: Optional[str] = None
        self.last_error: Optional[str] = None
        self.client = None
        self.ready = False
        if not GCP_TTS_AVAILABLE:
            self.last_error = "google-cloud-texttospeech is not installed"
            logger.warning("google-cloud-texttospeech is not installed.")
        elif not (self.cred_path and os.path.isfile(self.cred_path)):
            self.last_error = ("no key file: in a cloud session set GOOGLE_TTS_JSON_B64; "
                               "on a laptop set GOOGLE_APPLICATION_CREDENTIALS to the key file's path")
            logger.warning(f"Google Cloud TTS credentials not found at: {self.cred_path}")
        else:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.cred_path
            try:
                self.client = texttospeech.TextToSpeechClient()
                self.ready = True
                logger.info("Google Cloud TTS initialized successfully.")
            except Exception as e:
                self.last_error = str(e)
                logger.warning(f"Google Cloud TTS could not start: {e}")

    def status(self) -> dict:
        return {
            "ready": self.ready,
            "language": self.language_used or self.languages[0],
            "last_error": self.last_error,
        }

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

        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        output_path = AUDIO_DIR / output_filename

        gender_enum = (
            texttospeech.SsmlVoiceGender.FEMALE
            if (voice_gender or "").upper() == "FEMALE"
            else texttospeech.SsmlVoiceGender.MALE
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=0.0
        )
        synthesis_input = texttospeech.SynthesisInput(text=text[:4800])  # Google's limit is 5,000 bytes

        order = ([self.language_used] if self.language_used else []) + [
            lang for lang in self.languages if lang != self.language_used
        ]
        for language in order:
            try:
                voice = texttospeech.VoiceSelectionParams(language_code=language, ssml_gender=gender_enum)
                response = self.client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config, timeout=20
                )
                with open(output_path, "wb") as out:
                    out.write(response.audio_content)
                self.language_used = language
                self.last_error = None
                logger.success(f"Generated Bengali speech audio ({language}): {output_path} ({len(response.audio_content)} bytes)")
                return output_path
            except Exception as e:
                self.last_error = f"{language}: {e}"
                logger.warning(f"Failed to synthesize speech in {language}: {e}")
        return None

    def speak(self, text: str, voice_gender: str = "MALE") -> Optional[Path]:
        """MP3 for this text, made once and then served from the cache."""
        key = hashlib.sha1(f"{voice_gender}|{','.join(self.languages)}|{text}".encode("utf-8")).hexdigest()[:20]
        cached = AUDIO_DIR / f"say_{key}.mp3"
        if cached.exists() and cached.stat().st_size > 0:
            return cached
        return self.synthesize_speech(text, cached.name, voice_gender)


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
