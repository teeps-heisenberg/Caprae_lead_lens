import utils.session
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import settings
from .db import init_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="LeadLens API",
    version="0.1.0",
    description="Post-scrape intelligence for SaaSquatch exports: clean, dedupe, Web Intel, Fit × Exit-Readiness scoring, Credit Optimizer.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list or ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "enrich_mode": settings.enrich_mode, "llm_provider": settings.llm_provider}
