"""Rule-based fallback that fills the same IntelAnalysis shape from extracted signals.
Runs when no LLM key is configured, so the product never depends on an API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .base import IntelAnalysis, Judgement


class RulesProvider:
    name = "rules"

    async def analyze(self, lead: dict[str, Any], ex: dict[str, Any]) -> dict[str, Any] | None:
        if not ex:
            return None
        now = datetime.now().year
        signals: list[str] = []
        if ex.get("family_phrases"):
            signals.append(f"'{ex['family_phrases'][0]}' language")
        year = lead.get("year_founded") or ex.get("since_year")
        if year and now - int(year) >= 20:
            signals.append(f"{now - int(year)} years in business")
        if ex.get("copyright_year") and now - int(ex["copyright_year"]) >= 3:
            signals.append(f"website last touched ~{ex['copyright_year']}")
        if ex.get("has_careers_page") is False:
            signals.append("not hiring publicly")
        title = (lead.get("owner_title") or "").lower()
        owner = any(t in title for t in ("owner", "founder", "president", "proprietor"))
        owner_ev = f"contact title '{lead.get('owner_title')}'" if owner else (
            f"founder named on site: {ex['founder_mentions'][0]}" if ex.get("founder_mentions") else "no explicit signal")
        indep = not ex.get("acquisition_phrases")
        indep_ev = f"'{ex['acquisition_phrases'][0]}' on site" if not indep else "no parent/PE mention"

        score = 20 + 15 * len(signals[:4]) + (15 if owner else 0) + (10 if indep else -20)
        model = lead.get("business_type") or "unknown"
        what = ex.get("meta_description") or ex.get("title") or f"{lead.get('company')} ({lead.get('industry') or 'industry unknown'})"
        name = (lead.get("owner_name") or "").split(" ")[0] or "there"
        hook = (f"that it's {ex['family_phrases'][0]}" if ex.get("family_phrases")
                else f"your {now - int(year)} years in business" if year else "the reputation you've built")
        out = IntelAnalysis(
            what_they_sell=str(what)[:200],
            business_model=model,
            industry_normalized=(lead.get("industry") or "unknown")[:60],
            owner_operated=Judgement(value=owner or bool(ex.get("founder_mentions")), evidence=owner_ev),
            independence=Judgement(value=indep, evidence=indep_ev),
            succession_signals=signals[:4],
            exit_assessment=max(0, min(100, score)),
            exit_reasoning="Rule-based estimate from company age, website staleness, ownership language and independence. "
                           "Add an LLM key for a text-aware assessment.",
            analyst_note=f"{lead.get('company')}: {', '.join(signals) or 'few public signals'}. {indep_ev.capitalize()}.",
            outreach_angle=f"Hi {name}, I've followed {lead.get('company')} and admire {hook}; I'm an operator looking to carry on what you've built, not flip it.",
        )
        return out.model_dump()
