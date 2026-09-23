"""Tier 0: deterministic cleanup of a SaaSquatch export row.

Every function is pure and unit-tested. Bad values become None plus a flag, never a guess.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import phonenumbers
from email_validator import EmailNotValidError, validate_email

NULL_TOKENS = {"", "n/a", "na", "none", "null", "-", "—", "unknown", "not available", "nan"}

# Header aliases -> internal field. Keys are normalised with _key().
COLUMN_ALIASES: dict[str, str] = {
    "company": "company", "companyname": "company", "name": "company", "business": "company",
    "industry": "industry",
    "productservicecategory": "category", "category": "category", "productcategory": "category",
    "businesstype": "business_type", "businesstypeb2bb2b2c": "business_type", "type": "business_type",
    "employeescount": "employees", "employees": "employees", "employeecount": "employees", "headcount": "employees",
    "revenue": "revenue", "annualrevenue": "revenue", "estimatedrevenue": "revenue",
    "yearfounded": "year_founded", "founded": "year_founded", "established": "year_founded",
    "bbbrating": "bbb_rating", "bbb": "bbb_rating",
    "street": "street", "address": "street", "streetaddress": "street",
    "city": "city", "state": "state", "region": "state",
    "website": "website", "url": "website", "domain": "website", "site": "website",
    "linkedin": "linkedin", "linkedinurl": "linkedin", "companylinkedin": "linkedin",
    "email": "email", "contactemail": "email",
    "phone": "phone", "phonenumber": "phone", "telephone": "phone", "companyphone": "phone", "businessphone": "phone",
    "companywebsite": "website", "companyname": "company",
    "ownername": "owner_name", "owner": "owner_name", "contactname": "owner_name", "decisionmaker": "owner_name",
    "ownertitle": "owner_title", "title": "owner_title", "jobtitle": "owner_title", "ownerstitle": "owner_title",
    # SaaSquatch "Leads History" / enriched export owner columns
    "ownersfirstname": "owner_first", "ownerfirstname": "owner_first", "firstname": "owner_first",
    "ownerslastname": "owner_last", "ownerlastname": "owner_last", "lastname": "owner_last",
    "ownerslinkedin": "owner_linkedin", "ownerlinkedin": "owner_linkedin",
    "ownersphonenumber": "owner_phone", "ownerphone": "owner_phone", "ownersphone": "owner_phone",
    "ownersemail": "owner_email", "owneremail": "owner_email",
    "source": "source", "datasource": "source",
    # SaaSquatch "Owner Details" export
    "owner": "owner_name", "parentcompany": "parent_company", "ownershiptype": "ownership_type",
}

FIELDS = [
    "company", "industry", "category", "business_type", "employees", "revenue", "year_founded",
    "bbb_rating", "street", "city", "state", "website", "linkedin", "email", "phone",
    "owner_name", "owner_title", "parent_company", "ownership_type", "source",
]

KEY_FIELDS = [
    "company", "industry", "business_type", "employees", "revenue", "year_founded",
    "city", "state", "website", "email", "phone", "owner_name",
]

US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
    "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
}
STATE_CODES = set(US_STATES.values())

DISPOSABLE_DOMAINS = {"mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com", "yopmail.com"}
FREEMAIL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com"}

_MULT = {"k": 1_000, "m": 1_000_000, "mm": 1_000_000, "b": 1_000_000_000, "bn": 1_000_000_000}


def _key(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())


def map_columns(headers: list[str]) -> dict[str, str]:
    """Return {original_header: internal_field} for recognised headers."""
    out: dict[str, str] = {}
    for h in headers:
        k = _key(h)
        if k in COLUMN_ALIASES and COLUMN_ALIASES[k] not in out.values():
            out[h] = COLUMN_ALIASES[k]
    return out


def clean_text(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in NULL_TOKENS:
        return None
    return re.sub(r"\s+", " ", s)


def parse_revenue(v: Any) -> tuple[int | None, list[str]]:
    """'$11.1M' -> 11_100_000. '4' -> None + flag (a bare small number is not a revenue)."""
    s = clean_text(v)
    if s is None:
        return None, []
    raw = s.lower().replace("usd", "").replace("$", "").replace(",", "").strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(k|m|mm|b|bn|million|billion|thousand)?", raw)
    if not m:
        rng = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(k|m|b)?\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*(k|m|b)?", raw)
        if rng:
            lo = float(rng.group(1)) * _MULT.get(rng.group(2) or rng.group(4) or "", 1)
            hi = float(rng.group(3)) * _MULT.get(rng.group(4) or rng.group(2) or "", 1)
            return int((lo + hi) / 2), ["revenue_range_midpoint"]
        return None, ["revenue_unparseable"]
    num = float(m.group(1))
    unit = (m.group(2) or "").replace("million", "m").replace("billion", "b").replace("thousand", "k")
    value = int(num * _MULT.get(unit, 1))
    if value < 10_000:
        return None, ["revenue_suspect"]
    if value > 50_000_000_000:
        return None, ["revenue_suspect"]
    return value, []


def parse_employees(v: Any) -> tuple[int | None, list[str]]:
    s = clean_text(v)
    if s is None:
        return None, []
    raw = s.lower().replace(",", "").replace("+", "").strip()
    rng = re.fullmatch(r"(\d+)\s*[-–to]+\s*(\d+)", raw)
    if rng:
        return (int(rng.group(1)) + int(rng.group(2))) // 2, ["employees_range_midpoint"]
    m = re.fullmatch(r"(\d+)(\.\d+)?", raw)
    if not m:
        return None, ["employees_unparseable"]
    n = int(m.group(1))
    flags = ["employees_fractional"] if m.group(2) else []
    if n <= 0:
        return None, ["employees_unparseable"]
    return n, flags


def parse_year(v: Any) -> tuple[int | None, list[str]]:
    s = clean_text(v)
    if s is None:
        return None, []
    m = re.search(r"(18|19|20)\d{2}", s)
    if not m:
        return None, ["year_unparseable"]
    y = int(m.group(0))
    if y > datetime.now().year or y < 1800:
        return None, ["year_out_of_range"]
    return y, []


def canonical_domain(v: Any) -> str | None:
    s = clean_text(v)
    if s is None:
        return None
    s = s.lower().strip()
    if "@" in s:
        return None
    if not re.match(r"^[a-z]+://", s):
        s = "http://" + s
    host = urlparse(s).netloc.split("@")[-1].split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    if "." not in host or " " in host:
        return None
    return host


def normalize_website(v: Any) -> tuple[str | None, str | None, list[str]]:
    dom = canonical_domain(v)
    if clean_text(v) and not dom:
        return None, None, ["website_invalid"]
    return (f"https://{dom}" if dom else None), dom, []


def normalize_email(v: Any, domain: str | None) -> tuple[str | None, list[str]]:
    s = clean_text(v)
    if s is None:
        return None, []
    s = s.lower()
    try:
        info = validate_email(s, check_deliverability=False)
    except EmailNotValidError:
        return None, ["email_invalid"]
    flags: list[str] = []
    edom = info.normalized.split("@")[1]
    if edom in DISPOSABLE_DOMAINS:
        flags.append("email_disposable")
    if edom in FREEMAIL_DOMAINS:
        flags.append("email_freemail")
    elif domain and edom != domain and not edom.endswith("." + domain) and not domain.endswith("." + edom):
        flags.append("email_domain_mismatch")
    return info.normalized, flags


def normalize_phone(v: Any) -> tuple[str | None, list[str]]:
    s = clean_text(v)
    if s is None:
        return None, []
    try:
        p = phonenumbers.parse(s, "US")
    except phonenumbers.NumberParseException:
        return None, ["phone_invalid"]
    if phonenumbers.is_valid_number(p):
        return phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.E164), []
    if phonenumbers.is_possible_number(p):
        return phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.E164), ["phone_unverified"]
    return None, ["phone_invalid"]


def normalize_state(v: Any) -> tuple[str | None, list[str]]:
    s = clean_text(v)
    if s is None:
        return None, []
    up = s.upper()
    if up in STATE_CODES:
        return up, []
    code = US_STATES.get(s.lower())
    if code:
        return code, []
    return s, ["state_unrecognised"]


def normalize_business_type(v: Any) -> str | None:
    s = clean_text(v)
    if s is None:
        return None
    u = s.upper().replace(" ", "")
    if "B2B2C" in u:
        return "B2B2C"
    if "B2B" in u and "B2C" in u:
        return "B2B2C"
    if "B2B" in u:
        return "B2B"
    if "B2C" in u or "D2C" in u:
        return "B2C"
    return None


def normalize_linkedin(v: Any) -> tuple[str | None, list[str]]:
    s = clean_text(v)
    if s is None:
        return None, []
    if "linkedin.com/" not in s.lower():
        return None, ["linkedin_invalid"]
    if not re.match(r"^[a-z]+://", s.lower()):
        s = "https://" + s
    return s.split("?")[0].rstrip("/"), []


def normalize_row(raw: dict[str, Any], colmap: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    """Map a raw CSV row through the column map and clean every field."""
    r = {colmap[h]: raw.get(h) for h in colmap}
    out: dict[str, Any] = {f: None for f in FIELDS}
    flags: list[str] = []

    out["company"] = clean_text(r.get("company")) or ""
    if not out["company"]:
        flags.append("company_missing")
    # Owner split across first/last (SaaSquatch enriched export) -> one owner_name
    if not clean_text(r.get("owner_name")):
        parts = [clean_text(r.get("owner_first")), clean_text(r.get("owner_last"))]
        if any(parts):
            r["owner_name"] = " ".join(p for p in parts if p)
    # Direct owner contact beats a generic company inbox; fall back to it when the company field is empty
    if not clean_text(r.get("email")) and clean_text(r.get("owner_email")):
        r["email"] = r["owner_email"]
        flags.append("email_is_owner_direct")
    if not clean_text(r.get("phone")) and clean_text(r.get("owner_phone")):
        r["phone"] = r["owner_phone"]
        flags.append("phone_is_owner_direct")
    if not clean_text(r.get("linkedin")) and clean_text(r.get("owner_linkedin")):
        r["linkedin"] = r["owner_linkedin"]
    for f in ("industry", "category", "bbb_rating", "street", "city", "owner_name", "owner_title", "parent_company", "ownership_type", "source"):
        out[f] = clean_text(r.get(f))
    if out["bbb_rating"]:
        out["bbb_rating"] = out["bbb_rating"].upper()

    out["business_type"] = normalize_business_type(r.get("business_type"))
    out["employees"], f1 = parse_employees(r.get("employees"))
    out["revenue"], f2 = parse_revenue(r.get("revenue"))
    out["year_founded"], f3 = parse_year(r.get("year_founded"))
    out["website"], out["domain"], f4 = normalize_website(r.get("website"))
    out["email"], f5 = normalize_email(r.get("email"), out["domain"])
    out["phone"], f6 = normalize_phone(r.get("phone"))
    out["state"], f7 = normalize_state(r.get("state"))
    out["linkedin"], f8 = normalize_linkedin(r.get("linkedin"))
    flags += f1 + f2 + f3 + f4 + f5 + f6 + f7 + f8
    return out, flags


def quality_score(row: dict[str, Any], flags: list[str]) -> int:
    present = sum(1 for f in KEY_FIELDS if row.get(f) not in (None, ""))
    base = round(100 * present / len(KEY_FIELDS))
    penalty = 6 * sum(1 for f in flags if f.endswith(("_invalid", "_unparseable", "_suspect", "_mismatch")))
    return max(0, min(100, base - penalty))
