"""Generate the demo datasets and fixture websites.

Outputs
  data/saasquatch_sample.csv       ~300 synthetic rows, SaaSquatch column names, deliberately messy
  data/real_smb_sample.csv         ~20 real US businesses (public names + websites only) for live Web Intel
  backend/fixtures/sites/<domain>/ offline HTML + meta.json for ~45 synthetic companies

Deterministic (seed 42). No real people. Synthetic domains use the reserved .example TLD.
Run:  python scripts/make_dataset.py
"""
from __future__ import annotations

import csv
import json
import random
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FIXTURES = ROOT / "backend" / "fixtures" / "sites"
NOW = datetime.now().year
rng = random.Random(42)

HEADERS = ["Company", "Industry", "Product/Service Category", "Business Type (B2B, B2B2C)", "Employees Count",
           "Revenue", "Year Founded", "BBB Rating", "Street", "City", "State", "Website", "LinkedIn", "Email",
           "Phone", "Owner Name", "Owner Title", "Source"]

METROS = [
    ("Chicago", "IL", "312"), ("Grand Rapids", "MI", "616"), ("Milwaukee", "WI", "414"), ("Columbus", "OH", "614"),
    ("Indianapolis", "IN", "317"), ("Cleveland", "OH", "216"), ("St. Louis", "MO", "314"), ("Kansas City", "MO", "816"),
    ("Minneapolis", "MN", "612"), ("Pittsburgh", "PA", "412"), ("Nashville", "TN", "615"), ("Phoenix", "AZ", "602"),
    ("Denver", "CO", "303"), ("Dallas", "TX", "214"), ("Atlanta", "GA", "404"), ("Rockford", "IL", "815"),
]
STREETS = ["Industrial Dr", "Commerce Pkwy", "W Lake St", "N Main St", "Enterprise Blvd", "Mill Rd", "Harbor Ave", "Elm St"]
SURNAMES = ["Kowalski", "Nguyen", "Brennan", "Okafor", "Lindqvist", "Patel", "Marchetti", "Schroeder", "Delgado", "Whitaker",
            "Hoffman", "Castillo", "Byrne", "Tanaka", "Reilly", "Novak", "Andersen", "Fitzgerald", "Mehta", "Gallagher",
            "Haugen", "Petrov", "Sandoval", "Kramer", "Ortiz", "Dubois", "Lambert", "Sorensen", "Baptiste", "Voss"]
FIRST = ["Dale", "Linda", "Raymond", "Carol", "Gary", "Diane", "Frank", "Susan", "Glenn", "Nancy", "Priya", "Marcus",
         "Elena", "Tom", "Ruth", "Victor", "Amara", "Kenji", "Sofia", "Walter", "Jordan", "Maya", "Neil", "Beth"]
OWNER_TITLES_LEGACY = ["Owner", "Owner", "President", "Founder & President", "Owner/Operator", "Founder", "CEO & Owner"]
OWNER_TITLES_GROWTH = ["CEO", "Co-Founder & CEO", "VP Sales", "Director of Operations", "General Manager", "Head of Growth"]
SOURCES = ["Google Maps", "Google Maps", "Apollo", "Crunchbase", "Growjo"]

