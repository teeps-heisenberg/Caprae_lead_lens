# LeadLens — a "Rank & Prioritize" module for SaaSquatch Leads

**Caprae Capital · Full Stack Developer pre-work · Abdullah Malik**

> SaaSquatch tells you *who exists*. LeadLens tells a searcher *who to call first* and *where to spend enrichment credits*.

- 🎬 Video walkthrough: `<video-url>`
- 💻 Runs locally in two commands (section 4). API docs at `http://localhost:8787/docs` once running. Hosting design and a 10-minute deploy runbook are in sections 3 and 5.
- 📓 Notebook: [`notebooks/walkthrough.ipynb`](notebooks/walkthrough.ipynb) runs the pipeline end to end on the bundled data.

---

## 1. The problem I chose

I studied the SaaSquatch Companies table (the screen every user lives in) and its demo. In one screen of 25 rows I saw:

| Seen in SaaSquatch | Why it hurts a searcher |
|---|---|
| Same company 3× (InfiVR) with conflicting fields | Two wasted enrichment credits, double outreach |
| Revenue "4" next to "$11.1M", employees "13.1" | Sorting and filters can't be trusted |
| BBB / Street / Business Type mostly N/A | Can't tell "unknown" from "bad" |
| 247 rows, no score, no ranking | Which 20 deserve a credit? Nobody knows |
| Email focus: Partnership / Collaboration / Networking / Sales | No *acquisition* angle, the core persona's use case |

Caprae's thesis is the $10T baby-boomer exit wave. The bottleneck for a searcher is not *how many rows* but *which owners are likely to sell*. No sourcing tool answers that. LeadLens does.

## 2. What LeadLens does

Upload a SaaSquatch Companies export (or load the bundled demo). Then:

1. **Clean.** Every field parsed and validated: `$11.1M` → `11100000`, `13.1` → `13` + flag, `N/A` → empty, emails syntax-checked, phones to E.164, states to codes. Bad values become `null` + a flag, never a guess. Each lead gets a **Data Quality** score.
2. **Dedupe.** Rows are blocked by domain or by name-prefix + city, compared with fuzzy matching (`InfiVR` ≈ `InfiVR Inc.` ≈ `Infi VR`), clustered, and merged. The most complete value wins per field; every conflict and every original row is kept and shown.
3. **Web Intel** (free, no credits). For chosen leads, the backend politely reads the company website (homepage, about, contact), the Wayback Machine and DNS. It extracts: footer © year, "since 1987", family-owned language, "a division of…", careers page presence, founder mentions, on-site email/phone, tech hints. Optionally **Gemini** turns the page text into structured judgements (owner-operated? independent? succession signals? an opening line for outreach). No key → the same JSON comes from rules.
4. **Score.** Two explainable scores, every point with a reason:
   - **Acquisition Fit** (rules only): revenue band, years in business, headcount band, B2B, industry stability, reachability, completeness.
   - **Exit-Readiness** (rules + optional 30 % AI blend): company age, owner-operated, family language, website staleness, independence, small stable team, succession-heavy trade.
   - Fit × Exit places every company in a quadrant: **Call first · Enrich later · Needs Web Intel · Nurture · Skip**. *Needs Web Intel* is for rows with too little data to judge (a raw scrape), so nothing is dismissed unread.
5. **Act.** Four pages behind one sidebar:
   - **Overview**: the funnel (rows in → unique → flagged → reachable → checked), the Fit × Exit chart, who to call first, and where 50 credits would go.
   - **Leads**: ranked table with quadrant tabs, filters, search, sort, column builder (show/hide, drag reorder, three saved views), one-click Web Intel on the top 25 or a selection, and a detail drawer that explains every point, shows the Web Intel evidence, the Gemini note and outreach line, data notes, and the original merged rows.
   - **Credits**: enter your SaaSquatch balance (or pick Free/Bronze/Silver/Gold) and get the exact unlock list, plus credits saved by dedupe and avoided on low value. Picks can be highlighted in Leads or exported.
   - **Datasets**: every upload with its cleaning stats; upload, demo loads, remove.
   - Exports: full CSV with scores and reasons, or the exact SaaSquatch *Import Leads* shape.

Two scoring presets ship: *Searcher / ETA buyer* and *B2B sales team*. Weights live in [`backend/score_config.json`](backend/score_config.json).

