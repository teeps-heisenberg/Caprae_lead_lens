"""Provider-agnostic LLM interface. Every provider returns the same JSON shape (or None)."""
from __future__ import annotations

from typing import Any, Optional, Protocol

from pydantic import BaseModel, Field


class Judgement(BaseModel):
    value: Optional[bool] = None
    evidence: str = ""


class IntelAnalysis(BaseModel):
    """The structured read of a company website. Also used as Gemini's response schema."""
    what_they_sell: str = Field(description="One sentence: what the company sells and to whom")
    business_model: str = Field(description="One of B2B, B2C, B2B2C, unknown")
    industry_normalized: str = Field(description="Short normalised industry label, e.g. 'HVAC contractor'")
    owner_operated: Judgement = Field(description="Is the business run by its owner/founder? Cite the evidence")
    independence: Judgement = Field(description="Is it independent (not a subsidiary/PE-backed/franchise)? Cite evidence")
    succession_signals: list[str] = Field(description="Up to 4 short signals suggesting the owner may exit")
    exit_assessment: int = Field(description="0-100 likelihood the owner would entertain a sale in 1-3 years")
    exit_reasoning: str = Field(description="Two sentences justifying exit_assessment")
    analyst_note: str = Field(description="Two-line note a searcher would want before calling")
    outreach_angle: str = Field(description="One opening sentence a buyer could use, specific to this company")


class LLMProvider(Protocol):
    name: str

    async def analyze(self, lead: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any] | None: ...


def build_prompt(lead: dict[str, Any], extracted: dict[str, Any]) -> str:
    facts = {
        "company": lead.get("company"), "industry": lead.get("industry"), "category": lead.get("category"),
        "city": lead.get("city"), "state": lead.get("state"), "employees": lead.get("employees"),
        "revenue_usd": lead.get("revenue_usd"), "year_founded": lead.get("year_founded"),
        "owner_name": lead.get("owner_name"), "owner_title": lead.get("owner_title"),
    }
    signals = {k: v for k, v in extracted.items() if k not in ("text_excerpt", "pages_read") and v}
    return (
        "You are an acquisition analyst helping a search-fund entrepreneur decide which small-business owners "
        "to call about buying their company. Read the CSV facts, the extracted website signals and the website "
        "text. Answer strictly in the JSON schema. Be conservative: if evidence is missing say unknown/null. "
        "Never invent facts that are not in the text.\n\n"
        f"CSV FACTS:\n{facts}\n\nEXTRACTED SIGNALS:\n{signals}\n\nWEBSITE TEXT:\n{extracted.get('text_excerpt', '')[:3000]}"
    )