# industry, categories, name nouns, business_type, revenue range, employee range, founding range, persona weights
INDUSTRIES = [
    ("HVAC Contractor", ["Heating, Cooling, Ventilation", "Commercial HVAC, Refrigeration"], ["HVAC", "Heating & Air", "Mechanical", "Climate"], "B2B", (1.2e6, 18e6), (8, 90), (1968, 2012), "legacy"),
    ("Plumbing Services", ["Commercial Plumbing, Drain Services", "Plumbing, Water Heaters"], ["Plumbing", "Plumbing & Heating", "Pipe & Drain"], "B2B2C", (0.8e6, 9e6), (6, 60), (1972, 2015), "legacy"),
    ("Precision Machining", ["CNC Machining, Metal Fabrication", "Tool & Die, Precision Parts"], ["Machine Works", "Precision Machining", "Tool & Die", "Metal Products"], "B2B", (2e6, 25e6), (12, 120), (1958, 2008), "legacy"),
    ("Packaging Manufacturer", ["Flexible Packaging, Labels", "Corrugated Boxes, Displays"], ["Packaging", "Container", "Flexible Packaging", "Box Co"], "B2B", (3e6, 40e6), (20, 180), (1961, 2010), "legacy"),
    ("Trucking & Logistics", ["Freight, LTL, Warehousing", "Regional Trucking, Dedicated Fleet"], ["Freight Lines", "Transport", "Logistics", "Trucking"], "B2B", (2.5e6, 30e6), (15, 150), (1975, 2014), "legacy"),
    ("Commercial Printing", ["Commercial Printing, Signage", "Print, Direct Mail, Fulfilment"], ["Printing", "Press", "Graphics", "Print & Sign"], "B2B", (1e6, 12e6), (8, 70), (1965, 2010), "legacy"),
    ("Landscaping Services", ["Commercial Landscaping, Snow Removal", "Grounds Maintenance, Irrigation"], ["Landscape", "Lawn & Landscape", "Grounds", "Outdoor Services"], "B2B2C", (0.9e6, 8e6), (10, 80), (1980, 2016), "legacy"),
    ("Accounting Firm", ["Tax, Bookkeeping, Advisory", "CPA Services, Payroll"], ["& Associates CPA", "Tax & Accounting", "CPA Group", "Accounting"], "B2B", (0.7e6, 6e6), (4, 40), (1978, 2015), "legacy"),
    ("Home Health Care", ["Skilled Home Health Care", "Home Health Providers, Hospice"], ["Home Health", "Home Care", "Caregivers", "Health Services"], "B2C", (1.5e6, 14e6), (20, 160), (1990, 2018), "mixed"),
    ("Dental Practice", ["General Dentistry, Orthodontics", "Family Dental, Implants"], ["Family Dental", "Dental Group", "Dentistry", "Dental Care"], "B2C", (0.9e6, 5e6), (5, 30), (1985, 2017), "legacy"),
    ("IT Services", ["Managed IT Services, Cloud", "IT Outsourcing, Cybersecurity"], ["Technologies", "IT Solutions", "Networks", "Systems"], "B2B", (1e6, 15e6), (6, 80), (1996, 2019), "mixed"),
    ("Software Development", ["Custom Software Development, Cloud", "B2B SaaS, Analytics"], ["Labs", "Software", "Digital", "Cloud"], "B2B", (0.3e6, 8e6), (3, 60), (2012, 2023), "growth"),
    ("E-Commerce", ["E-Commerce Platform Development, DTC", "Online Retail, Subscription Boxes"], ["Goods", "Supply", "Market", "Direct"], "B2C", (0.4e6, 6e6), (3, 40), (2013, 2023), "growth"),
    ("Restaurant Group", ["Restaurants, Catering", "Fast Casual, Franchise"], ["Kitchen", "Grill", "Eatery", "Hospitality"], "B2C", (0.8e6, 7e6), (15, 120), (1998, 2021), "growth"),
    ("Crypto & Blockchain", ["Crypto Exchange, DeFi", "Blockchain Consulting, NFTs"], ["Chain", "Protocol", "Ledger", "Digital Assets"], "B2C", (0.2e6, 5e6), (2, 30), (2017, 2024), "growth"),
    ("Insurance Agency", ["Commercial Insurance, Benefits", "Independent Insurance Agency"], ["Insurance Agency", "Insurance Group", "& Sons Insurance", "Risk Partners"], "B2B2C", (0.6e6, 5e6), (4, 35), (1970, 2014), "legacy"),
]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def make_name(ind: tuple, owner_last: str, metro: str, persona: str) -> str:
    nouns = ind[2]
    noun = rng.choice(nouns)
    style = rng.random()
    if persona == "legacy" and style < 0.45:
        pat = rng.choice(["{last} {noun}", "{last} & Sons {noun}", "{last} Brothers {noun}", "{last} {noun} Co."])
        return pat.format(last=owner_last, noun=noun)
    if style < 0.6:
        return f"{rng.choice(['North', 'Great Lakes', 'Prairie', 'Summit', 'Heartland', 'Tri-State', 'Midwest', 'Capital', 'Pioneer', 'Keystone'])} {noun}"
    if style < 0.8:
        return f"{metro.split()[0]} {noun}"
    return f"{rng.choice(['Apex', 'Vector', 'Bluebird', 'Ironwood', 'Redline', 'Northstar', 'Silverline', 'Clearpath', 'Cobalt', 'Granite'])} {noun}"


