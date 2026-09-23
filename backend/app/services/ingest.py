"""CSV -> raw rows -> clean rows -> merged leads -> scored leads, persisted."""
from __future__ import annotations

import io
from typing import Any

import pandas as pd
from fastapi import HTTPException
from sqlmodel import Session, select

from ..models import Dataset, Lead, RawLead
from ..pipeline.dedupe import find_clusters, merge_cluster
from ..pipeline.normalize import map_columns, normalize_row, quality_score
from ..pipeline.score import exit_score, fit_confidence, fit_score, quadrant_for

LEAD_FIELDS = [
    "company", "domain", "industry", "category", "business_type", "employees", "year_founded",
    "bbb_rating", "street", "city", "state", "website", "linkedin", "email", "phone",
    "owner_name", "owner_title", "parent_company", "ownership_type", "source",
]


def read_csv(data: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except Exception:
        try:
            df = pd.read_excel(io.BytesIO(data), dtype=str)
        except Exception as e:
            raise HTTPException(400, f"Could not parse file as CSV/Excel: {e}") from e
    if df.empty:
        raise HTTPException(400, "File has no rows")
    df.columns = [str(c).strip() for c in df.columns]
    return df.fillna("")


def score_lead_dict(lead: dict[str, Any], preset: str, override: dict | None = None) -> None:
    fs, grade, fb = fit_score(lead, preset, override)
    es, eb = exit_score(lead, lead.get("web_intel"), preset, override)
    lead.update(fit_score=fs, fit_grade=grade, fit_breakdown=fb, exit_score=es, exit_breakdown=eb,
                quadrant=quadrant_for(fs, es, fit_confidence(fb)))


def ingest_dataframe(session: Session, df: pd.DataFrame, name: str, source: str, preset: str = "searcher") -> Dataset:
    colmap = map_columns(list(df.columns))
    if "company" not in colmap.values():
        raise HTTPException(400, f"No company-name column recognised. Headers: {list(df.columns)[:12]}")

    ds = Dataset(name=name, source=source, preset=preset, rows_in=len(df))
    session.add(ds)
    session.flush()

    clean_rows: list[dict[str, Any]] = []
    flag_rows: list[list[str]] = []
    raw_ids: list[int] = []
    for i, rec in enumerate(df.to_dict(orient="records")):
        raw = RawLead(dataset_id=ds.id, row_index=i, payload=rec)
        session.add(raw)
        session.flush()
        raw_ids.append(raw.id)
        clean, flags = normalize_row(rec, colmap)
        clean_rows.append(clean)
        flag_rows.append(flags)

    clusters = find_clusters(clean_rows)
    n_flagged = 0
    for idxs in clusters:
        merged, flags, conflicts = merge_cluster(clean_rows, flag_rows, idxs, raw_ids)
        merged["revenue_usd"] = merged.pop("revenue", None)
        merged["quality_score"] = quality_score({**merged, "revenue": merged["revenue_usd"]}, flags)
        merged["web_intel"] = None
        score_lead_dict(merged, preset)
        if any(not f.startswith("merged") for f in flags):
            n_flagged += 1
        lead = Lead(
            dataset_id=ds.id,
            **{f: merged.get(f) for f in LEAD_FIELDS},
            revenue_usd=merged["revenue_usd"],
            merged_from=[raw_ids[i] for i in idxs],
            conflicts=conflicts,
            flags=flags,
            quality_score=merged["quality_score"],
            fit_score=merged["fit_score"], fit_grade=merged["fit_grade"], fit_breakdown=merged["fit_breakdown"],
            exit_score=merged["exit_score"], exit_breakdown=merged["exit_breakdown"], quadrant=merged["quadrant"],
        )
        session.add(lead)

    ds.rows_out = len(clusters)
    ds.dup_clusters = sum(1 for c in clusters if len(c) > 1)
    ds.rows_flagged = n_flagged
    session.commit()
    session.refresh(ds)
    return ds


def rescore_dataset(session: Session, ds: Dataset, preset: str, override: dict | None) -> int:
    leads = session.exec(select(Lead).where(Lead.dataset_id == ds.id)).all()
    for lead in leads:
        d = lead.model_dump()
        score_lead_dict(d, preset, override)
        lead.fit_score, lead.fit_grade, lead.fit_breakdown = d["fit_score"], d["fit_grade"], d["fit_breakdown"]
        lead.exit_score, lead.exit_breakdown, lead.quadrant = d["exit_score"], d["exit_breakdown"], d["quadrant"]
        session.add(lead)
    ds.preset = preset
    ds.weights = override or {}
    session.add(ds)
    session.commit()
    return len(leads)
