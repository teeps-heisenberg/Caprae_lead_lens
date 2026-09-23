from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import case, func
from sqlmodel import Session, col, select

from ..config import settings
from ..db import get_session
from ..llm import active_provider_name
from ..models import Dataset, Job, Lead, RawLead
from ..pipeline.score import load_config
from ..services.export import leads_to_csv, leads_to_saasquatch_csv
from ..services.ingest import ingest_dataframe, read_csv, rescore_dataset
from ..services.optimizer import optimize
from ..services.webintel import pick_top_n, run_web_intel

router = APIRouter(prefix="/api/v1")

QUADRANTS = ("call_first", "enrich_later", "unscored", "nurture", "skip")
SORTABLE = {"fit_score", "exit_score", "quality_score", "company", "revenue_usd", "employees", "year_founded", "state", "industry"}


# ---------- meta ----------

@router.get("/meta")
def meta() -> dict[str, Any]:
    cfg = load_config()
    return {
        "enrich_mode": settings.enrich_mode,
        "llm_provider": active_provider_name(),
        "presets": {k: {"label": v["label"], "description": v["description"], "fit": v["fit"], "exit": v["exit"]}
                    for k, v in cfg["presets"].items()},
        "thresholds": cfg["quadrant_thresholds"],
        "grades": cfg["grades"],
    }


# ---------- datasets ----------

def _dataset_or_404(session: Session, dataset_id: int) -> Dataset:
    ds = session.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")
    return ds


@router.get("/datasets")
def list_datasets(session: Session = Depends(get_session)) -> list[Dataset]:
    return list(session.exec(select(Dataset).order_by(col(Dataset.created_at).desc())).all())


@router.post("/datasets/upload")
async def upload_dataset(file: UploadFile, preset: str = "searcher", session: Session = Depends(get_session)) -> Dataset:
    data = await file.read()
    if len(data) > 15_000_000:
        raise HTTPException(413, "File too large (15MB max)")
    df = read_csv(data)
    return ingest_dataframe(session, df, name=file.filename or "upload.csv", source="upload", preset=preset)


@router.post("/datasets/demo")
def load_demo(which: str = "synthetic", preset: str = "searcher", session: Session = Depends(get_session)) -> Dataset:
    fname = {"synthetic": "saasquatch_sample.csv", "real": "real_smb_sample.csv"}.get(which)
    if not fname:
        raise HTTPException(400, "which must be synthetic or real")
    path = settings.data_dir / fname
    if not path.exists():
        raise HTTPException(404, f"Bundled dataset missing: {path.name}")
    df = read_csv(path.read_bytes())
    return ingest_dataframe(session, df, name=fname, source=f"demo_{which}", preset=preset)