def make_company(i: int) -> dict:
    ind = INDUSTRIES[i % len(INDUSTRIES)] if i < len(INDUSTRIES) * 4 else rng.choice(INDUSTRIES)
    city, state, area = rng.choice(METROS)
    first, last = rng.choice(FIRST), rng.choice(SURNAMES)
    persona_pool = {"legacy": ["legacy", "legacy", "legacy", "minimal", "acquired", "no_site"],
                    "mixed": ["legacy", "growth", "minimal", "acquired", "no_site"],
                    "growth": ["growth", "growth", "minimal", "acquired"]}[ind[7]]
    persona = rng.choice(persona_pool)
    year = rng.randint(*ind[6])
    if persona == "legacy":
        year = min(year, rng.randint(ind[6][0], max(ind[6][0] + 1, 2006)))
    name = make_name(ind, last, city, persona)
    domain = None if persona == "no_site" else (slug(name)[:28].strip("-") + ".example")
    rev = int(rng.uniform(*ind[4]) // 1000 * 1000)
    emp = rng.randint(*ind[5])
    noise = rng.random()  # real scrapes are not all ideal targets
    if noise < 0.12:  # too small to buy
        rev, emp = int(rng.uniform(80e3, 450e3) // 1000 * 1000), rng.randint(1, 4)
    elif noise < 0.22:  # too big for a searcher
        rev, emp = int(rng.uniform(60e6, 400e6) // 1e6 * 1e6), rng.randint(300, 1500)
    elif noise < 0.32:  # young
        year = rng.randint(NOW - 6, NOW - 1)
    title = rng.choice(OWNER_TITLES_LEGACY if persona in ("legacy", "minimal") else OWNER_TITLES_GROWTH)
    return {
        "company": name, "industry": ind[0], "category": rng.choice(ind[1]), "business_type": ind[3],
        "employees": emp, "revenue": rev, "year_founded": year, "city": city, "state": state, "area": area,
        "street": f"{rng.randint(100, 9800)} {rng.choice(STREETS)}", "domain": domain,
        "owner_first": first, "owner_last": last, "owner_title": title, "persona": persona,
        "bbb": rng.choice(["A+", "A+", "A", "A-", "B+", "B"]),
    }


def fmt_revenue(v: int) -> str:
    r = rng.random()
    if r < 0.45:
        return f"${v/1e6:.1f}M" if v >= 1e6 else f"${v/1e3:.0f}K"
    if r < 0.6:
        return f"{v:,}"
    if r < 0.7:
        return f"${v/1e6:.1f} million" if v >= 1e6 else f"${v:,}"
    if r < 0.8:
        return f"${v:,}"
    if r < 0.86:
        return "N/A"
    if r < 0.92:
        return str(rng.choice([4, 12, 7, 1, 3]))  # garbage: a bare small number
    lo, hi = v * 0.7, v * 1.3
    return f"${lo/1e6:.1f}M-${hi/1e6:.1f}M"


def fmt_employees(v: int) -> str:
    r = rng.random()
    if r < 0.7:
        return str(v)
    if r < 0.78:
        return f"{v}.{rng.randint(1, 9)}"
    if r < 0.86:
        return f"{max(1, v - rng.randint(2, 10))}-{v + rng.randint(5, 30)}"
    return "N/A"


def fmt_phone(area: str) -> str:
    n = f"{rng.randint(100, 199):03d}"
    return rng.choice([f"({area}) 555-0{n}", f"{area}-555-0{n}", f"{area}.555.0{n}", f"+1 {area} 555 0{n}"])


def to_row(c: dict, drop_rate: float = 0.0) -> dict:
    """Render a clean company as a messy SaaSquatch-style CSV row."""
    def maybe(v, p_missing):
        return "N/A" if rng.random() < p_missing + drop_rate else v

    dom = c["domain"]
    website = "N/A" if not dom else rng.choice([f"https://www.{dom}", f"www.{dom}", dom, f"https://{dom}/"])
    email = "N/A"
    if dom and rng.random() < 0.72 + (0.1 if c["persona"] == "growth" else 0):
        r = rng.random()
        local = rng.choice(["info", "office", "contact", c["owner_first"].lower(), f"{c['owner_first'][0].lower()}{c['owner_last'].lower()}"])
        if r < 0.86:
            email = f"{local}@{dom}"
        elif r < 0.91:
            email = f"{c['owner_first'].lower()}.{c['owner_last'].lower()}@gmail.com"
        elif r < 0.95:
            email = f"{local}@"
        else:
            email = f"{local}@{rng.choice(['oldsite-mail.example', 'legacyhost.example'])}"
    year = str(c["year_founded"])
    if rng.random() < 0.03:
        year = rng.choice(["2031", "N/A", "1899"])
    return {
        "Company": c["company"],
        "Industry": maybe(c["industry"], 0.03),
        "Product/Service Category": maybe(c["category"], 0.08),
        "Business Type (B2B, B2B2C)": maybe(c["business_type"], 0.35),
        "Employees Count": maybe(fmt_employees(c["employees"]), 0.12),
        "Revenue": fmt_revenue(c["revenue"]),
        "Year Founded": maybe(year, 0.1),
        "BBB Rating": maybe(c["bbb"], 0.62),
        "Street": maybe(c["street"], 0.58),
        "City": maybe(c["city"], 0.02),
        "State": maybe(rng.choice([c["state"], c["state"], c["state"].lower(), {"IL": "Illinois", "OH": "Ohio", "MI": "Michigan"}.get(c["state"], c["state"])]), 0.05),
        "Website": website,
        "LinkedIn": maybe(f"https://www.linkedin.com/company/{slug(c['company'])}" if dom else "N/A", 0.3),
        "Email": email,
        "Phone": maybe(fmt_phone(c["area"]), 0.25),
        "Owner Name": maybe(f"{c['owner_first']} {c['owner_last']}", 0.2),
        "Owner Title": maybe(c["owner_title"], 0.25),
        "Source": rng.choice(SOURCES),
    }


def near_duplicate(c: dict) -> dict:
    d = dict(c)
    v = rng.random()
    if v < 0.35:
        d["company"] = c["company"] + rng.choice([", Inc.", " Inc", " LLC", " Co."])
    elif v < 0.6:
        d["company"] = c["company"].replace("&", "and").replace(" Co.", "")
    elif v < 0.8:
        d["company"] = re.sub(r"(\w)(\w)", r"\1\2", c["company"]).replace(" ", "  ", 1).strip()
    else:
        d["company"] = c["company"].upper()
    return d


# ---------- fixture sites ----------

def site_html(c: dict) -> dict[str, str]:
    name, ind, city, st = c["company"], c["industry"], c["city"], c["state"]
    owner = f"{c['owner_first']} {c['owner_last']}"
    year = c["year_founded"]
    p = c["persona"]
    phone = fmt_phone(c["area"])
    email = f"info@{c['domain']}"
    nav_extra = ""
    body_extra = ""
    footer_year = NOW
    about = ""
    if p == "legacy":
        footer_year = rng.randint(2016, NOW - 3)
        gen = rng.choice(["", " Now in our second generation.", " Now run by the third generation of the family."])
        body_extra = (f"<p>Family owned and operated since {year}.{gen} {owner}, Owner, still answers the phone.</p>"
                      f"<p>Serving {city} and the surrounding area for over {NOW - year} years.</p>")
        about = (f"<h1>About {name}</h1><p>{name} was founded by {owner} in {year} in {city}, {st}. "
                 f"We are a locally owned {ind.lower()} business built on handshakes and repeat customers.</p>"
                 f"<p>{owner}, Owner &amp; President</p>")
    elif p == "growth":
        nav_extra = '<a href="/careers">Careers</a><a href="/blog">Blog</a>'
        body_extra = (f"<p>{name} is a fast-growing {ind.lower()} company. We're hiring across engineering and sales.</p>"
                      f"<p>Founded in {year}. Backed by our customers, not investors.</p>")
        about = f"<h1>About</h1><p>Our team of {c['employees']}+ serves clients nationwide from {city}.</p><a href='/careers'>Join our team</a>"
    elif p == "acquired":
        nav_extra = '<a href="/careers">Careers</a>'
        group = f"{rng.choice(['Summit', 'Meridian', 'Harbor', 'Atlas'])} {rng.choice(['Holdings', 'Group', 'Partners'])}"
        body_extra = (f"<p>{name} is a division of {group}. In {rng.randint(2019, NOW - 1)} we were acquired by {group} "
                      f"to expand our {ind.lower()} footprint.</p>")
        about = f"<h1>About</h1><p>Part of the {group} family of companies. Established {year}.</p>"
        footer_year = NOW - rng.randint(0, 1)
    else:  # minimal brochure site
        footer_year = rng.randint(2015, NOW)
        body_extra = f"<p>{ind} in {city}, {st}. Est. {year}.</p>"
        about = f"<h1>{name}</h1><p>Quality {ind.lower()} since {year}.</p>"
    index = f"""<!doctype html><html><head><meta charset="utf-8"><title>{name} | {ind} in {city}, {st}</title>
<meta name="description" content="{name}: {c['category']} in {city}, {st}. {('Family owned since ' + str(year)) if p == 'legacy' else ind}.">
{'<link rel="stylesheet" href="/wp-content/themes/base/style.css">' if p in ('legacy', 'minimal') else ''}
</head><body><nav><a href="/">Home</a><a href="/about">About</a><a href="/contact">Contact</a>{nav_extra}</nav>
<h1>{name}</h1><p>{c['category']}.</p>{body_extra}
<footer>&copy; {footer_year} {name}. {c['street']}, {city}, {st}. {phone} &middot; {email}</footer></body></html>"""
    contact = f"<html><head><title>Contact {name}</title></head><body><h1>Contact</h1><p>{c['street']}, {city}, {st}</p><p>Phone: {phone}</p><p>Email: {email}</p></body></html>"
    return {"index.html": index, "about.html": f"<html><head><title>About {name}</title></head><body>{about}</body></html>", "contact.html": contact}


def site_meta(c: dict) -> dict:
    p, year = c["persona"], c["year_founded"]
    first = max(1996, year + rng.randint(0, 6))
    last = {"legacy": rng.randint(NOW - 4, NOW - 1), "growth": NOW, "acquired": NOW - rng.randint(0, 1), "minimal": rng.randint(NOW - 3, NOW)}[p]
    return {"wayback_first_year": first, "wayback_last_year": last, "mx_ok": rng.random() < 0.9}


REAL_SMBS = [
    ("Lodge Cast Iron", "lodgecastiron.com", "South Pittsburg", "TN", "Cookware Manufacturer"),
    ("Klein Tools", "kleintools.com", "Lincolnshire", "IL", "Hand Tool Manufacturer"),
    ("Zippo Manufacturing Company", "zippo.com", "Bradford", "PA", "Consumer Products Manufacturer"),
    ("Ariens Company", "ariens.com", "Brillion", "WI", "Outdoor Power Equipment"),
    ("W.S. Darley & Co.", "darley.com", "Itasca", "IL", "Fire Equipment Manufacturer"),
    ("Marlin Steel Wire Products", "marlinwire.com", "Baltimore", "MD", "Precision Machining"),
    ("Spangler Candy Company", "spanglercandy.com", "Bryan", "OH", "Confectionery Manufacturer"),
    ("Jelly Belly Candy Company", "jellybelly.com", "Fairfield", "CA", "Confectionery Manufacturer"),
    ("Nordic Ware", "nordicware.com", "Minneapolis", "MN", "Cookware Manufacturer"),
    ("Buck Knives", "buckknives.com", "Post Falls", "ID", "Knife Manufacturer"),
    ("Duluth Pack", "duluthpack.com", "Duluth", "MN", "Bag Manufacturer"),
    ("The Vermont Country Store", "vermontcountrystore.com", "Weston", "VT", "Retail"),
    ("Stonewall Kitchen", "stonewallkitchen.com", "York", "ME", "Specialty Food Manufacturer"),
    ("Bob's Red Mill", "bobsredmill.com", "Milwaukie", "OR", "Food Manufacturer"),
    ("Zingerman's Delicatessen", "zingermansdeli.com", "Ann Arbor", "MI", "Food Retail"),
    ("Faribault Mill", "faribaultmill.com", "Faribault", "MN", "Textile Manufacturer"),
    ("Rada Cutlery", "radacutlery.com", "Waverly", "IA", "Cutlery Manufacturer"),
    ("Weaver Leather", "weaverleather.com", "Mt. Hope", "OH", "Leather Goods Manufacturer"),
    ("Vermont Teddy Bear Company", "vermontteddybear.com", "Shelburne", "VT", "Toy Manufacturer"),
    ("Leatherman Tool Group", "leatherman.com", "Portland", "OR", "Multi-tool Manufacturer"),
]


def main() -> None:
    DATA.mkdir(exist_ok=True)
    if FIXTURES.exists():
        shutil.rmtree(FIXTURES)
    FIXTURES.mkdir(parents=True)

    companies = [make_company(i) for i in range(262)]
    # Ensure unique names/domains
    seen: set[str] = set()
    for c in companies:
        base = c["company"]
        k = 2
        while c["company"].lower() in seen:
            c["company"] = f"{base} {rng.choice(['of ' + c['city'], 'Group', 'Services', str(k)])}"
            k += 1
        seen.add(c["company"].lower())
        if c["domain"]:
            c["domain"] = slug(c["company"])[:30].strip("-") + ".example"

    rows: list[dict] = [to_row(c) for c in companies]
    exact_dups = rng.sample(companies, 22)
    rows += [dict(r) for r in (rows[companies.index(c)] for c in exact_dups)]
    near_dups = rng.sample([c for c in companies if c not in exact_dups], 20)
    rows += [to_row(near_duplicate(c), drop_rate=0.25) for c in near_dups]
    # a few triple duplicates like the InfiVR case in the SaaSquatch demo
    for c in rng.sample(near_dups, 4):
        rows.append(to_row(near_duplicate(c), drop_rate=0.4))
    rng.shuffle(rows)

    with open(DATA / "saasquatch_sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        w.writeheader()
        w.writerows(rows)

    # fixtures for ~45 companies with a site; ~15% of sited companies deliberately have none (unreachable sites)
    sited = [c for c in companies if c["domain"]]
    fixture_cos = rng.sample(sited, 48)
    for c in fixture_cos:
        d = FIXTURES / c["domain"]
        d.mkdir(parents=True, exist_ok=True)
        if rng.random() < 0.06:
            (d / "meta.json").write_text(json.dumps({"status": rng.choice(["timeout", "blocked"]), "note": "simulated unreachable site"}), encoding="utf-8")
            continue
        for fname, html in site_html(c).items():
            (d / fname).write_text(html, encoding="utf-8")
        (d / "meta.json").write_text(json.dumps(site_meta(c)), encoding="utf-8")

    with open(DATA / "real_smb_sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        w.writeheader()
        for name, dom, city, st, ind in REAL_SMBS:
            w.writerow({h: "N/A" for h in HEADERS} | {"Company": name, "Website": f"https://www.{dom}", "City": city,
                                                        "State": st, "Industry": ind, "Source": "Public website"})

    print(f"rows={len(rows)} unique_companies={len(companies)} fixtures={len(fixture_cos)} -> {DATA}")


if __name__ == "__main__":
    main()
