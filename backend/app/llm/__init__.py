from __future__ import annotations

from functools import lru_cache

from ..config import settings
from .base import LLMProvider
from .rules import RulesProvider


@lru_cache(maxsize=1)
def get_provider() -> LLMProvider:
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        from .gemini import GeminiProvider

        return GeminiProvider()
    return RulesProvider()


def active_provider_name() -> str:
    return get_provider().name
