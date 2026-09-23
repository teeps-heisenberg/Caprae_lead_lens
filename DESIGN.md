# SaaSquatch Lead Intelligence Layer — System Design (v2)

Author: Abdullah Malik. Working name: **LeadLens**.

A post-scrape, pre-outreach layer for SaaSquatch. It takes the raw Companies export, cleans and dedupes it, enriches it from free public sources, and ranks every company on two axes a searcher actually cares about: **is this a good business to buy** and **is this owner likely to sell**. Output: a "Call First" list, with evidence, that plugs into SaaSquatch's existing enrichment credits and email generator.

---

## 1. Positioning: what we build vs what SaaSquatch already has

We do **not** rebuild the scraper, the email generator, the map, or LinkedIn links. The assignment's "Quality First" path is "enhance a specific feature to improve performance, accuracy, or usability". The feature we enhance is the **Lead table**, the screen every user lives in, and we bolt an intelligence stage onto it.

```
SaaSquatch today:   Scrape ──▶ Lead table (247 unranked rows) ──▶ spend credit ──▶ email
LeadLens:           Scrape ──▶ Clean + Dedupe ──▶ Free enrich ──▶ Fit × Exit scoring ──▶ Call-First list ──▶ credit ──▶ email
```

Observed problems in their UI that this fixes:

| Seen in demo | Fix |
|---|---|
| InfiVR ×3, conflicting fields | fuzzy dedupe + merge with provenance |
| revenue "4", employees "13.1", N/A everywhere | validation, normalization, flags, quality score |
| 247 rows, no ranking | Fit score + Exit score + Call-First quadrant |
| 1 credit per enrichment, no guidance | Credit Optimizer: "spend 20 credits here" |
| Email focus lacks "Acquisition" | grounded outreach angle per lead for owner-to-buyer messaging |
| 15-column horizontal scroll | column builder, sticky key columns, saved views |

---

## 2. The differentiating feature: Exit-Readiness ("who is likely to sell")

Every sourcing tool answers *who exists*. None answer *who will pick up the phone about selling*. Caprae's entire thesis is the $10T baby-boomer exit wave, so this is the feature their persona is missing.

**Exit-Readiness score (0–100)**, built only from public, non-personal signals:

| Signal | Source | Points |
|---|---|---|
| Company age ≥ 20 yrs (≥ 15: partial) | CSV year founded, "since 19xx" on site, Wayback first snapshot | 20 |
| Owner-operated: title is Owner/Founder/President, or surname in company name | CSV owner fields, site "About" text | 15 |
| Family / founder language: "family owned", "second generation", "founded by" | site text | 10 |
| Website staleness: footer © year ≤ current−3, no blog/news since, no careers page | site fetch | 15 |
| Independent: no "a division of", "acquired by", "part of … group", no PE mention | site text | 15 |
| Small stable team: 5–75 employees, single location | CSV, site | 10 |
| Boomer-heavy trade: HVAC, plumbing, electrical, machining, distribution, accounting, dental, printing, landscaping, trucking | industry map | 15 |

Every signal produces an evidence string ("© 2019 in footer", "'family owned since 1987' on /about"). The drawer shows them so the user can trust or override.

**Fit score (0–100)**, "is it a business worth buying" (unchanged from v1): revenue band, years in business, employee band, B2B, industry stability, reachability, completeness. Two presets: *Searcher/ETA* and *Sales team*, weights editable in UI.

**Call-First quadrant** (the headline visual):

```
              high Exit
     NURTURE   │  CALL FIRST
  ─────────────┼─────────────  
     SKIP      │  ENRICH LATER
              low Exit
   low Fit            high Fit
```

**Credit Optimizer**: user enters their credit balance (e.g., 50). Tool returns the ordered list that maximizes expected reachable Call-First leads, and shows "credits saved by dedupe" and "credits avoided on D-grade". This speaks the product's own currency.

---

## 3. Enrichment: how it actually works

Three tiers, each free, each independently switchable. No paid people-data APIs are required; they plug in behind one interface.

### Tier 0 — Deterministic cleanup (always on, no network)
Parse revenue/employees/year, canonical domain, E.164 phone, email syntax + disposable check, state codes, null-ify N/A. Produces `flags[]` and `quality_score`.

