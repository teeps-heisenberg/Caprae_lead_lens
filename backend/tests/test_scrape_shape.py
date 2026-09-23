"""A raw SaaSquatch scrape (before Estimate Revenue / Enrich) has only 8 columns. The tool must still rank it."""
from app.pipeline.normalize import map_columns, normalize_row, quality_score
from app.pipeline.score import fit_confidence, fit_score

SCRAPE_HEADERS = ["Company", "Industry", "Street", "City", "State", "BBB Rating", "Company Phone", "Website"]


def test_scrape_headers_map():
    m = map_columns(SCRAPE_HEADERS)
    assert m["Company Phone"] == "phone" and m["Street"] == "street" and m["Website"] == "website"
    assert len(m) == 8


def test_unknown_factors_do_not_drag_score_and_confidence_is_reported():
    colmap = map_columns(SCRAPE_HEADERS)
    row = {"Company": "Hillco Distributing", "Industry": "Hvac Equipment", "Street": "N/A", "City": "Chicago",
           "State": "IL", "BBB Rating": "N/A", "Company Phone": "N/A", "Website": "hillcodistributing.com"}
    clean, flags = normalize_row(row, colmap)
    lead = {**clean, "revenue_usd": clean.pop("revenue"), "quality_score": quality_score(clean, flags)}
    score, grade, bd = fit_score(lead, "searcher")
    conf = fit_confidence(bd)
    assert 0 < conf < 100
    unknown = [b["factor"] for b in bd if b.get("known") is False]
    assert {"Revenue", "Years in business", "Employees", "Business model"} <= set(unknown)
    # industry is a stable/boomer trade and the website is present, so the lead is not buried
    assert score >= 40


ENRICHED_HEADERS = ["company", "website", "industry", "employees", "revenue", "yearFounded", "productCategory", "businessType",
                    "bbbRating", "street", "city", "state", "companyPhone", "companyLinkedin", "aiScore", "matched_keywords",
                    "descriptive_keywords", "aiExplanation"]
HISTORY_HEADERS = ["Company", "Website", "Industry", "Year Founded", "City", "State", "Company Phone", "Company LinkedIn",
                   "Owner's First Name", "Owner's Last Name", "Owner's Title", "Owner's LinkedIn", "Owner's Phone Number", "Owner's Email"]


def test_enriched_export_camelcase_headers_map():
    m = map_columns(ENRICHED_HEADERS)
    assert m["yearFounded"] == "year_founded" and m["productCategory"] == "category" and m["businessType"] == "business_type"
    assert m["bbbRating"] == "bbb_rating" and m["companyPhone"] == "phone" and m["companyLinkedin"] == "linkedin"
    assert "aiScore" not in m  # ignored, but kept verbatim in raw_leads


def test_leads_history_owner_columns_combine():
    colmap = map_columns(HISTORY_HEADERS)
    row = {"Company": "Park Supply", "Website": "parksupply.com", "Industry": "Plumbing Supplies", "Year Founded": "1971",
           "City": "Chicago", "State": "IL", "Company Phone": "N/A", "Company LinkedIn": "N/A",
           "Owner's First Name": "Dan", "Owner's Last Name": "Park", "Owner's Title": "Owner",
           "Owner's LinkedIn": "linkedin.com/in/danpark", "Owner's Phone Number": "(312) 555-0101", "Owner's Email": "dan@parksupply.com"}
    clean, flags = normalize_row(row, colmap)
    assert clean["owner_name"] == "Dan Park" and clean["owner_title"] == "Owner"
    assert clean["email"] == "dan@parksupply.com" and "email_is_owner_direct" in flags
    assert clean["phone"] == "+13125550101" and "phone_is_owner_direct" in flags
    assert clean["linkedin"] and "linkedin.com/in/danpark" in clean["linkedin"]


OWNER_DETAILS_HEADERS = ["Company", "Owner", "Company LinkedIn", "Owner LinkedIn", "Parent Company", "Affiliated Companies",
                         "Ownership Type", "Confidence", "Sources"]


def test_owner_details_export_feeds_exit_score():
    from app.pipeline.score import exit_score

    colmap = map_columns(OWNER_DETAILS_HEADERS)
    base = {"Company": "Chicago Brass, Inc.", "Owner": "Kurt Schnakenberg", "Company LinkedIn": "NaN",
            "Owner LinkedIn": "https://linkedin.com/in/kurt", "Affiliated Companies": "ADBM", "Confidence": "high", "Sources": "..."}
    indep, _ = normalize_row({**base, "Parent Company": "NaN", "Ownership Type": "Privately Held Individual"}, colmap)
    owned, _ = normalize_row({**base, "Parent Company": "Summit Holdings", "Ownership Type": "Subsidiary"}, colmap)
    assert indep["owner_name"] == "Kurt Schnakenberg" and indep["parent_company"] is None  # NaN -> null
    assert indep["linkedin"] and "kurt" in indep["linkedin"]
    s1, bd1 = exit_score({**indep, "revenue_usd": None}, None)
    s2, bd2 = exit_score({**owned, "revenue_usd": None}, None)
    assert s1 > s2
    assert any("Privately Held" in b["reason"] for b in bd1)
    assert any("Summit Holdings" in b["reason"] for b in bd2)


def test_import_export_roundtrip_columns():
    from app.services.export import SAASQUATCH_COLUMNS

    assert SAASQUATCH_COLUMNS[:2] == ["Company", "Industry"]  # the two Import Leads requires
    assert "Business Phone" in SAASQUATCH_COLUMNS and "Website" in SAASQUATCH_COLUMNS
