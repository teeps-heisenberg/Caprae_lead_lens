from __future__ import annotations

import csv
import io

from ..models import Lead

COLUMNS = [
    "quadrant", "fit_score", "fit_grade", "exit_score", "quality_score", "company", "industry", "category",
    "business_type", "employees", "revenue_usd", "year_founded", "bbb_rating", "city", "state", "street",
    "website", "linkedin", "email", "phone", "owner_name", "owner_title", "source",
    "fit_reasons", "exit_reasons", "flags", "outreach_angle", "merged_rows",
]


# Exactly the schema SaaSquatch's "Import Leads" dialog accepts (Required: Company, Industry;
# Good to have: City, State, Business Phone, Website; Optional: Street, BBB Rating).
SAASQUATCH_COLUMNS = ["Company", "Industry", "City", "State", "Business Phone", "Website", "Street", "BBB Rating"]


def leads_to_saasquatch_csv(leads: list[Lead]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(SAASQUATCH_COLUMNS)
    for l in leads:
        w.writerow([l.company, l.industry or "", l.city or "", l.state or "", l.phone or "", l.website or "", l.street or "", l.bbb_rating or ""])
    return buf.getvalue()


def leads_to_csv(leads: list[Lead]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, extrasaction="ignore")
    w.writeheader()
    for l in leads:
        d = l.model_dump()
        d["fit_reasons"] = " | ".join(b["reason"] for b in l.fit_breakdown)
        d["exit_reasons"] = " | ".join(b["reason"] for b in l.exit_breakdown)
        d["flags"] = ", ".join(l.flags)
        d["outreach_angle"] = ((l.web_intel or {}).get("llm") or {}).get("outreach_angle", "")
        d["merged_rows"] = len(l.merged_from)
        w.writerow(d)
    return buf.getvalue()