### Tier 1 — Public web fetch (async, cached, polite)
For each company with a website:
- **Homepage + /about + /contact** via `httpx` async, 8s timeout, 3 concurrent per host, retries with backoff, honest User-Agent, robots.txt respected, HTML only, 500KB cap.
- **Extractors (regex/BeautifulSoup):** copyright year, "since 19xx / est. 19xx", family-owned phrases, "acquired by / division of", careers link present, team page headcount, phone/email on site, social links, meta description, tech hints (Shopify, WordPress, HubSpot).
- **Wayback Machine availability API** (free, no key): earliest snapshot year → company-age corroboration; latest snapshot → staleness.
- **DNS MX lookup** on email domain: does it accept mail at all.
- **Clearbit logo** (free, no key) for the UI only.
- Results cached in `enrichment_cache` (domain, fetched_at, payload) with 7-day TTL; re-runs are instant.
- Errors are data: `fetch_status` = ok / timeout / blocked / no_site, surfaced in UI. This is the honest answer to "adapting to changing websites, CAPTCHAs, IP restrictions": detect, back off, degrade gracefully, never block the pipeline.

### Tier 2 — LLM structuring (optional, key-gated, rule fallback)
Input: scraped text (trimmed to ~3k tokens) + CSV row. Output: strict JSON via schema:
```json
{"what_they_sell": "...", "business_model": "B2B|B2C|B2B2C",
 "owner_operated": {"value": true, "evidence": "..."},
 "succession_signals": ["..."], "independence": {"value": true, "evidence": "..."},
 "industry_normalized": "...", "outreach_angle": "one sentence a buyer could open with"}
```
- Provider-agnostic `LLMProvider` interface. Default adapter: **Gemini Flash via Google AI Studio free tier** (rate-limited, so enrichment runs on demand for selected rows or top-N, not the whole table). Second adapter: Claude (`claude-haiku-4-5` or `claude-sonnet-5`) for teams that already use Anthropic. Switch with `LLM_PROVIDER` + key env vars.
- **No key → rule-based fallback** fills the same JSON from the Tier 1 extractors. The demo never breaks for a reviewer.
- Every LLM field is stored with `source: "llm"` vs `"rules"` so nothing is silently hallucinated; the drawer labels them.
- **Gemini's role in scoring (decided 2026-09-21):** Fit score stays 100% rules (numeric bands, reproducible). Exit-Readiness = 70% rule signals + 30% Gemini's `ai_exit_assessment` (0–100 with reasoning) when a key is present; 100% rules otherwise. Gemini also writes the `analyst_note` and `outreach_angle` shown in the drawer.
- **Naming:** in the UI our free step is called **Web Intel**, never "enrichment", to avoid confusion with SaaSquatch's paid 1-credit contact enrichment.

### Pluggable paid providers (stubbed, not built)
`EnrichmentProvider` interface with `ApolloProvider`, `HunterProvider` stubs and a README note. Shows the architecture without spending 5 hours on API paperwork. SaaSquatch's own 1-credit enrichment is *the* paid provider in this story; we tell the user where to spend it.

### Ethics line (rubric "Other")
Only company websites and public archive/DNS data. No LinkedIn scraping, no personal-data aggregation, robots.txt honored, rate-limited, identifiable UA, cache to avoid re-hitting sites. Synthetic dataset carries no real people.

---

## 4. Demo data strategy (important: synthetic domains have no websites)

- `data/saasquatch_sample.csv` — ~300 synthetic rows with SaaSquatch's exact columns and injected mess (duplicates, "4", "13.1", bad emails, N/A). Domains like `northstar-hvac.example`.
- **Fixture web**: `backend/fixtures/sites/<domain>/index.html|about.html` for ~40 of those synthetic companies, written to exercise every extractor (old copyright year, "family owned since 1984", "acquired by X Group", missing careers page…). In `ENRICH_MODE=fixture` the fetcher serves these. Deterministic, offline, testable.
- `data/real_smb_sample.csv` — ~20 real US small businesses (names + public websites only, other fields blank) for a **live** enrichment demo in the video. `ENRICH_MODE=live`.
- README explains both modes plainly.

---

## 5. Architecture

