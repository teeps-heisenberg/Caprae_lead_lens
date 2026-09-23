"""Credit Optimizer: given N SaaSquatch enrichment credits, which leads should be unlocked?

A credit buys the contact profile (email, phone, LinkedIn). So a credit is only worth
spending on a lead that (a) we cannot already reach and (b) is worth reaching.
"""
from __future__ import annotations

from typing import Any

from ..models import Lead

QUADRANT_PRIORITY = {"call_first": 4, "enrich_later": 3, "unscored": 2, "nurture": 1, "skip": 0}


def needs_credit(lead: Lead) -> bool:
    return not (lead.email and lead.phone)


def priority(lead: Lead) -> float:
    return QUADRANT_PRIORITY[lead.quadrant] * 10_000 + lead.fit_score * lead.exit_score / 100 + lead.fit_score


def optimize(leads: list[Lead], credits: int) -> dict[str, Any]:
    ranked = sorted(leads, key=priority, reverse=True)
    already_reachable = [l for l in ranked if not needs_credit(l) and l.quadrant in ("call_first", "enrich_later")]
    candidates = [l for l in ranked if needs_credit(l) and l.quadrant != "skip"]
    picks = candidates[:credits]
    skipped_low_value = [l for l in leads if needs_credit(l) and l.quadrant == "skip"]
    dup_rows_removed = sum(max(0, len(l.merged_from) - 1) for l in leads)

    return {
        "credits": credits,
        "picks": [
            {"id": l.id, "company": l.company, "quadrant": l.quadrant, "fit_score": l.fit_score,
             "exit_score": l.exit_score, "missing": [k for k in ("email", "phone") if not getattr(l, k)]}
            for l in picks
        ],
        "summary": {
            "credits_used": len(picks),
            "credits_left": max(0, credits - len(picks)),
            "candidates_needing_credit": len(candidates),
            "already_reachable_free": len(already_reachable),
            "credits_avoided_low_value": len(skipped_low_value),
            "credits_saved_by_dedupe": dup_rows_removed,
            "call_first_in_picks": sum(1 for l in picks if l.quadrant == "call_first"),
        },
        "free_calls": [{"id": l.id, "company": l.company, "quadrant": l.quadrant} for l in already_reachable[:25]],
    }
