import json
import logging
import re
from typing import Any

from app.core.config import settings
from app.schemas.ai import ExplainResponse
from app.schemas.finding import FindingDetail, FindingItem
from app.services.ai.prompt_templates import (
    build_explanation_prompt,
    generate_deterministic_fallback,
)

logger = logging.getLogger(__name__)

_UNSET = object()


class AIServiceUnavailableError(Exception):
    """Raised when the Gemini/Gemma AI explanation service is unavailable or unconfigured."""

    def __init__(self, message: str = "AI explanation service is unavailable.") -> None:
        super().__init__(message)
        self.message = message
        self.code = "AI_SERVICE_UNAVAILABLE"


class GeminiService:
    """Service for generating evidence-grounded finding explanations using Google Gemini / Gemma."""

    def __init__(
        self,
        api_key: Any = _UNSET,
        model: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.api_key = settings.gemini_api_key if api_key is _UNSET else api_key
        self.model = model if model is not None else settings.gemini_model
        self._client = client

        if self._client is None and self.api_key and self.api_key.strip():
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key.strip())
                logger.info("Initialized AI client with model %s", self.model)
            except Exception as exc:
                logger.warning("Failed to initialize Google GenAI client: %s", exc)
                self._client = None

    def is_available(self) -> bool:
        """Returns True if the AI client is configured and initialized."""
        return self._client is not None

    async def explain_finding(
        self,
        finding: FindingItem | FindingDetail,
        repo_name: str = "",
        fallback_on_error: bool = False,
    ) -> ExplainResponse:
        """
        Generates an evidence-grounded AI explanation for a given finding.
        Falls back to a deterministic explanation if fallback_on_error is True.
        """
        if not self.is_available():
            if fallback_on_error:
                logger.info("AI client not configured; returning deterministic fallback explanation.")
                data = generate_deterministic_fallback(finding)
                return ExplainResponse(**data)
            raise AIServiceUnavailableError(
                "Gemini API key is not configured. The AI explanation service is currently unavailable."
            )

        prompt = build_explanation_prompt(finding, repo_name)

        try:
            from google.genai import types

            response = None
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                    ),
                )
            except Exception as json_err:
                logger.info("JSON-mode generation failed (%s), trying basic generation", json_err)
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )

            raw_text = getattr(response, "text", "") or ""
            if not raw_text.strip():
                raise ValueError("Received empty response from AI model.")

            # Attempt direct parse
            try:
                parsed = json.loads(raw_text)
                return ExplainResponse(**parsed)
            except Exception:
                # If markdown code block formatting was wrapped around JSON
                match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(1))
                    return ExplainResponse(**parsed)
                # Fallback regex for raw JSON object
                match_raw = re.search(r"(\{.*\})", raw_text, re.DOTALL)
                if match_raw:
                    parsed = json.loads(match_raw.group(1))
                    return ExplainResponse(**parsed)
                raise

        except Exception as exc:
            logger.warning("AI model generation failed for finding %s: %s", finding.finding_id, exc)
            if fallback_on_error:
                logger.info("Returning deterministic fallback explanation due to model error.")
                return ExplainResponse(**generate_deterministic_fallback(finding))
            raise AIServiceUnavailableError(
                f"Failed to generate AI explanation: {exc}"
            ) from exc


# Global service singleton
gemini_service = GeminiService()
