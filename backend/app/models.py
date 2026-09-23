"""Database tables. JSON columns hold breakdowns/evidence so the UI can explain every number."""
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Dataset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    source: str = "upload"  # upload | demo_synthetic | demo_real
    created_at: datetime = Field(default_factory=utcnow)
    rows_in: int = 0
    rows_out: int = 0
    dup_clusters: int = 0
    rows_flagged: int = 0
    preset: str = "searcher"
    weights: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class RawLead(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    dataset_id: int = Field(index=True, foreign_key="dataset.id")
    row_index: int
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class Lead(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    dataset_id: int = Field(index=True, foreign_key="dataset.id")

    company: str = Field(index=True)
    domain: Optional[str] = Field(default=None, index=True)
    industry: Optional[str] = None
    category: Optional[str] = None
    business_type: Optional[str] = None
    employees: Optional[int] = None
    revenue_usd: Optional[int] = None
    year_founded: Optional[int] = None
    bbb_rating: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    owner_name: Optional[str] = None
    owner_title: Optional[str] = None
    parent_company: Optional[str] = None   # from SaaSquatch "Owner Details"
    ownership_type: Optional[str] = None   # e.g. "Privately Held Individual"
    source: Optional[str] = None

    merged_from: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    conflicts: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    flags: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    quality_score: int = 0
    fit_score: int = 0
    fit_grade: str = "D"
    fit_breakdown: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    exit_score: int = 0
    exit_breakdown: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    quadrant: str = "skip"  # call_first | nurture | enrich_later | skip

    web_intel: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    fetch_status: Optional[str] = None  # ok | no_site | timeout | blocked | error | fixture_missing
    intel_at: Optional[datetime] = None


class SiteCache(SQLModel, table=True):
    domain: str = Field(primary_key=True)
    fetched_at: datetime = Field(default_factory=utcnow)
    status: str
    extracted: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    llm: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    dataset_id: int = Field(index=True)
    kind: str
    status: str = "queued"  # queued | running | done | failed
    total: int = 0
    done: int = 0
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    finished_at: Optional[datetime] = None
