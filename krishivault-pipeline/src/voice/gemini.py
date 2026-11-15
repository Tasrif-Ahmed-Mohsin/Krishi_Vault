"""
A small Gemini client for the conversation: fixed JSON fields for understanding the farmer, and short
rewording of the engine's advice. Off unless GEMINI_API_KEY is set; every call has a timeout and returns
None on failure, so the conversation always works without it.

GEMINI_MODEL (optional) names the model, or several separated by commas, tried in order.
GEMINI_BUDGET_S (optional, default 5) is the most a farmer waits for Gemini in one turn: after it the
template answer is used, so a slow or overloaded model never leaves the caller in silence.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Optional

from loguru import logger

# The lite model first: it answers in about a second; the full model timed out on a cold start (15 November)
DEFAULT_MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-lite-latest", "gemini-flash-latest"]

# Google refuses a wait shorter than 10 seconds ("Minimum allowed deadline is 10s"), so 8 failed every call
MIN_TIMEOUT_S = 10.0
DEFAULT_BUDGET_S = 5.0

# A late answer still finishes in the background and teaches the client which model works
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="gemini")


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, models: Optional[list] = None, timeout_s: float = 12.0,
                 budget_s: Optional[float] = None):
        self.api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "").strip()
        env_models = [m.strip() for m in os.getenv("GEMINI_MODEL", "").split(",") if m.strip()]
        self.models = models or env_models or DEFAULT_MODELS
        self.timeout_ms = int(max(timeout_s, MIN_TIMEOUT_S) * 1000)
        if budget_s is None:
            try:
                budget_s = float(os.getenv("GEMINI_BUDGET_S", DEFAULT_BUDGET_S))
            except ValueError:
                budget_s = DEFAULT_BUDGET_S
        self.budget_s = budget_s
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
        future = _pool.submit(self._try_models, prompt, json_output, system)
        try:
            return future.result(timeout=self.budget_s)
        except FutureTimeout:
            logger.warning(f"Gemini gave no answer within {self.budget_s:.0f} s: the template is used")
            return None

    def _try_models(self, prompt: str, json_output: bool, system: Optional[str] = None) -> Optional[str]:
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