### Built for the export SaaSquatch actually produces
A raw scrape has only **Company, Industry, Street, City, State, BBB Rating, Company Phone, Website** (see [`data/saasquatch_scrape_shape.csv`](data/saasquatch_scrape_shape.csv)). Revenue, employees and year founded only appear after *Estimate Revenue* and *Enrich*. So:
- Fit is scored on the factors that **have** data and shows a **confidence %** (share of scoring weight that was known). Unknowns are never counted against a lead. Below 50 % confidence a lead is placed in **Needs Web Intel** rather than *Skip*: we don't dismiss what we haven't looked at.
- Web Intel **backfills** year founded, owner name, phone and email from the company's own website when the scrape lacks them, and re-scores. Free enrichment before any credit is spent.
- **Export → For SaaSquatch import** writes exactly the columns their *Import Leads* dialog accepts (Company, Industry, City, State, Business Phone, Website, Street, BBB Rating), so the Call-First shortlist goes straight back into SaaSquatch for paid enrichment. A clean round trip.
- All three SaaSquatch shapes are accepted: the raw scrape, the enriched export (camelCase headers such as `yearFounded`, `companyPhone`, `aiScore`), and the Leads History table with its six *Owner's …* columns (first + last name are combined; the owner's direct email/phone are used when the company inbox is empty).
- SaaSquatch's **Get Owner Details** table (Owner, Parent Company, Ownership Type, Confidence) is also accepted; when present, *Ownership Type* and *Parent Company* feed the Exit-Readiness factors directly, so their paid data and our free signals combine in one score.
- Paid enrichment can come back empty ("No Results Found … not in our sources"). Web Intel's free backfill from the company website is the fallback for exactly that case.
- SaaSquatch already has an **AI Scorer** (Insights Dashboard) and an **AI Scoring** toolbar button. On the Chicago Brass test it returned *"company data is not found in our sources"*: database-backed scoring fails for exactly the small, obscure, owner-operated firms a searcher wants. LeadLens scores from the company's **own website**, so it works where the database is empty (Chicago Brass: founding year recovered from the Wayback Machine, Exit-Readiness 15 → 47). It is proposed as a *Rank & Prioritize* tab beside *Companies*, not a competing product.

### The Credits page, in SaaSquatch's own currency
SaaSquatch sells credits: seeing a scraped company is free, unlocking its contact details (email, phone, LinkedIn) costs one credit (Free 5, Bronze 50, Silver 125, Gold 292 a month). LeadLens is not connected to the SaaSquatch account, so the user types their balance or picks a plan. The optimizer then ranks leads by quadrant then Fit × Exit, **skips leads that already have email and phone** (no credit needed) and skips the *Skip* quadrant, and returns the exact list to unlock. It also reports credits saved by dedupe and credits avoided on low-value rows.

## 3. Architecture

```
┌──────────────────┐   JSON    ┌──────────────────────────────┐   SQL    ┌───────────────────┐
│ React 18 + Vite  │ ────────▶ │ FastAPI (Python 3.12)        │ ───────▶ │ Postgres          │
│ TypeScript       │           │  pipeline/normalize.py       │          │  Supabase (prod)  │
│ Tailwind         │ ◀──────── │  pipeline/dedupe.py rapidfuzz│ ◀─────── │  SQLite (local)   │
│ TanStack Table   │           │  pipeline/fetcher.py httpx   │          └───────────────────┘
│ Recharts         │           │  pipeline/extract.py bs4     │              ▲ site_cache (7d)
│ Vercel (static)  │           │  pipeline/score.py           │              │
└──────────────────┘           │  llm/ gemini | rules fallback│ ─────────────┘
                               │  BackgroundTasks + job status│ ──▶ company sites · Wayback · DNS · Gemini
                               │  Render (Docker, Ubuntu)     │
                               └──────────────────────────────┘
```

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 18, Vite, TypeScript, Tailwind, TanStack Table, Recharts | Caprae's stack is React. Static build, no server. TanStack gives column visibility/order for free. |
| Frontend hosting | **Vercel** (static, CDN) | Zero server cost, git-push deploy. |
| Backend | **FastAPI**, pydantic v2, SQLModel, pandas, rapidfuzz, httpx, BeautifulSoup, phonenumbers, email-validator, dnspython | First backend in Caprae's job post. Typed; `/docs` is a free API demo. |
| Backend hosting | **Render** web service, Dockerfile (Ubuntu-based image) | Long-lived process for async Web Intel jobs; free tier. |
| Database | **Supabase Postgres** in prod, **SQLite** locally, one `DATABASE_URL` switch | Managed Postgres without ops; reviewers run locally with zero keys. |
| Caching | `site_cache` table (7-day TTL per domain) + `lru_cache` on score config | Re-checking a lead is instant; no site is hit twice in a week. Redis is the named scale-up path. |
| Jobs | FastAPI `BackgroundTasks`, bounded `asyncio.Semaphore`, job table polled by UI | Web Intel for 25 leads runs concurrently with visible progress. |
| AI | Gemini Flash (Google AI Studio free tier) behind a provider interface; rules fallback | Free for the reviewer; deterministic when no key. |

