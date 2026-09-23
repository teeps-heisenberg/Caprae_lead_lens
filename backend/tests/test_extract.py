from app.pipeline.extract import extract

HOME = """<html><head><title>Northstar HVAC | Heating & Cooling</title>
<meta name="description" content="Family owned HVAC contractor serving Chicago since 1994."></head>
<body><nav><a href="/about">About</a><a href="/contact">Contact</a></nav>
<p>Family owned and operated since 1994. Dale Northstar, Owner, still answers the phone.</p>
<p>Call (312) 555-0100 or email info@northstar.example</p>
<footer>&copy; 2018 Northstar HVAC</footer></body></html>"""

GROWTH = """<html><head><title>Acme Cloud</title></head><body>
<a href="/careers">We're hiring</a><a href="/blog">Blog</a>
<p>Acme Cloud is a division of MegaCorp Holdings.</p><footer>© 2026 Acme</footer></body></html>"""


def test_extract_legacy_signals():
    ex = extract({"/": HOME})
    assert ex["copyright_year"] == 2018
    assert ex["since_year"] == 1994
    assert "family owned" in ex["family_phrases"]
    assert ex["founder_mentions"] and "Dale Northstar" in ex["founder_mentions"][0]
    assert ex["has_careers_page"] is False
    assert "info@northstar.example" in ex["emails_on_site"]
    assert ex["phones_on_site"]
    assert ex["meta_description"].startswith("Family owned")


def test_extract_growth_and_acquired():
    ex = extract({"/": GROWTH})
    assert ex["has_careers_page"] is True and ex["has_blog"] is True
    assert ex["copyright_year"] == 2026
    assert "a division of" in ex["acquisition_phrases"]


def test_founder_regex_ignores_lowercase_prose():
    ex = extract({"/": "<p>we want to be an owner of the north side of chicago founder market. Maria Lopez, Owner.</p>"})
    assert ex["founder_mentions"] == ["Maria Lopez"]
    ex = extract({"/": "<nav>Certification About The Founder</nav><p>Column Nikki Liddy, President</p>"})
    assert ex["founder_mentions"] == ["Nikki Liddy"]


def test_thin_js_shell_is_detected():
    from app.pipeline.extract import is_thin

    shell = "<html><head><script>" + "x" * 8000 + "</script></head><body><div id='root'></div></body></html>"
    assert is_thin(extract({"/": shell})) is True
    assert is_thin(extract({"/": HOME})) is False


def test_extract_empty():
    assert extract({})["pages_read"] == []
