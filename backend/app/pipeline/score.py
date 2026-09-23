"""Scoring. Fit = rules only. Exit-Readiness = rule signals blended with an optional AI assessment.

Every factor returns {factor, points, max, reason} so the UI can explain the number.
"""
from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from typing import Any

from ..config import settings


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    with open(settings.score_config_path, encoding="utf-8") as f:
        return json.load(f)


def preset_weights(preset: str, override: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = load_config()
    base = cfg["presets"].get(preset) or cfg["presets"]["searcher"]
    if not override:
        return base
    merged = {**base, "fit": dict(base["fit"]), "exit": dict(base["exit"])}
    for section in ("fit", "exit"):
        for k, v in (override.get(section) or {}).items():
            if k in merged[section] and isinstance(v, (int, float)) and 0 <= v <= 100:
                merged[section][k] = int(v)
    return merged


def _band(value: int | None, full: list[int], half: list[int], max_pts: int, label: str, unit: str = "") -> dict:
    if value is None:
        return {"factor": label, "points": 0, "max": max_pts, "reason": f"{label} unknown (not in export yet)", "known": False}
    v = value
    fmt = _fmt_money if unit == "$" else (lambda x: f"{x:,}")
    if full[0] <= v <= full[1]:
        return {"factor": label, "points": max_pts, "max": max_pts, "reason": f"{label} {fmt(v)} in target band"}
    if half[0] <= v <= half[1]:
        return {"factor": label, "points": round(max_pts * 0.5), "max": max_pts, "reason": f"{label} {fmt(v)} near target band"}
    return {"factor": label, "points": round(max_pts * 0.1), "max": max_pts, "reason": f"{label} {fmt(v)} outside band"}


def _fmt_money(v: int) -> str:
    if v >= 1_000_000_000:
        return f"${v/1e9:.1f}B"
    if v >= 1_000_000:
        return f"${v/1e6:.1f}M"
    if v >= 1_000:
        return f"${v/1e3:.0f}K"
    return f"${v}"


def _industry_text(lead: dict[str, Any]) -> str:
    return " ".join(str(lead.get(k) or "") for k in ("industry", "category")).lower()


def _matches(text: str, terms: list[str]) -> str | None:
    for t in terms:
        if t in text:
            return t
    return None


def fit_score(lead: dict[str, Any], preset: str = "searcher", override: dict[str, Any] | None = None) -> tuple[int, str, list[dict[str, Any]]]:
    """Acquisition Fit. Unknown factors are excluded from the denominator (a raw SaaSquatch scrape has no
    revenue/employees/year yet); the share of weight that was actually known is reported as `confidence`
    in the last breakdown entry so the UI can show it."""
    cfg = load_config()
    w = preset_weights(preset, override)
    fw = w["fit"]
    bd: list[dict[str, Any]] = []

    bd.append(_band(lead.get("revenue_usd"), *w["revenue_bands"].values(), fw["revenue"], "Revenue", "$"))

    yrs = None if not lead.get("year_founded") else datetime.now().year - int(lead["year_founded"])
    m = fw["years"]
    if yrs is None:
        bd.append({"factor": "Years in business", "points": 0, "max": m, "reason": "Founding year unknown (Web Intel can find it)", "known": False})
    elif yrs >= 15:
        bd.append({"factor": "Years in business", "points": m, "max": m, "reason": f"{yrs} years in business"})
    elif yrs >= 8:
        bd.append({"factor": "Years in business", "points": round(m * 0.66), "max": m, "reason": f"{yrs} years in business"})
    elif yrs >= 5:
        bd.append({"factor": "Years in business", "points": round(m * 0.33), "max": m, "reason": f"{yrs} years in business"})
    else:
        bd.append({"factor": "Years in business", "points": round(m * 0.1), "max": m, "reason": f"Only {yrs} years in business"})

    bd.append(_band(lead.get("employees"), *w["employee_bands"].values(), fw["employees"], "Employees"))

    m = fw["business_model"]
    bt = lead.get("business_type")
    if bt:
        pts = {"B2B": m, "B2B2C": round(m * 0.6), "B2C": round(m * 0.3)}.get(bt, round(m * 0.3))
        bd.append({"factor": "Business model", "points": pts, "max": m, "reason": bt})
    else:
        bd.append({"factor": "Business model", "points": 0, "max": m, "reason": "Model unknown", "known": False})

    m = fw["industry"]
    text = _industry_text(lead).strip()
    if not text:
        bd.append({"factor": "Industry", "points": 0, "max": m, "reason": "Industry unknown", "known": False})
    elif hit := _matches(text, cfg["volatile_industries"]):
        bd.append({"factor": "Industry", "points": round(m * 0.2), "max": m, "reason": f"Volatile sector ({hit})"})
    elif hit := _matches(text, cfg["stable_industries"]):
        bd.append({"factor": "Industry", "points": m, "max": m, "reason": f"Stable sector ({hit})"})
    else:
        bd.append({"factor": "Industry", "points": round(m * 0.5), "max": m, "reason": "Sector not classified"})

    m = fw["reachability"]
    have = [k for k in ("email", "phone", "owner_name") if lead.get(k)]
    if lead.get("linkedin") and "owner_name" not in have:
        have.append("linkedin")
    pts = round(m * min(3, len(have)) / 3)
    bd.append({"factor": "Reachability", "points": pts, "max": m, "reason": ("Has " + ", ".join(have)) if have else "No contact channel"})

    m = fw["completeness"]
    q = int(lead.get("quality_score") or 0)
    bd.append({"factor": "Data completeness", "points": round(m * q / 100), "max": m, "reason": f"Quality score {q}/100"})

    total = sum(b["points"] for b in bd)
    all_max = sum(b["max"] for b in bd) or 100
    known_max = sum(b["max"] for b in bd if b.get("known", True)) or 1
    score = round(100 * total / known_max)
    confidence = round(100 * known_max / all_max)
    bd.append({"factor": "Confidence", "points": confidence, "max": 100, "known": True, "confidence": confidence,
               "reason": f"{confidence}% of the scoring weight had data" + ("" if confidence == 100 else "; unknown factors are not counted against the lead")})
    return score, grade_for(score), bd


def fit_confidence(breakdown: list[dict[str, Any]]) -> int:
    for b in breakdown:
        if "confidence" in b:
            return int(b["confidence"])
    return 100


def grade_for(score: int) -> str:
    g = load_config()["grades"]
    if score >= g["A"]:
        return "A"
    if score >= g["B"]:
        return "B"
    if score >= g["C"]:
        return "C"
    return "D"


def exit_score(lead: dict[str, Any], intel: dict[str, Any] | None, preset: str = "searcher", override: dict[str, Any] | None = None) -> tuple[int, list[dict[str, Any]]]:
    """Exit-Readiness. `intel` is the Web Intel dict (extracted + optional llm) or None."""
    cfg = load_config()
    ew = preset_weights(preset, override)["exit"]
    ex = (intel or {}).get("extracted") or {}
    ai = (intel or {}).get("llm") or {}
    bd: list[dict[str, Any]] = []
    now = datetime.now().year

    # Company age: CSV year, else 'since' year on site, else first Wayback snapshot
    m = ew["company_age"]
    year = lead.get("year_founded") or ex.get("since_year") or ex.get("wayback_first_year")
    src = "CSV" if lead.get("year_founded") else ("website" if ex.get("since_year") else "Wayback")
    if year:
        age = now - int(year)
        pts = m if age >= 20 else round(m * 0.6) if age >= 15 else round(m * 0.3) if age >= 10 else round(m * 0.1)
        bd.append({"factor": "Company age", "points": pts, "max": m, "reason": f"~{age} years old ({src})"})
    else:
        bd.append({"factor": "Company age", "points": round(m * 0.2), "max": m, "reason": "Age unknown"})

    m = ew["owner_operated"]
    title = (lead.get("owner_title") or "").lower()
    owner_titles = ("owner", "founder", "president", "ceo", "principal", "proprietor")
    surname_in_name = False
    if lead.get("owner_name") and lead.get("company"):
        last = lead["owner_name"].split()[-1].lower()
        surname_in_name = len(last) > 2 and last in lead["company"].lower()
    ai_owner = (ai.get("owner_operated") or {}).get("value")
    otype = (lead.get("ownership_type") or "").lower()
    if otype and ("individual" in otype or "privately held" in otype or "family" in otype):
        bd.append({"factor": "Owner-operated", "points": round(m * 0.9), "max": m, "reason": f"SaaSquatch owner details: {lead['ownership_type']}"})
    elif otype and any(k in otype for k in ("public", "subsidiary", "private equity", "franchise")):
        bd.append({"factor": "Owner-operated", "points": 0, "max": m, "reason": f"SaaSquatch owner details: {lead['ownership_type']}"})
    elif surname_in_name:
        bd.append({"factor": "Owner-operated", "points": m, "max": m, "reason": "Owner surname appears in company name"})
    elif any(t in title for t in owner_titles):
        bd.append({"factor": "Owner-operated", "points": round(m * 0.8), "max": m, "reason": f"Contact title: {lead.get('owner_title')}"})
    elif ai_owner is True:
        bd.append({"factor": "Owner-operated", "points": round(m * 0.7), "max": m, "reason": f"AI: {(ai.get('owner_operated') or {}).get('evidence', 'owner-operated')}"})
    elif ex.get("founder_mentions"):
        bd.append({"factor": "Owner-operated", "points": round(m * 0.5), "max": m, "reason": "Founder named on website"})
    else:
        bd.append({"factor": "Owner-operated", "points": round(m * 0.15), "max": m, "reason": "No owner signal"})

    m = ew["family_language"]
    fam = ex.get("family_phrases") or []
    if fam:
        bd.append({"factor": "Family / founder language", "points": m, "max": m, "reason": f"'{fam[0]}' on website"})
    else:
        bd.append({"factor": "Family / founder language", "points": 0, "max": m, "reason": "None found"})

    m = ew["web_staleness"]
    cy = ex.get("copyright_year")
    stale_pts, reasons = 0, []
    if cy:
        if now - int(cy) >= 3:
            stale_pts += round(m * 0.5); reasons.append(f"© {cy} in footer")
        else:
            reasons.append(f"© {cy}")
    if ex.get("has_careers_page") is False:
        stale_pts += round(m * 0.25); reasons.append("no careers page")
    lw = ex.get("wayback_last_year")
    if lw and now - int(lw) >= 2:
        stale_pts += round(m * 0.25); reasons.append(f"last archived {lw}")
    if ex.get("has_blog") is False and ex.get("copyright_year"):
        stale_pts = min(m, stale_pts + round(m * 0.1)); reasons.append("no blog/news")
    bd.append({"factor": "Website staleness", "points": min(m, stale_pts), "max": m, "reason": ", ".join(reasons) or "No site data"})

    m = ew["independence"]
    acq = ex.get("acquisition_phrases") or []
    ai_ind = (ai.get("independence") or {}).get("value")
    if lead.get("parent_company"):
        bd.append({"factor": "Independent", "points": 0, "max": m, "reason": f"Parent company: {lead['parent_company']} (SaaSquatch owner details)"})
    elif otype and not acq and ai_ind is not False:
        bd.append({"factor": "Independent", "points": m, "max": m, "reason": "No parent company (SaaSquatch owner details)"})
    elif acq:
        bd.append({"factor": "Independent", "points": 0, "max": m, "reason": f"'{acq[0]}' on website"})
    elif ai_ind is False:
        bd.append({"factor": "Independent", "points": round(m * 0.1), "max": m, "reason": f"AI: {(ai.get('independence') or {}).get('evidence', 'part of a group')}"})
    elif ex:
        bd.append({"factor": "Independent", "points": m, "max": m, "reason": "No parent/PE mention on website"})
    else:
        bd.append({"factor": "Independent", "points": round(m * 0.2), "max": m, "reason": "Not checked yet (run Web Intel)"})

    m = ew["small_stable_team"]
    emp = lead.get("employees")
    if emp is None:
        bd.append({"factor": "Small stable team", "points": round(m * 0.3), "max": m, "reason": "Headcount unknown"})
    elif 5 <= emp <= 75:
        bd.append({"factor": "Small stable team", "points": m, "max": m, "reason": f"{emp} employees"})
    elif emp <= 150:
        bd.append({"factor": "Small stable team", "points": round(m * 0.5), "max": m, "reason": f"{emp} employees"})
    else:
        bd.append({"factor": "Small stable team", "points": round(m * 0.1), "max": m, "reason": f"{emp} employees"})

    m = ew["boomer_trade"]
    text = _industry_text(lead) + " " + str(ex.get("meta_description") or "").lower()
    if hit := _matches(text, cfg["boomer_trades"]):
        bd.append({"factor": "Succession-heavy trade", "points": m, "max": m, "reason": f"{hit} sector"})
    else:
        bd.append({"factor": "Succession-heavy trade", "points": round(m * 0.2), "max": m, "reason": "Not a typical succession trade"})

    total = sum(b["points"] for b in bd)
    maxsum = sum(b["max"] for b in bd) or 100
    rules = 100 * total / maxsum

    ai_score = ai.get("exit_assessment")
    if isinstance(ai_score, (int, float)) and 0 <= ai_score <= 100:
        blend = float(load_config().get("exit_ai_blend", 0.3))
        final = round((1 - blend) * rules + blend * float(ai_score))
        bd.append({"factor": "AI assessment", "points": round(ai_score), "max": 100,
                   "reason": str(ai.get("exit_reasoning") or "")[:240], "blend": blend})
    else:
        final = round(rules)
    return final, bd


def quadrant_for(fit: int, exit_: int, confidence: int = 100) -> str:
    """Quadrant from the two scores. A raw scrape row (little data, no Web Intel yet) is 'unscored',
    not 'skip': we do not know enough to dismiss it."""
    t = load_config()["quadrant_thresholds"]
    if confidence < int(t.get("min_confidence", 50)):
        return "unscored"
    hi_fit, hi_exit = fit >= t["fit"], exit_ >= t["exit"]
    if hi_fit and hi_exit:
        return "call_first"
    if hi_fit:
        return "enrich_later"
    if hi_exit:
        return "nurture"
    return "skip"
