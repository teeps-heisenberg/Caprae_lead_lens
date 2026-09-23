from app.pipeline.score import exit_score, fit_score, grade_for, quadrant_for


def _lead(**kw):
    base = {"company": "Northstar HVAC", "industry": "HVAC Contractor", "category": "Heating, Cooling",
            "business_type": "B2B", "employees": 32, "revenue_usd": 6_500_000, "year_founded": 1994,
            "email": "info@northstar.example", "phone": "+13125550100", "owner_name": "Dale Northstar",
            "owner_title": "Owner", "linkedin": None, "quality_score": 85}
    base.update(kw)
    return base


def test_ideal_searcher_target_scores_a():
    score, grade, bd = fit_score(_lead(), "searcher")
    assert grade == "A" and score >= 80
    assert all({"factor", "points", "max", "reason"} <= set(b) for b in bd)


def test_young_b2c_scores_low():
    score, grade, _ = fit_score(_lead(year_founded=2023, business_type="B2C", revenue_usd=120_000, employees=2,
                                      industry="Crypto exchange", category="", email=None, phone=None, owner_name=None,
                                      quality_score=30), "searcher")
    assert grade in ("C", "D") and score < 62


def test_exit_uses_intel_and_ai_blend():
    lead = _lead()
    no_intel, _ = exit_score(lead, None)
    intel = {"extracted": {"copyright_year": 2018, "has_careers_page": False, "family_phrases": ["family owned"],
                           "acquisition_phrases": [], "since_year": 1994},
             "llm": {"exit_assessment": 90, "exit_reasoning": "Owner near retirement age, stale site."}}
    with_intel, bd = exit_score(lead, intel)
    assert with_intel > no_intel
    assert any(b["factor"] == "AI assessment" for b in bd)
    acquired = {"extracted": {"acquisition_phrases": ["a division of"]}, "llm": None}
    acq_score, _ = exit_score(lead, acquired)
    assert acq_score < with_intel


def test_grades_and_quadrants():
    assert grade_for(85) == "A" and grade_for(65) == "B" and grade_for(45) == "C" and grade_for(10) == "D"
    assert quadrant_for(80, 70) == "call_first"
    assert quadrant_for(80, 20) == "enrich_later"
    assert quadrant_for(20, 70) == "nurture"
    assert quadrant_for(20, 20) == "skip"
    assert quadrant_for(20, 20, confidence=35) == "unscored"  # thin scrape row: not enough data to dismiss
