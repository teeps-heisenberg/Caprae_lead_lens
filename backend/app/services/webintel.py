"""Web Intel job: fetch -> extract -> LLM/rules -> cache -> re-score Exit-Readiness.

Network work runs concurrently (bounded); DB writes happen per chunk so job progress is visible.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from sqlmodel import Session, select

from ..config import settings
from ..db import engine
from ..llm import get_provider
from ..models import Job, Lead, SiteCache, utcnow
from ..pipeline.extract import extract, is_thin
from ..pipeline.fetcher import fetch_site
from ..pipeline.score import exit_score, fit_confidence, fit_score, quadrant_for


def backfill_from_site(lead: Lead, ex: dict[str, Any]) -> list[str]:
    """Free enrichment: fill fields the scrape did not have from what the website says. Returns added flags."""
    added: list[str] = []
    if not lead.year_founded and (ex.get("since_year") or ex.get("wayback_first_year")):
        lead.year_founded = int(ex.get("since_year") or ex["wayback_first_year"])
        added.append("year_from_website" if ex.get("since_year") else "year_from_wayback")
    if not lead.owner_name and ex.get("founder_mentions"):
        lead.owner_name = ex["founder_mentions"][0]
        added.append("owner_from_website")
    if not lead.phone and ex.get("phones_on_site"):
        from ..pipeline.normalize import normalize_phone

        p, _ = normalize_phone(ex["phones_on_site"][0])
        if p:
            lead.phone = p
            added.append("phone_from_website")
    if not lead.email and ex.get("emails_on_site"):
        from ..pipeline.normalize import normalize_email

        e, fl = normalize_email(ex["emails_on_site"][0], lead.domain)
        if e and "email_freemail" not in fl:
            lead.email = e
            added.append("email_from_website")
    return added

log = logging.getLogger(__name__)


async def _intel_for(lead: dict[str, Any], cached: SiteCache | None) -> tuple[str, dict[str, Any], dict[str, Any] | None, bool]:
    """Returns (status, extracted, llm, from_cache)."""
    domain = lead.get("domain")
    if cached and cached.fetched_at.replace(tzinfo=None) > (utcnow() - timedelta(days=settings.cache_ttl_days)).replace(tzinfo=None):
        return cached.status, cached.extracted, cached.llm, True

    res = await fetch_site(domain)
    extracted = extract(res.pages) if res.pages else {}
    status = res.status
    if res.pages:
        extracted.update(wayback_first_year=res.wayback_first_year, wayback_last_year=res.wayback_last_year, mx_ok=res.mx_ok)
        if is_thin(extracted):
            status = "thin"  # JS-rendered shell: keep Wayback/DNS facts, but do not ask the LLM to judge an empty page
    llm = None
    if extracted and status == "ok":
        llm = await get_provider().analyze(lead, extracted)
        if llm is None and get_provider().name != "rules":
            from ..llm.rules import RulesProvider

            llm = await RulesProvider().analyze(lead, extracted)
            if llm:
                llm["_provider"] = "rules (fallback)"
        elif llm:
            llm["_provider"] = get_provider().name
    return status, extracted, llm, False


async def run_web_intel(job_id: int, lead_ids: list[int], preset: str, override: dict | None) -> None:
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if not job:
            return
        job.status, job.total = "running", len(lead_ids)
        s.add(job)
        s.commit()

    sem = asyncio.Semaphore(settings.fetch_concurrency)
    chunk = max(1, settings.fetch_concurrency)

    async def one(lead_id: int) -> tuple[int, str, dict, dict | None, bool]:
        async with sem:
            with Session(engine) as s:
                lead = s.get(Lead, lead_id)
                if not lead:
                    return lead_id, "error", {}, None, False
                d = lead.model_dump()
                cached = s.get(SiteCache, lead.domain) if lead.domain else None
                cached_copy = SiteCache(**cached.model_dump()) if cached else None
            try:
                status, ex, llm, from_cache = await _intel_for(d, cached_copy)
            except Exception as e:  # never let one lead kill the job
                log.exception("intel failed for lead %s", lead_id)
                status, ex, llm, from_cache = "error", {}, None, False
            return lead_id, status, ex, llm, from_cache

    try:
        for start in range(0, len(lead_ids), chunk):
            results = await asyncio.gather(*(one(i) for i in lead_ids[start:start + chunk]))
            with Session(engine) as s:
                for lead_id, status, ex, llm, from_cache in results:
                    lead = s.get(Lead, lead_id)
                    if not lead:
                        continue
                    intel = {"extracted": ex, "llm": llm, "status": status, "from_cache": from_cache,
                             "mode": settings.enrich_mode}
                    lead.web_intel = intel
                    lead.fetch_status = status
                    lead.intel_at = utcnow()
                    if status == "ok" and ex:
                        added = backfill_from_site(lead, ex)
                        if added:
                            lead.flags = sorted(set(lead.flags) | set(added))
                            fs, grade, fb = fit_score(lead.model_dump(), preset, override)
                            lead.fit_score, lead.fit_grade, lead.fit_breakdown = fs, grade, fb
                    es, eb = exit_score(lead.model_dump(), intel, preset, override)
                    lead.exit_score, lead.exit_breakdown = es, eb
                    # once the website has been read, we know enough to place the lead even if the CSV was thin
                    conf = max(fit_confidence(lead.fit_breakdown), 50 if status == "ok" else 0)
                    lead.quadrant = quadrant_for(lead.fit_score, es, conf)
                    s.add(lead)
                    if lead.domain and not from_cache and status in ("ok", "thin", "no_site", "blocked", "timeout"):
                        s.merge(SiteCache(domain=lead.domain, fetched_at=utcnow(), status=status, extracted=ex, llm=llm))
                job = s.get(Job, job_id)
                job.done = min(job.total, job.done + len(results))
                s.add(job)
                s.commit()
        with Session(engine) as s:
            job = s.get(Job, job_id)
            job.status, job.finished_at = "done", utcnow()
            s.add(job)
            s.commit()
    except Exception as e:
        log.exception("web intel job %s failed", job_id)
        with Session(engine) as s:
            job = s.get(Job, job_id)
            job.status, job.error, job.finished_at = "failed", str(e)[:400], utcnow()
            s.add(job)
            s.commit()


def pick_top_n(session: Session, dataset_id: int, n: int) -> list[int]:
    """Leads most worth checking: not yet checked, has a website, best Fit first."""
    q = (
        select(Lead.id)
        .where(Lead.dataset_id == dataset_id, Lead.intel_at.is_(None), Lead.domain.is_not(None))
        .order_by(Lead.fit_score.desc(), Lead.exit_score.desc())
        .limit(n)
    )
    return list(session.exec(q).all())
