from app.pipeline.dedupe import find_clusters, merge_cluster, name_key


def test_name_key_strips_legal_suffixes():
    assert name_key("InfiVR, Inc.") == "infivr"
    assert name_key("The Iserv Company LLC") == "iserv"


def test_clusters_by_domain_and_fuzzy_name():
    rows = [
        {"company": "InfiVR", "domain": "infivr.example", "city": "Chicago"},
        {"company": "InfiVR Inc.", "domain": None, "city": "Chicago"},
        {"company": "Infi VR", "domain": "infivr.example", "city": None},
        {"company": "Sidero", "domain": "sidero.example", "city": "Chicago"},
        {"company": "Sidero Labs", "domain": "siderolabs.example", "city": "Chicago"},  # different site -> different co
    ]
    clusters = find_clusters(rows)
    as_sets = [set(c) for c in clusters]
    assert {0, 1, 2} in as_sets
    assert {3} in as_sets and {4} in as_sets


def test_merge_prefers_trustworthy_and_records_conflicts():
    rows = [
        {"company": "InfiVR", "domain": "infivr.example", "employees": 39, "revenue": None, "city": "Chicago"},
        {"company": "InfiVR", "domain": "infivr.example", "employees": None, "revenue": 4_000_000, "city": "Chicago"},
        {"company": "InfiVR", "domain": "infivr.example", "employees": 40, "revenue": None, "city": None},
    ]
    flags = [[], ["revenue_range_midpoint"], ["employees_fractional"]]
    merged, mflags, conflicts = merge_cluster(rows, flags, [0, 1, 2], [10, 11, 12])
    assert merged["employees"] == 39  # from the cleanest row
    assert merged["revenue"] == 4_000_000  # filled from another row
    assert "merged_duplicate" in mflags
    assert any(c["field"] == "employees" for c in conflicts)