```
┌──────────────────┐  JSON   ┌──────────────────────────┐  SQL   ┌───────────────────┐
│ React + Vite +TS │ ──────▶ │ FastAPI                  │ ─────▶ │ Postgres          │
│ Tailwind         │         │  pipeline/ normalize     │        │  Supabase (prod)  │
│ TanStack Table   │ ◀────── │            dedupe        │ ◀───── │  SQLite (local)   │
│ Recharts quadrant│         │            enrich (httpx)│        └───────────────────┘
│ Vercel (static)  │         │            score         │           ▲
└──────────────────┘         │  llm/ gemini | claude |  │           │ enrichment_cache
                             │       rules-fallback     │ ──────────┘
                             │  cache: TTL by (hash,cfg)│
                             │ Render (Docker, Ubuntu)  │ ──▶ public web, Wayback, DNS, LLM API
                             └──────────────────────────┘
```

| Layer | Choice | Reason to state on camera |
|---|---|---|
| Frontend | React 18, Vite, TypeScript, Tailwind, TanStack Table, Recharts | Their stack; static build; table features free |
| FE hosting | Vercel | CDN-served static assets, zero server, git-push deploy |
| Backend | FastAPI, pydantic v2, SQLModel, httpx, BeautifulSoup, rapidfuzz, pandas | Their first-listed backend; async fetch; typed API; OpenAPI docs = API demo |
| BE hosting | Render web service (Dockerfile, Ubuntu base) | Long-lived process for async enrichment; free tier |
| DB | Supabase Postgres (prod) / SQLite (local) via `DATABASE_URL` | Managed Postgres, zero-key local run |
| Cache | In-process TTL for scored views; `enrichment_cache` table for fetched sites | Cheap now; Redis named as scale path |
| Jobs | FastAPI `BackgroundTasks` + job status endpoint | Enrichment of 25 rows runs async; UI polls |
| LLM | Gemini Flash (free tier) default; Claude adapter; rules fallback | Free for reviewer; provider-agnostic |

---

## 6. Data model

```
datasets          id, name, mode, uploaded_at, rows_in, rows_out, dup_clusters, config jsonb
raw_leads         id, dataset_id, row_index, payload jsonb
leads             id, dataset_id, company, domain, industry, category, business_type,
                  employees, revenue_usd, year_founded, bbb_rating, street, city, state,
                  website, linkedin, email, phone, owner_name, owner_title,
                  merged_from int[], conflicts jsonb, flags text[],
                  quality_score, fit_score, fit_grade, fit_breakdown jsonb,
                  exit_score, exit_evidence jsonb, quadrant,
                  enrichment jsonb, enriched_at, fetch_status
enrichment_cache  domain PK, fetched_at, html_meta jsonb, extracted jsonb, llm jsonb
jobs              id, dataset_id, kind, status, progress, error
```

---

## 7. API (`/api/v1`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/datasets/upload` | CSV → Tier 0 + dedupe + score → summary |
| POST | `/datasets/demo?which=synthetic\|real` | load bundled dataset |
| GET | `/datasets/{id}/stats` | funnel + quadrant counts + credits saved |
| GET | `/datasets/{id}/leads` | filters: quadrant, grade, min_fit, min_exit, state, industry, has_email, q; sort; page |
| GET | `/leads/{id}` | full record, breakdowns, evidence, merged sources, raw diff |
| POST | `/datasets/{id}/enrich` | body: lead_ids or top_n → background job |
| GET | `/jobs/{id}` | progress |
| POST | `/datasets/{id}/rescore` | weights → recompute (cached) |
| GET | `/datasets/{id}/optimize?credits=50` | Credit Optimizer list |
| GET | `/datasets/{id}/export?format=csv\|hubspot&ids=` | export |
| GET | `/health` | Render check |

---

## 8. Frontend (single page, four zones)

