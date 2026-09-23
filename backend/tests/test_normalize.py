from app.pipeline.normalize import (
    canonical_domain, map_columns, normalize_email, normalize_phone, normalize_row, normalize_state,
    parse_employees, parse_revenue, parse_year, quality_score,
)


def test_parse_revenue_formats():
    assert parse_revenue("$11.1M") == (11_100_000, [])
    assert parse_revenue("850K") == (850_000, [])
    assert parse_revenue("$1.2B") == (1_200_000_000, [])
    assert parse_revenue("4,200,000") == (4_200_000, [])
    assert parse_revenue("1.1 million") == (1_100_000, [])
    assert parse_revenue("N/A") == (None, [])


def test_parse_revenue_garbage_is_flagged_not_guessed():
    assert parse_revenue("4") == (None, ["revenue_suspect"])
    assert parse_revenue("lots") == (None, ["revenue_unparseable"])
    v, f = parse_revenue("$1M-$5M")
    assert v == 3_000_000 and f == ["revenue_range_midpoint"]


def test_parse_employees():
    assert parse_employees("79") == (79, [])
    assert parse_employees("13.1") == (13, ["employees_fractional"])
    assert parse_employees("10-50") == (30, ["employees_range_midpoint"])
    assert parse_employees("N/A") == (None, [])
    assert parse_employees("many") == (None, ["employees_unparseable"])


def test_parse_year():
    assert parse_year("2014") == (2014, [])
    assert parse_year("Est. 1987") == (1987, [])
    assert parse_year("2099") == (None, ["year_out_of_range"])
    assert parse_year("-") == (None, [])


def test_domain_and_email():
    assert canonical_domain("https://www.Acme.com/about") == "acme.com"
    assert canonical_domain("acme.com") == "acme.com"
    assert canonical_domain("not a site") is None
    assert normalize_email("Info@Acme.com", "acme.com") == ("info@acme.com", [])
    assert normalize_email("bob@gmail.com", "acme.com") == ("bob@gmail.com", ["email_freemail"])
    assert normalize_email("bob@other.com", "acme.com") == ("bob@other.com", ["email_domain_mismatch"])
    assert normalize_email("john@", "acme.com") == (None, ["email_invalid"])


def test_phone_and_state():
    v, f = normalize_phone("(312) 555-0142")
    assert v == "+13125550142"
    assert normalize_phone("12") == (None, ["phone_invalid"])
    assert normalize_state("Illinois") == ("IL", [])
    assert normalize_state("il") == ("IL", [])
    assert normalize_state("Ontario") == ("Ontario", ["state_unrecognised"])


def test_map_columns_handles_saasquatch_headers():
    headers = ["Company", "Industry", "Product/Service Category", "Business Type (B2B, B2B2C)", "Employees Count",
               "Revenue", "Year Founded", "BBB Rating", "Street", "City", "State", "Website", "LinkedIn", "Email",
               "Phone", "Owner Name", "Owner Title", "Source"]
    m = map_columns(headers)
    assert m["Business Type (B2B, B2B2C)"] == "business_type"
    assert m["Employees Count"] == "employees"
    assert len(m) == 18


def test_normalize_row_and_quality():
    headers = ["Company", "Revenue", "Employees Count", "Website", "Email", "State"]
    colmap = map_columns(headers)
    row = {"Company": " InfiVR ", "Revenue": "4", "Employees Count": "13.1", "Website": "infivr.example",
           "Email": "hi@infivr.example", "State": "IL"}
    clean, flags = normalize_row(row, colmap)
    assert clean["company"] == "InfiVR"
    assert clean["revenue"] is None and "revenue_suspect" in flags
    assert clean["employees"] == 13 and "employees_fractional" in flags
    assert clean["domain"] == "infivr.example"
    q = quality_score(clean, flags)
    assert 0 <= q <= 100
