"""Gemini adapter (Google AI Studio free tier is enough for on-demand runs of ~25 leads)."""
from __future__ import annotations

import json
import logging
from typing import Any

from ..config import settings
from .base import IntelAnalysis, build_prompt

log = logging.getLogger(__name__)

_JUDGEMENT = {"type": "OBJECT", "properties": {"value": {"type": "BOOLEAN", "nullable": True}, "evidence": {"type": "STRING"}},
              "required": ["value", "evidence"]}
# Explicit response schema: the Gemini API rejects pydantic-derived schemas that carry default values.
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "what_they_sell": {"type": "STRING", "description": "One sentence: what the company sells and to whom"},
        "business_model": {"type": "STRING", "description": "One of B2B, B2C, B2B2C, unknown"},
        "industry_normalized": {"type": "STRING", "description": "Short normalised industry label, e.g. 'HVAC contractor'"},
        "owner_operated": {**_JUDGEMENT, "description": "Is the business run by its owner/founder? Cite evidence"},
        "independence": {**_JUDGEMENT, "description": "Independent (not subsidiary/PE-backed/franchise)? Cite evidence"},
        "succession_signals": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Up to 4 short signals the owner may exit"},
        "exit_assessment": {"type": "INTEGER", "description": "0-100 likelihood the owner would entertain a sale in 1-3 years"},
        "exit_reasoning": {"type": "STRING", "description": "Two sentences justifying exit_assessment"},
        "analyst_note": {"type": "STRING", "description": "Two-line note a searcher would want before calling"},
        "outreach_angle": {"type": "STRING", "description": "One opening sentence a buyer could use, specific to this company"},
    },
    "required": ["what_they_sell", "business_model", "industry_normalized", "owner_operated", "independence",
                 "succession_signals", "exit_assessment", "exit_reasoning", "analyst_note", "outreach_angle"],
}


class GeminiProvider:
    name = "gemini"

    def __init__(self) -> None:
        from google import genai  # imported lazily so the app runs without the package configured

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model

    async def analyze(self, lead: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any] | None:
        from google.genai import types

        try:
            resp = await self._client.aio.models.generate_content(
                model=self._model,
                contents=build_prompt(lead, extracted),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                    temperature=0.2,
                ),
            )
            data = json.loads(resp.text or "{}")
            return IntelAnalysis.model_validate(data).model_dump()
        except Exception as e:  # rate limit, network, schema -> degrade to rules
            log.warning("Gemini analyze failed for %s: %s", lead.get("company"), e)
            return None