1. **Header strip**: dataset selector / upload, ENRICH MODE badge, KPI cards: rows in → after dedupe → with valid contact → Call-First count → credits saved.
2. **Quadrant chart** (Recharts scatter, Fit × Exit, colored by quadrant, click a dot → row highlights). Toggle to hide.
3. **Ranked table** (TanStack): default sort by Call-First then Fit. Columns: Quadrant chip, Fit bar, Exit bar, Company (+logo), Revenue, Employees, Founded, Location, Industry, Reachability icons, Quality, Enriched ✓. Sticky first 3 columns. Row → **drawer**: score breakdowns with evidence, flags, enrichment JSON (labelled llm/rules), merged sources, raw vs clean diff, outreach angle with copy button.
4. **Toolbar**: filters (quadrant, grade, revenue slider, state, industry, has email/phone), **Enrich selected / Enrich top 25**, **Credit Optimizer** (input credits → highlights rows), **Column Builder** (visibility, drag reorder, presets Searcher/Sales, save view to localStorage), Export CSV / HubSpot CSV.

Theme: SaaSquatch dark navy, teal→blue gradient for primary actions, grade colors green/teal/amber/slate. Designed empty, loading, error and "enrichment blocked" states.

---

## 9. Build plan — 5-hour code box

| Slot | Work |
|---|---|
| 0:00–0:20 | Scaffold FE/BE, docker-compose, dataset generator + fixture sites generator |
| 0:20–1:05 | normalize, dedupe, fit score, tests |
| 1:05–1:50 | fetcher (httpx, robots, cache, fixture mode), extractors, Wayback, MX, exit score, tests |
| 1:50–2:15 | LLM layer: provider interface, Gemini adapter, Claude adapter, rules fallback, JSON schema |
| 2:15–2:40 | models, endpoints, background jobs, TTL cache |
| 2:40–4:00 | UI: KPI strip, quadrant, table, drawer, enrich flow with progress |
| 4:00–4:30 | Credit Optimizer, column builder, exports |
| 4:30–5:00 | polish states, deploy (Supabase → Render → Vercel), README |

Outside the box (allowed): video, essays, optional notebook `notebooks/walkthrough.ipynb` running the pipeline on the CSV.

Stretch if time remains: **Lookalike** ("star 3 companies → find similar" via TF-IDF cosine on industry/category/description).

---

## 10. Deployment runbook

1. Supabase: new project → Settings → Database → pooled URI → `DATABASE_URL`.
2. Render: New Web Service → repo → root `backend/` → Dockerfile → env `DATABASE_URL`, `CORS_ORIGINS`, `ENRICH_MODE=live`, optional `LLM_PROVIDER=gemini`, `GEMINI_API_KEY` → deploy.
3. Vercel: import → root `frontend/` → env `VITE_API_URL` → deploy.
4. Smoke: open Vercel → Load demo → Enrich top 25 → quadrant fills.
Local: `docker compose up` (SQLite, fixture mode, no keys) or `uvicorn` + `npm run dev`.

---

## 11. Rubric mapping

| Bucket | Evidence |
|---|---|
| Business (10) | Exit-Readiness encodes the boomer-exit thesis; Call-First quadrant; Credit Optimizer in SaaSquatch's own currency; Acquisition outreach angle; HubSpot export |
| UX/UI (10) | Ranked table, evidence drawer, one-click enrich with progress, column builder + saved views, guided empty states |
| Technicality (10) | Multi-source extraction (site, Wayback, DNS, LLM), async polite fetcher with backoff and status, fuzzy dedupe with provenance, validation flags, configurable scoring, cache, tests, OpenAPI |
| Design (5) | SaaSquatch-matched theme, quadrant visual, score bars, logos, sticky columns |
| Other (5) | Ethical scraping policy, synthetic + fixture data, provider-agnostic LLM, notebook, honest time log |

---

## 12. Video script (≤ 2:00)

0:00 Their table: InfiVR ×3, revenue "4", 247 unranked rows. "A searcher can't tell who to call." (20s)
0:20 LeadLens: clean → dedupe → free enrichment → Fit × Exit → Call-First. (15s)
0:35 Demo: load export → KPIs → Enrich top 25 → quadrant fills → open a Call-First lead → evidence: "family owned since 1987", "© 2019", owner title → outreach angle → Credit Optimizer → export. (55s)
1:30 Architecture: React/Vercel static, FastAPI/Render, Supabase Postgres, async fetch cache, Gemini or Claude with rules fallback. (20s)
1:50 "Searchers pick the 20 owners most likely to sell, spend credits only there, and open with a grounded message." (10s)
