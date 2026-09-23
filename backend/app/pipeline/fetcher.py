"""Polite async site fetcher with a fixture mode for offline, deterministic demos and tests.

Live mode: robots.txt honoured, honest User-Agent, 8s timeout, one retry with backoff,
500KB cap, at most homepage + 2 discovered pages (about/contact). Failures are classified,
never raised: ok | no_site | timeout | blocked | error | fixture_missing.
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from ..config import settings

USER_AGENT = "LeadLensBot/0.1 (+https://github.com/abdullah-malik/leadlens; research tool; contact via repo)"
MAX_BYTES = 500_000
SUBPAGE_HINTS = ("about", "company", "our-story", "history", "team", "contact")


@dataclass
class FetchResult:
    status: str
    pages: dict[str, str] = field(default_factory=dict)
    wayback_first_year: int | None = None
    wayback_last_year: int | None = None
    mx_ok: bool | None = None
    note: str | None = None


# ---------- fixture mode ----------

def _fixture_dir(domain: str) -> Path:
    return settings.fixtures_dir / domain


def fetch_fixture(domain: str) -> FetchResult:
    d = _fixture_dir(domain)
    if not d.exists():
        return FetchResult(status="fixture_missing", note="No bundled fixture for this domain")
    pages: dict[str, str] = {}
    for name in ("index.html", "about.html", "contact.html"):
        p = d / name
        if p.exists():
            pages["/" if name == "index.html" else f"/{name[:-5]}"] = p.read_text(encoding="utf-8")
    meta: dict[str, Any] = {}
    mp = d / "meta.json"
    if mp.exists():
        meta = json.loads(mp.read_text(encoding="utf-8"))
    if meta.get("status") and meta["status"] != "ok":
        return FetchResult(status=meta["status"], note=meta.get("note"))
    return FetchResult(
        status="ok", pages=pages,
        wayback_first_year=meta.get("wayback_first_year"), wayback_last_year=meta.get("wayback_last_year"),
        mx_ok=meta.get("mx_ok"),
    )


# ---------- live mode ----------

async def _robots_allows(client: httpx.AsyncClient, base: str) -> bool:
    try:
        r = await client.get(urljoin(base, "/robots.txt"), timeout=4.0)
        if r.status_code != 200:
            return True
        rp = RobotFileParser()
        rp.parse(r.text.splitlines())
        return rp.can_fetch(USER_AGENT, base)
    except Exception:
        return True


async def _get(client: httpx.AsyncClient, url: str) -> tuple[str | None, str]:
    for attempt in range(2):
        try:
            async with client.stream("GET", url) as r:
                if r.status_code in (403, 429, 503):
                    return None, "blocked"
                if r.status_code >= 400:
                    return None, "error"
                ctype = r.headers.get("content-type", "")
                if "html" not in ctype and "text" not in ctype:
                    return None, "error"
                buf = b""
                async for chunk in r.aiter_bytes():
                    buf += chunk
                    if len(buf) > MAX_BYTES:
                        break
                return buf.decode(r.encoding or "utf-8", errors="replace"), "ok"
        except httpx.TimeoutException:
            if attempt == 1:
                return None, "timeout"
            await asyncio.sleep(1.5)
        except httpx.HTTPError:
            return None, "no_site"
    return None, "error"


async def _wayback(client: httpx.AsyncClient, domain: str) -> tuple[int | None, int | None]:
    first = last = None
    try:
        r = await client.get("https://archive.org/wayback/available", params={"url": domain, "timestamp": "19960101"}, timeout=6.0)
        ts = (r.json().get("archived_snapshots") or {}).get("closest", {}).get("timestamp")
        first = int(ts[:4]) if ts else None
        r = await client.get("https://archive.org/wayback/available", params={"url": domain}, timeout=6.0)
        ts = (r.json().get("archived_snapshots") or {}).get("closest", {}).get("timestamp")
        last = int(ts[:4]) if ts else None
    except Exception:
        pass
    return first, last


def _mx_ok(domain: str) -> bool | None:
    try:
        import dns.resolver

        dns.resolver.resolve(domain, "MX", lifetime=4.0)
        return True
    except Exception as e:  # NXDOMAIN, NoAnswer, timeout...
        return False if e.__class__.__name__ in ("NXDOMAIN", "NoAnswer", "NoNameservers") else None


async def fetch_live(domain: str) -> FetchResult:
    base = f"https://{domain}/"
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=settings.fetch_timeout_s) as client:
        if not await _robots_allows(client, base):
            return FetchResult(status="blocked", note="robots.txt disallows")
        html, st = await _get(client, base)
        if html is None and st == "no_site":
            html, st = await _get(client, f"http://{domain}/")
        if html is None:
            return FetchResult(status=st)
        pages = {"/": html}
        links = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.I)
        picked: list[str] = []
        for href in links:
            path = urlparse(urljoin(base, href)).path.lower()
            if urlparse(urljoin(base, href)).netloc.replace("www.", "") != domain:
                continue
            if any(h in path for h in SUBPAGE_HINTS) and path not in picked and path != "/":
                picked.append(path)
            if len(picked) == 2:
                break
        for path in picked:
            sub, st2 = await _get(client, urljoin(base, path))
            if sub:
                pages[path] = sub
        first, last = await _wayback(client, domain)
    mx = await asyncio.to_thread(_mx_ok, domain)
    return FetchResult(status="ok", pages=pages, wayback_first_year=first, wayback_last_year=last, mx_ok=mx)


async def fetch_site(domain: str | None) -> FetchResult:
    if not domain:
        return FetchResult(status="no_site", note="No website on record")
    if settings.enrich_mode == "fixture":
        return fetch_fixture(domain)
    if settings.enrich_mode == "auto" and _fixture_dir(domain).exists():
        return fetch_fixture(domain)
    return await fetch_live(domain)