@router.delete("/datasets/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: int, session: Session = Depends(get_session)) -> Response:
    ds = _dataset_or_404(session, dataset_id)
    for model in (Lead, RawLead, Job):
        for row in session.exec(select(model).where(model.dataset_id == dataset_id)).all():
            session.delete(row)
    session.delete(ds)
    session.commit()
    return Response(status_code=204)


@router.get("/datasets/{dataset_id}/stats")
def dataset_stats(dataset_id: int, session: Session = Depends(get_session)) -> dict[str, Any]:
    ds = _dataset_or_404(session, dataset_id)
    L = Lead
    base = select(L).where(L.dataset_id == dataset_id)

    def count(*conds) -> int:
        return session.exec(select(func.count()).select_from(L).where(L.dataset_id == dataset_id, *conds)).one()

    quadrants = {q: count(L.quadrant == q) for q in QUADRANTS}
    grades = {g: count(L.fit_grade == g) for g in "ABCD"}
    with_contact = count((L.email.is_not(None)) | (L.phone.is_not(None)))
    intel_done = count(L.intel_at.is_not(None))
    avg = session.exec(select(func.avg(L.fit_score), func.avg(L.exit_score), func.avg(L.quality_score)).where(L.dataset_id == dataset_id)).one()
    states = [s for s in session.exec(select(L.state).where(L.dataset_id == dataset_id, L.state.is_not(None)).distinct()).all()]
    industries = [s for s in session.exec(select(L.industry).where(L.dataset_id == dataset_id, L.industry.is_not(None)).distinct()).all()]
    points = session.exec(select(L.id, L.company, L.fit_score, L.exit_score, L.quadrant).where(L.dataset_id == dataset_id)).all()
    return {
        "dataset": ds,
        "funnel": {
            "rows_in": ds.rows_in, "rows_out": ds.rows_out, "duplicates_removed": ds.rows_in - ds.rows_out,
            "dup_clusters": ds.dup_clusters, "rows_flagged": ds.rows_flagged, "with_contact": with_contact,
            "intel_done": intel_done, "call_first": quadrants["call_first"],
        },
        "quadrants": quadrants,
        "grades": grades,
        "averages": {"fit": round(avg[0] or 0), "exit": round(avg[1] or 0), "quality": round(avg[2] or 0)},
        "filters": {"states": sorted(states), "industries": sorted(industries)},
        "points": [{"id": p[0], "company": p[1], "fit": p[2], "exit": p[3], "quadrant": p[4]} for p in points],
    }


@router.get("/datasets/{dataset_id}/leads")
def list_leads(
    dataset_id: int,
    quadrant: Optional[str] = None,
    grade: Optional[str] = None,
    min_fit: int = 0,
    min_exit: int = 0,
    state: Optional[str] = None,
    industry: Optional[str] = None,
    has_email: Optional[bool] = None,
    has_phone: Optional[bool] = None,
    intel: Optional[bool] = None,
    q: Optional[str] = None,
    sort: str = "priority",
    order: str = "desc",
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=500),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    _dataset_or_404(session, dataset_id)
    L = Lead
    conds = [L.dataset_id == dataset_id, L.fit_score >= min_fit, L.exit_score >= min_exit]
    if quadrant:
        conds.append(col(L.quadrant).in_([x for x in quadrant.split(",") if x in QUADRANTS]))
    if grade:
        conds.append(col(L.fit_grade).in_(list(grade.upper())))
    if state:
        conds.append(L.state == state.upper())
    if industry:
        conds.append(L.industry == industry)
    if has_email is not None:
        conds.append(L.email.is_not(None) if has_email else L.email.is_(None))
    if has_phone is not None:
        conds.append(L.phone.is_not(None) if has_phone else L.phone.is_(None))
    if intel is not None:
        conds.append(L.intel_at.is_not(None) if intel else L.intel_at.is_(None))
    if q:
        like = f"%{q.lower()}%"
        conds.append(func.lower(L.company).like(like) | func.lower(func.coalesce(L.city, "")).like(like)
                     | func.lower(func.coalesce(L.industry, "")).like(like) | func.lower(func.coalesce(L.owner_name, "")).like(like))

    total = session.exec(select(func.count()).select_from(L).where(*conds)).one()
    stmt = select(L).where(*conds)
    desc = order != "asc"
    if sort == "priority":
        rank = case((L.quadrant == "call_first", 4), (L.quadrant == "enrich_later", 3), (L.quadrant == "unscored", 2), (L.quadrant == "nurture", 1), else_=0)
        keys = (rank, col(L.fit_score), col(L.exit_score))
        stmt = stmt.order_by(*(k.desc() if desc else k.asc() for k in keys))
    elif sort in SORTABLE:
        c = col(getattr(L, sort))
        stmt = stmt.order_by(c.desc().nulls_last() if desc else c.asc().nulls_last())
    stmt = stmt.offset((page - 1) * size).limit(size)
    items = session.exec(stmt).all()
    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/leads/{lead_id}")
def get_lead(lead_id: int, session: Session = Depends(get_session)) -> dict[str, Any]:
    lead = session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    raws = session.exec(select(RawLead).where(col(RawLead.id).in_(lead.merged_from))).all() if lead.merged_from else []
    return {"lead": lead, "raw_rows": [{"id": r.id, "row_index": r.row_index, "payload": r.payload} for r in raws]}


# ---------- actions ----------

class IntelRequest(BaseModel):
    lead_ids: list[int] = Field(default_factory=list)
    top_n: int = Field(default=0, ge=0, le=200)


@router.post("/datasets/{dataset_id}/intel")
def start_intel(dataset_id: int, body: IntelRequest, bg: BackgroundTasks, session: Session = Depends(get_session)) -> Job:
    ds = _dataset_or_404(session, dataset_id)
    ids = list(body.lead_ids)
    if body.top_n:
        ids += [i for i in pick_top_n(session, dataset_id, body.top_n) if i not in ids]
    if not ids:
        raise HTTPException(400, "Nothing to check: pass lead_ids or top_n (leads need a website)")
    job = Job(dataset_id=dataset_id, kind="web_intel", total=len(ids))
    session.add(job)
    session.commit()
    session.refresh(job)
    bg.add_task(run_web_intel, job.id, ids, ds.preset, ds.weights or None)
    return job


@router.get("/jobs/{job_id}")
def get_job(job_id: int, session: Session = Depends(get_session)) -> Job:
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


class RescoreRequest(BaseModel):
    preset: str = "searcher"
    weights: Optional[dict[str, dict[str, int]]] = None


@router.post("/datasets/{dataset_id}/rescore")
def rescore(dataset_id: int, body: RescoreRequest, session: Session = Depends(get_session)) -> dict[str, Any]:
    ds = _dataset_or_404(session, dataset_id)
    if body.preset not in load_config()["presets"]:
        raise HTTPException(400, "Unknown preset")
    n = rescore_dataset(session, ds, body.preset, body.weights)
    return {"rescored": n, "preset": body.preset}


@router.get("/datasets/{dataset_id}/optimize")
def optimize_credits(dataset_id: int, credits: int = Query(50, ge=1, le=5000), session: Session = Depends(get_session)) -> dict[str, Any]:
    _dataset_or_404(session, dataset_id)
    leads = session.exec(select(Lead).where(Lead.dataset_id == dataset_id)).all()
    return optimize(list(leads), credits)


@router.get("/datasets/{dataset_id}/export")
def export(dataset_id: int, ids: Optional[str] = None, quadrant: Optional[str] = None, format: str = "full",
           session: Session = Depends(get_session)) -> Response:
    """format=full: every field, score and reason. format=saasquatch: the exact columns SaaSquatch's Import Leads accepts."""
    _dataset_or_404(session, dataset_id)
    stmt = select(Lead).where(Lead.dataset_id == dataset_id)
    if ids:
        stmt = stmt.where(col(Lead.id).in_([int(x) for x in ids.split(",") if x.strip().isdigit()]))
    if quadrant:
        stmt = stmt.where(col(Lead.quadrant).in_(quadrant.split(",")))
    leads = list(session.exec(stmt.order_by(col(Lead.fit_score).desc())).all())
    if format == "saasquatch":
        csv_text, name = leads_to_saasquatch_csv(leads), f"leadlens_for_saasquatch_import_{dataset_id}.csv"
    else:
        csv_text, name = leads_to_csv(leads), f"leadlens_dataset{dataset_id}.csv"
    return Response(csv_text, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}"'})
