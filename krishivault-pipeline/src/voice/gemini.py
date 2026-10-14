"""
A small Gemini client for the conversation: fixed JSON fields for understanding the farmer, and short
rewording of the engine's advice. Off unless GEMINI_API_KEY is set; every call has a timeout and returns
None on failure, so the conversation always works without it.

GEMINI_MODEL (optional) names the model, or several separated by commas, tried in order.
"""

import json
import os
from typing import Optional

from loguru import logger

DEFAULT_MODELS = ["gemini-3.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest", "gemini-3.8-flash"]


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, models: Optional[list] = None, timeout_s: float = 8.0):
        self.api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "").strip()
        env_models = [m.strip() for m in os.getenv("GEMINI_MODEL", "").split(",") if m.strip()]
        self.models = models or env_models or DEFAULT_MODELS
        self.timeout_ms = int(timeout_s * 1000)
        self._client = None
        self._working_model: Optional[str] = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            from google import genai
            from google.genai import types
            self._client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=self.timeout_ms))
        return self._client

    def _generate(self, prompt: str, json_output: bool, system: Optional[str] = None) -> Optional[str]:
        if not self.available:
            return None
        from google.genai import types
        config = types.GenerateContentConfig(
            temperature=0.2,
            system_instruction=system,
            response_mime_type="application/json" if json_output else None,
        )
        order = ([self._working_model] if self._working_model else []) + [m for m in self.models if m != self._working_model]
        for model in order:
            try:
                response = self._get_client().models.generate_content(model=model, contents=prompt, config=config)
                text = (response.text or "").strip()
                if text:
                    self._working_model = model
                    return text
            except Exception as exc:
                logger.warning(f"Gemini model {model} failed: {exc}")
        return None

    def json(self, prompt: str) -> Optional[dict]:
        text = self._generate(prompt, json_output=True)
        if not text:
            return None
        try:
            data = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            logger.warning("Gemini did not return valid JSON")
            return None

    def text(self, prompt: str, system: Optional[str] = None) -> Optional[str]:
        return self._generate(prompt, json_output=False, system=system)

    @property
    def model_used(self) -> Optional[str]:
        return self._working_model
