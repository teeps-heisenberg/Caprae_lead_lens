"""Turn fetched HTML pages into structured signals. Pure functions, no network."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

FAMILY_PHRASES = [
    "family owned", "family-owned", "family run", "family-run", "family business", "second generation",
    "third generation", "2nd generation", "3rd generation", "father and son", "father-and-son",
    "locally owned", "owner operated", "owner-operated", "founded by", "started by", "husband and wife",
]
# Ownership-change language. Generic phrases ("backed by", "part of the") only count with a corporate object,
# so "backed by our lifetime guarantee" or "part of the community" do not flag a company as acquired.
ACQUISITION_PATTERNS = [
    (r"\bacquired by\b", "acquired by"), (r"\ba division of\b", "a division of"), (r"\b(?:a )?subsidiary of\b", "subsidiary of"),
    (r"\bportfolio company\b", "portfolio company"), (r"\bwholly[- ]owned\b", "wholly owned"), (r"\bmerged with\b", "merged with"),
    (r"\bnow part of\b", "now part of"), (r"\bis owned by\b", "is owned by"), (r"\ban affiliate of\b", "an affiliate of"),
    (r"\bpart of the [\w&' -]{1,40}\b(?:group|holdings|family of companies|family of brands|portfolio|corporation)\b", "part of the ... group"),
    (r"\bbacked by [\w&' -]{1,40}\b(?:capital|partners|equity|investors|ventures|holdings)\b", "backed by ... capital"),
    (r"\bprivate equity\b", "private equity"),
]
CAREERS_HINTS = ("career", "careers", "jobs", "join-our-team", "join our team", "we're hiring", "we are hiring", "employment")
BLOG_HINTS = ("blog", "news", "insights", "press", "articles")
TECH_HINTS = {
    "wordpress": "WordPress", "wp-content": "WordPress", "shopify": "Shopify", "wix.com": "Wix",
    "squarespace": "Squarespace", "hubspot": "HubSpot", "godaddy": "GoDaddy Builder", "webflow": "Webflow",
}
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\(?\b\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
YEAR = r"((?:18|19|20)\d{2})"
COPYRIGHT_RE = re.compile(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?" + YEAR, re.I)
SINCE_RE = re.compile(r"\b(?:since|est\.?|established(?: in)?|founded(?: in)?|serving [a-z ]+ since)\s+" + YEAR, re.I)
# Name part is case-sensitive (two or three Capitalised words); only the title part is case-insensitive.
FOUNDER_RE = re.compile(r"\b([A-Z][a-z]{1,}(?: [A-Z][a-z]{1,}){1,2}),?\s+(?:(?i:our|the|is|as)\s+)?(?i:founder|owner|president|ceo)\b")


NAME_STOPWORDS = {
    "about", "the", "our", "home", "contact", "menu", "column", "certification", "certified", "company", "team", "meet",
    "services", "products", "news", "blog", "careers", "login", "search", "welcome", "read", "more", "learn", "view",
    "from", "with", "and", "for", "new", "your", "all", "get", "call", "email", "phone", "us", "inc", "llc", "co",
}


def _clean_names(cands: list[str]) -> list[str]:
    """Keep only plausible person names: 2–3 capitalised words, none of which is a nav/marketing word."""
    out: list[str] = []
    for c in cands:
        words = c.strip().split()
        if not 2 <= len(words) <= 3 or any(w.lower() in NAME_STOPWORDS for w in words):
            continue
        # a 3-word hit that starts with junk but ends in a real name ("Column Nikki Liddy") is dropped above; try the tail
        if c not in out:
            out.append(c)
    if not out:  # second pass: salvage "<junk> First Last" by taking the last two words
        for c in cands:
            words = c.strip().split()
            tail = " ".join(words[-2:])
            if len(words) == 3 and not any(w.lower() in NAME_STOPWORDS for w in words[-2:]) and tail not in out:
                out.append(tail)
    return out[:3]


def _text(soup: BeautifulSoup) -> str:
    for t in soup(["script", "style", "noscript", "svg"]):
        t.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))


def extract(pages: dict[str, str]) -> dict[str, Any]:
    """pages: {path: html}. Returns a flat dict of signals."""
    out: dict[str, Any] = {
        "pages_read": sorted(pages.keys()),
        "title": None, "meta_description": None,
        "copyright_year": None, "since_year": None,
        "family_phrases": [], "acquisition_phrases": [], "founder_mentions": [],
        "has_careers_page": False, "has_blog": False,
        "emails_on_site": [], "phones_on_site": [], "social_links": {},
        "tech_hints": [], "text_excerpt": "", "text_chars": 0, "html_chars": 0,
    }
    if not pages:
        return out

    all_text: list[str] = []
    all_html = "\n".join(pages.values()).lower()
    now = datetime.now().year

    for path, html in pages.items():
        soup = BeautifulSoup(html, "lxml")
        if path in ("/", "/index.html") or out["title"] is None:
            if soup.title and soup.title.string:
                out["title"] = soup.title.string.strip()[:160]
            md = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
            if md and md.get("content"):
                out["meta_description"] = md["content"].strip()[:300]
        for a in soup.find_all("a", href=True):
            href, label = a["href"].lower(), a.get_text(" ", strip=True).lower()
            if any(h in href or h in label for h in CAREERS_HINTS):
                out["has_careers_page"] = True
            if any(f"/{h}" in href for h in BLOG_HINTS) or label in BLOG_HINTS:
                out["has_blog"] = True
            for net in ("linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com", "youtube.com"):
                if net in href and net.split(".")[0] not in out["social_links"]:
                    out["social_links"][net.split(".")[0]] = a["href"]
        all_text.append(_text(soup))

    text = " ".join(all_text)
    low = text.lower()

    years = [int(y) for y in COPYRIGHT_RE.findall(text) if 1990 <= int(y) <= now]
    out["copyright_year"] = max(years) if years else None
    since = [int(y) for y in SINCE_RE.findall(text) if 1800 <= int(y) <= now]
    out["since_year"] = min(since) if since else None

    out["family_phrases"] = [p for p in FAMILY_PHRASES if p in low][:4]
    out["acquisition_phrases"] = [label for pat, label in ACQUISITION_PATTERNS if re.search(pat, low)][:3]
    out["founder_mentions"] = _clean_names(FOUNDER_RE.findall(text))
    out["emails_on_site"] = list(dict.fromkeys(e.lower() for e in EMAIL_RE.findall(text)))[:5]
    out["phones_on_site"] = list(dict.fromkeys(PHONE_RE.findall(text)))[:3]
    out["tech_hints"] = sorted({v for k, v in TECH_HINTS.items() if k in all_html})
    out["text_excerpt"] = text[:3000]
    out["text_chars"] = len(text)
    out["html_chars"] = sum(len(h) for h in pages.values())
    return out


def is_thin(ex: dict[str, Any]) -> bool:
    """Big HTML but almost no readable text = a JavaScript-rendered site. We got the shell, not the content."""
    return ex.get("html_chars", 0) > 5_000 and ex.get("text_chars", 0) < 200