**Why not Supabase-only / serverless?** Fuzzy dedupe and site fetching are Python-shaped, long-running work; a container fits. Supabase is used for what it's best at: managed Postgres.

### Data model
`datasets` → `raw_leads` (untouched rows) → `leads` (cleaned, merged, scored; JSON columns hold breakdowns/evidence/conflicts) · `site_cache` · `jobs`.

### API (`/api/v1`, OpenAPI at `/docs`)
| Method | Path | What |
|---|---|---|
| POST | `/datasets/upload` · `/datasets/demo?which=synthetic\|real` | ingest → clean → dedupe → score |
| GET | `/datasets/{id}/stats` | funnel, quadrant/grade counts, chart points |
| GET | `/datasets/{id}/leads?quadrant&grade&state&industry&has_email&q&sort&page` | ranked, filtered leads |
| GET | `/leads/{id}` | full record + breakdowns + original rows |
| POST | `/datasets/{id}/intel` `{lead_ids | top_n}` → GET `/jobs/{id}` | Web Intel job + progress |
| POST | `/datasets/{id}/rescore` `{preset, weights?}` | switch preset / override weights |
| GET | `/datasets/{id}/optimize?credits=50` | Credit Optimizer |
| GET | `/datasets/{id}/export?ids=&quadrant=&format=full\|saasquatch` | CSV with scores and reasons, or the SaaSquatch Import Leads shape |

### Where each technical claim lives (for the Technicality rubric)

| Rubric phrase | What LeadLens does | File |
|---|---|---|
| Multiple sources | CSV export, company website (home/about/contact), Wayback Machine API, DNS MX, Gemini, SaaSquatch Owner Details export | `services/ingest.py`, `pipeline/fetcher.py`, `llm/gemini.py` |
| Data parsing | `$11.1M` / `850K` / `1.1 million` / `$1M–$5M` / `4` → integer or flag; `13.1` headcount; years; E.164 phones; RFC emails; state codes; HTML → text; © and "since" years by regex | `pipeline/normalize.py`, `pipeline/extract.py` |
| Performance at scale | pandas ingest; blocking before fuzzy matching (no O(n²)); async fetch with bounded concurrency; chunked background jobs with progress; 7-day site cache; paginated API; indexed columns | `pipeline/dedupe.py`, `services/webintel.py`, `models.py` |
| Complex web structures | BeautifulSoup + lxml; scripts/styles stripped; about/contact discovery; redirects; non-HTML and >500 KB rejected; encoding fallback; layout-independent regex extractors; JS-only shells detected as `thin` | `pipeline/fetcher.py`, `pipeline/extract.py` |
| Deduplication | domain + name-prefix/city blocking, rapidfuzz `token_set_ratio ≥ 90`, union-find clusters, trust-ordered merge, conflicts and original rows kept | `pipeline/dedupe.py` |
| Enrichment | Web Intel backfills year/owner/phone/email; Gemini structured judgements; Owner Details consumed into Exit score | `services/webintel.py`, `llm/`, `pipeline/score.py` |
| Validation | 20+ flags (invalid/suspect/mismatch/range/fractional), MX check, disposable/free-mail detection, Data Quality score, Fit confidence % | `pipeline/normalize.py`, `pipeline/score.py` |
| Changing websites | extractors are pattern-based, not CSS-selector-based, so layouts can change; every fetch outcome is classified (`ok/thin/no_site/timeout/blocked/error`) and never breaks the job; fixture sites give regression tests | `pipeline/fetcher.py`, `backend/fixtures/sites/` |
| CAPTCHAs / IP restrictions | 403/429/503 → `blocked`, one retry with back-off, then stop; robots.txt honoured; identifying User-Agent; per-host concurrency cap; cache prevents re-hits. We **detect and degrade, never bypass**: a blocked site is shown as blocked and scored from CSV signals. Proxy rotation and headless rendering are the documented next step, not hidden | `pipeline/fetcher.py` |
| Speed | 308-row export cleaned, deduped and scored in ~1 s; 30 fixture sites read and scored in ~1 s; live sites bounded by an 8 s timeout each, 6 in parallel | measured locally, see notebook |

### Design system (frontend)
- **Structure:** four pages behind a left sidebar (Overview, Leads, Credits, Datasets); bottom tab bar on phones. One drawer for company detail. No modals.
- **Color:** OKLCH tokens in `frontend/src/index.css`. Light surface, because a searcher uses this at a desk in daylight next to spreadsheets and a phone: pure white body, a faintly brand-tinted second neutral (hue 345) for the sidebar and toolbars, one deep magenta accent (`oklch(0.52 0.19 345)`) reserved for primary actions, the active page and the *Call first* state. Text steps are contrast-checked against white: ink ≈ 14:1, ink2 ≈ 8:1, ink3 ≈ 5.5:1. Quadrants are tinted chips (each text-on-tint pair clears 4.5:1); *Needs Web Intel* is drawn hollow so it never depends on hue alone. Strong scores read green, the one semantic use of color in numbers.
- **Type:** IBM Plex Sans, one family, fixed rem scale (12/13/14/16/20/24), weight for hierarchy. No uppercase micro-labels.
- **States:** every control has hover, focus-visible ring, disabled and loading; tables show skeletons while loading; empty states explain the next action; `prefers-reduced-motion` respected; z-index is a named scale.
- Checked with impeccable's anti-pattern detector (0 findings) and manually at 375, 768 and 1440 px.

## 4. Run it locally (no keys needed)

```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8787 --reload           # http://localhost:8787/docs
```
```bash
# frontend (new terminal)
cd frontend
npm install
npm run dev                                         # http://localhost:5173
```
Or one command: `docker compose up` → UI on http://localhost:5173, API on http://localhost:8787.

Then: **Load demo export** (landing page or the dataset menu in the top bar) → **Leads** → **Run Web Intel on top 25** → open *Granite Tool and Die*. For real websites, upload [`data/saasquatch_scrape_shape.csv`](data/saasquatch_scrape_shape.csv) (14 real Chicago companies) and run Web Intel again: those domains have no bundled sample, so they are fetched live and read by Gemini if a key is set.

Tests: `cd backend && pytest` (26 tests: normalize, dedupe, scoring, extraction, SaaSquatch export shapes).

Notebook (runs the same pipeline code step by step, no server needed):
```bash
cd backend
.venv/Scripts/python -m pip install -r ../notebooks/requirements.txt
.venv/Scripts/python -m ipykernel install --user --name leadlens --display-name "LeadLens (backend venv)"
.venv/Scripts/python -m jupyter notebook ../notebooks/walkthrough.ipynb     # pick the "LeadLens (backend venv)" kernel
```

### Configuration (`backend/.env`, see `.env.example`)
| Var | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./leadlens.db` | Supabase URI in prod |
| `ENRICH_MODE` | `auto` | `auto` = bundled sample site when one exists for the domain (the synthetic demo companies), otherwise the real website; `fixture` = samples only (tests); `live` = real web only |
| `LLM_PROVIDER` / `GEMINI_API_KEY` / `GEMINI_MODEL` | `none` / — / `gemini-2.5-flash` | set `gemini` + a Google AI Studio key for AI judgements; otherwise the rules provider produces the same fields |
| `CORS_ORIGINS` | localhost | add your Vercel URL |

## 5. Deploy (optional, ≈10 minutes)

The brief asks for the hosting design, not a live URL, so the submission runs locally. This is the path if one is wanted:

1. **Supabase** → New project → Settings → Database → copy the *pooled* connection URI.
2. **Render** → New Web Service → this repo → Root `backend` → Docker → env: `DATABASE_URL`, `CORS_ORIGINS=https://<your-vercel>.vercel.app`, optional `LLM_PROVIDER=gemini`, `GEMINI_API_KEY`. Tables are created on first boot.
3. **Vercel** → Import repo → Root `frontend` → Framework Vite → env `VITE_API_URL=https://<render-service>.onrender.com`.
4. Open the Vercel URL → Load demo → done.

## 6. Data

- [`data/saasquatch_sample.csv`](data/saasquatch_sample.csv) — **synthetic**, 308 rows, SaaSquatch's exact column names. Generated by [`scripts/make_dataset.py`](scripts/make_dataset.py) (seed 42). Mess is injected on purpose so the tool has to earn its keep: 22 exact + 26 near duplicates (incl. triple rows like the InfiVR case), revenue as `$4.2M` / `4,200,000` / `$1.1 million` / `4` / ranges, fractional and ranged headcounts, impossible years, malformed / free-mail / mismatched emails, N/A-heavy BBB and Street. Domains use the reserved `.example` TLD; **no real people**.
- `backend/fixtures/sites/` — 48 offline websites for those synthetic companies (legacy family firms, growth companies, acquired divisions, brochure sites, and a few deliberately unreachable). In the default `auto` mode Web Intel uses one of these whenever a company's domain has a bundled sample, and fetches the real website for everything else, so the demo and a real upload work in the same run. `ENRICH_MODE=fixture` forces samples only (tests).
- [`data/saasquatch_scrape_shape.csv`](data/saasquatch_scrape_shape.csv) — 14 real Chicago HVAC/plumbing companies, copied from a real SaaSquatch search result: the exact eight-column raw-scrape shape, public names and websites only. The best file for a live Web Intel run.
- [`data/saasquatch_enriched_shape.csv`](data/saasquatch_enriched_shape.csv) and [`data/saasquatch_owner_details_shape.csv`](data/saasquatch_owner_details_shape.csv) — one-row samples of SaaSquatch's enriched export (camelCase headers) and Owner Details export, used to verify header mapping.
- [`data/real_smb_sample.csv`](data/real_smb_sample.csv) — 20 real US businesses, **public company names and websites only**, everything else blank (they are larger than a typical search target; they're here to prove the fetcher, not the thesis).

### Ethical data collection
Only company websites and public archive/DNS data are read. `robots.txt` is honoured, requests carry an identifying User-Agent, concurrency is bounded, pages are capped at 500 KB, and results are cached so no site is fetched twice in 7 days. No LinkedIn scraping, no personal-data aggregation. Every AI field is labelled with its provider so nothing is silently hallucinated.

### What SaaSquatch already does per company, and where LeadLens is different
Each row in the Companies table has *View Details, Edit, Notes, News, Generate Insights, Favorite*. Those are **one-company-at-a-time** actions. LeadLens works on the **whole export at once**: 250 companies cleaned, deduped, checked and ranked in one pass, with every score explained. The analyst note in our drawer is a by-product of that batch run, not a replacement for *Generate Insights*.

## 7. What I deliberately did not build
Live scraping (SaaSquatch does it), auth/billing, LinkedIn automation, paid people-data APIs (Apollo/Hunter — the `LLMProvider`-style interface is where they'd plug in), lookalike search ("more like these 3"), HubSpot-native export. Listed as next steps, not missing work.

## 8. Time log (5-hour code box)
| Slot | Work |
|---|---|
| 0:00–0:20 | Scaffold (FastAPI, Vite, compose), dataset + sample-site generator |
| 0:20–1:00 | normalize (parsers, flags, three SaaSquatch header shapes), dedupe (blocking, fuzzy, merge with provenance), tests |
| 1:00–1:40 | fetcher (sample/live/auto, robots, cache, status classes, thin-page detection), extractors, Wayback, MX |
| 1:40–2:10 | Fit score with confidence, Exit-Readiness score, quadrants, presets; Owner Details fields into Exit |
| 2:10–2:30 | LLM layer: provider interface, Gemini adapter with explicit schema, rules fallback |
| 2:30–2:55 | models, API routes, background jobs, credit optimizer, two export formats |
| 2:55–4:15 | UI: sidebar and four pages, table with column builder, drawer with evidence, Web Intel job flow |
| 4:15–4:45 | Design system pass: OKLCH tokens, contrast, states, phone layout, anti-pattern check |
| 4:45–5:00 | Docker images, README, final test run |

Outside the box, as the brief allows: the video, the notebook, and the Business Understanding essays.

## 9. Repo map
```
backend/app/pipeline/   normalize.py dedupe.py fetcher.py extract.py score.py
backend/app/llm/        base.py (schema+prompt) gemini.py rules.py
backend/app/services/   ingest.py webintel.py optimizer.py export.py
backend/app/api/        routes.py
backend/tests/          26 unit tests
backend/fixtures/sites/ 48 bundled sample websites for the synthetic demo companies
frontend/src/           App.tsx (shell, pages, jobs)  components/ Sidebar, Overview, QuadrantChart, LeadTable,
                        LeadDrawer, Filters, ColumnBuilder, Optimizer (Credits page), Datasets, bits
frontend/src/index.css  design tokens (OKLCH) and component classes
scripts/make_dataset.py data/  notebooks/  DESIGN.md (original design, kept for the record)
```
