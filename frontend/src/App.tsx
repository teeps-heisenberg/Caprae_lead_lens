import clsx from "clsx";
import { ChevronDown, ChevronLeft, ChevronRight, Database, Download, FileUp, Radar, Upload, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { ColumnBuilder, VIEW_PRESETS } from "./components/ColumnBuilder";
import { Datasets } from "./components/Datasets";
import { Filters } from "./components/Filters";
import { LeadDrawer } from "./components/LeadDrawer";
import { COLUMNS, LeadTable } from "./components/LeadTable";
import { Optimizer } from "./components/Optimizer";
import { Overview } from "./components/Overview";
import { MobileNav, Sidebar, type View } from "./components/Sidebar";
import { PageHeader, Popover, Spinner } from "./components/bits";
import { useLocalStorage } from "./hooks/useLocalStorage";
import type { Dataset, Job, Lead, LeadFilters, Meta, Stats } from "./types";
import { EMPTY_FILTERS } from "./types";

const PAGE_SIZE = 25;

export default function App() {
  const [view, setView] = useLocalStorage<View>("ll.view", "overview");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetId, setDatasetId] = useLocalStorage<number | null>("ll.dataset", null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [leads, setLeads] = useState<{ total: number; items: Lead[] }>({ total: 0, items: [] });
  const [filters, setFilters] = useState<LeadFilters>(EMPTY_FILTERS);
  const [sort, setSort] = useState<{ id: string; desc: boolean }>({ id: "priority", desc: true });
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [drawer, setDrawer] = useState<number | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [highlight, setHighlight] = useState<Set<number> | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [order, setOrder] = useLocalStorage<string[]>("ll.cols.order", COLUMNS.map((c) => c.id));
  const [visible, setVisible] = useLocalStorage<Record<string, boolean>>("ll.cols.visible", Object.fromEntries(COLUMNS.map((c) => [c.id, VIEW_PRESETS.searcher.visible.includes(c.id) || !!c.locked])));
  const fileRef = useRef<HTMLInputElement>(null);
  const apiDown = meta === null && datasets.length === 0;

  const notify = (kind: "ok" | "err", text: string) => { setToast({ kind, text }); setTimeout(() => setToast(null), 4500); };

  const refreshDatasets = useCallback(async () => {
    const ds = await api.datasets(); setDatasets(ds);
    if (!datasetId || !ds.some((d) => d.id === datasetId)) setDatasetId(ds[0]?.id ?? null);
    return ds;
  }, [datasetId, setDatasetId]);

  useEffect(() => { api.meta().then(setMeta).catch(() => setMeta(null)); refreshDatasets().catch(() => notify("err", "API not reachable. Start the backend on port 8787, then reload.")); }, []);

  const refreshStats = useCallback(async () => { if (datasetId) setStats(await api.stats(datasetId)); }, [datasetId]);
  const refreshLeads = useCallback(async () => {
    if (!datasetId) { setLeads({ total: 0, items: [] }); return; }
    setLoading(true);
    try { setLeads(await api.leads(datasetId, filters, sort.id, sort.desc ? "desc" : "asc", page, PAGE_SIZE)); } finally { setLoading(false); }
  }, [datasetId, filters, sort, page]);

  useEffect(() => { setPage(1); setSelected(new Set()); }, [datasetId, filters, sort]);
  useEffect(() => { setHighlight(null); }, [datasetId]);
  useEffect(() => { refreshStats().catch(() => setStats(null)); }, [refreshStats]);
  useEffect(() => {
    const t = setTimeout(() => refreshLeads().catch((e) => { if (!/not found/i.test(String(e.message))) notify("err", String(e.message)); }), filters.q ? 250 : 0);
    return () => clearTimeout(t);
  }, [refreshLeads]);

  useEffect(() => {
    if (!job || job.status === "done" || job.status === "failed") return;
    const t = setInterval(async () => {
      const j = await api.job(job.id); setJob(j);
      if (j.status === "done" || j.status === "failed") { clearInterval(t); await Promise.all([refreshStats(), refreshLeads()]); notify(j.status === "done" ? "ok" : "err", j.status === "done" ? `Web Intel finished for ${j.done} companies` : `Web Intel failed: ${j.error}`); }
    }, 800);
    return () => clearInterval(t);
  }, [job?.id, job?.status]);

  const loadDemo = async (which: "synthetic" | "real") => {
    setBusy(which === "real" ? "Loading real websites sample" : "Loading demo export");
    try { const ds = await api.loadDemo(which, "searcher"); await refreshDatasets(); setDatasetId(ds.id); setView("overview"); notify("ok", `${ds.rows_in} rows in, ${ds.rows_out} unique companies, ${ds.rows_in - ds.rows_out} duplicate rows merged`); }
    catch (e) { notify("err", (e as Error).message); } finally { setBusy(null); }
  };
  const upload = async (file: File) => {
    setBusy(`Cleaning ${file.name}`);
    try { const ds = await api.upload(file, "searcher"); await refreshDatasets(); setDatasetId(ds.id); setView("overview"); notify("ok", `${ds.rows_in} rows in, ${ds.rows_out} unique companies`); }
    catch (e) { notify("err", (e as Error).message); } finally { setBusy(null); if (fileRef.current) fileRef.current.value = ""; }
  };
  const startIntel = async (body: { lead_ids?: number[]; top_n?: number }) => {
    if (!datasetId) return;
    try { setJob(await api.startIntel(datasetId, body)); } catch (e) { notify("err", (e as Error).message); }
  };
  const rescore = async (preset: string) => {
    if (!datasetId) return;
    setBusy("Re-scoring");
    try { await api.rescore(datasetId, preset); await Promise.all([refreshDatasets(), refreshStats(), refreshLeads()]); } finally { setBusy(null); }
  };
  const removeDataset = async (id: number) => {
    if (!confirm("Remove this dataset from LeadLens? Your original file is untouched.")) return;
    await api.deleteDataset(id); const ds = await refreshDatasets(); if (id === datasetId) setDatasetId(ds[0]?.id ?? null);
  };
  const seeCallFirst = () => { setFilters({ ...EMPTY_FILTERS, quadrant: ["call_first"] }); setView("leads"); };

  const current = datasets.find((d) => d.id === datasetId) ?? null;
  const pages = Math.max(1, Math.ceil(leads.total / PAGE_SIZE));
  const jobRunning = job && (job.status === "queued" || job.status === "running");
  const exportOpts = useMemo(() => (selected.size ? { ids: [...selected] } : { quadrant: filters.quadrant }), [selected, filters.quadrant]);
  const exportScope = selected.size ? `${selected.size} selected` : filters.quadrant.length ? "filtered" : "all";
  const counts: Partial<Record<View, number>> = { leads: stats?.funnel.rows_out, credits: stats?.funnel.call_first, datasets: datasets.length };
  const thresholds = meta?.thresholds ?? { fit: 65, exit: 55 };

  const landing = (
    <div className="mx-auto max-w-xl pt-12">
      <h1 className="text-xl font-semibold text-ink">Which of your scraped leads should you call first?</h1>
      <p className="mt-3 text-md leading-relaxed text-ink2">Drop in a SaaSquatch Companies export. LeadLens merges duplicates, fixes bad values, reads each company's website for exit signals, and ranks every company on acquisition fit and exit-readiness, so your enrichment credits go to the right owners.</p>
      <div className="mt-6 flex flex-wrap gap-2">
        <button className="btn-primary" onClick={() => loadDemo("synthetic")} disabled={!!busy || apiDown}>{busy ? <Spinner /> : null} Load demo export</button>
        <button className="btn-secondary" onClick={() => fileRef.current?.click()} disabled={!!busy || apiDown}><Upload size={14} /> Upload my CSV</button>
        <button className="btn-ghost" onClick={() => loadDemo("real")} disabled={!!busy || apiDown} title="20 real US businesses, websites only. Best with live web mode.">Real websites sample</button>
      </div>
      {apiDown && <p className="mt-4 text-sm text-amber">Cannot reach the API. Start the backend on port 8787, then reload.</p>}
      <ol className="mt-10 space-y-3 border-t border-line pt-6 text-sm text-ink2">
        <li><span className="font-medium text-ink">Clean and merge.</span> Revenue “4” and headcount “13.1” become flags, InfiVR and InfiVR Inc. become one row, every original row is kept.</li>
        <li><span className="font-medium text-ink">Web Intel.</span> The company site, the Wayback Machine and DNS: “family owned since 1987”, a stale © year, no careers page, “a division of …”.</li>
        <li><span className="font-medium text-ink">Rank and spend.</span> Fit × exit-readiness puts every company in a quadrant. The credits page says where your credits go.</li>
      </ol>
    </div>
  );

  return (
    <div className="flex min-h-full">
      <Sidebar view={view} setView={setView} meta={meta} counts={counts} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-sticky border-b border-line bg-bg/95 backdrop-blur">
          <div className="flex min-h-12 flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2 md:px-6">
            <span className="inline-flex items-center gap-2 text-sm font-semibold text-ink md:hidden"><Radar size={16} className="text-accent" /> LeadLens</span>
            <Popover width={320} button={(open) => (
              <button className={clsx("btn-secondary max-w-[min(70vw,360px)]", open && "bg-surface2")} aria-label="Switch dataset">
                <Database size={14} className="shrink-0 text-ink2" />
                <span className="truncate">{current ? current.name : "No dataset"}</span>
                {current && <span className="shrink-0 text-xs text-ink3">{current.rows_out} companies</span>}
                <ChevronDown size={12} className="shrink-0 text-ink3" />
              </button>
            )}>
              {(close) => (
                <>
                  {datasets.length > 0 && <div className="px-2.5 pb-1 pt-1.5 text-xs text-ink3">Datasets</div>}
                  {datasets.map((d) => (
                    <button key={d.id} className={clsx("menu-item", d.id === datasetId && "bg-surface2")} onClick={() => { setDatasetId(d.id); close(); }}>
                      <span className="min-w-0 flex-1 truncate">{d.name}</span><span className="text-xs text-ink3">{d.rows_out} companies</span>
                    </button>
                  ))}
                  {datasets.length > 0 && <div className="mx-2 my-1 border-t border-line" />}
                  <button className="menu-item" onClick={() => { close(); fileRef.current?.click(); }}><Upload size={14} className="text-ink2" /> Upload a SaaSquatch export</button>
                  <button className="menu-item" onClick={() => { close(); loadDemo("synthetic"); }}><FileUp size={14} className="text-ink2" /> Load the demo export</button>
                  <button className="menu-item" onClick={() => { close(); setView("datasets"); }}><Database size={14} className="text-ink2" /> Manage datasets</button>
                </>
              )}
            </Popover>
            <button className="btn-primary hidden sm:inline-flex" onClick={() => fileRef.current?.click()} disabled={!!busy}><Upload size={14} /> Upload export</button>
            <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
            <div className="flex items-center gap-3 sm:ml-auto">
              {current && meta && (
                <div className="flex items-center gap-2">
                  <span className="hidden text-sm text-ink2 lg:inline">Score as</span>
                  <div className="seg" role="group" aria-label="Scoring preset" title="Who is this list for? Changes the weights behind every score.">
                    {Object.entries(meta.presets).map(([k, p]) => <button key={k} data-on={current.preset === k} onClick={() => rescore(k)} title={p.description}>{p.label}</button>)}
                  </div>
                </div>
              )}
            </div>
          </div>
          {jobRunning && <div className="h-0.5 bg-surface2"><div className="h-full bg-accent transition-[width] duration-300" style={{ width: `${(100 * job!.done) / Math.max(1, job!.total)}%` }} /></div>}
        </header>

        <main className="flex-1 px-4 py-4 pb-20 md:px-6 md:pb-6">
          {view === "datasets" ? (
            <Datasets datasets={datasets} currentId={datasetId} onSelect={(id) => { setDatasetId(id); setView("overview"); }} onDelete={removeDataset} onUpload={() => fileRef.current?.click()} onDemo={loadDemo} busy={!!busy} />
          ) : !current || !stats ? landing : view === "overview" ? (
            <Overview stats={stats} thresholds={thresholds} onPick={setDrawer} onSeeCallFirst={seeCallFirst} onOpenCredits={() => setView("credits")} onRunIntel={() => startIntel({ top_n: 25 })} highlight={highlight} />
          ) : view === "credits" ? (
            <Optimizer datasetId={current.id} onHighlight={setHighlight} onOpen={setDrawer} onShowInLeads={() => { setFilters(EMPTY_FILTERS); setView("leads"); }} />
          ) : (
            <div>
              <PageHeader title="Leads" description={`${stats.funnel.rows_out.toLocaleString()} companies, ranked by quadrant then fit and exit-readiness.`}>
                <ColumnBuilder columns={COLUMNS} order={order} visible={visible} setOrder={setOrder} setVisible={setVisible} />
                <Popover align="right" width={280} button={() => <button className="btn-secondary"><Download size={14} /> Export <ChevronDown size={12} className="text-ink3" /></button>}>
                  {(close) => (
                    <>
                      <a className="menu-item" href={api.exportUrl(current.id, exportOpts)} onClick={close}><span>Full CSV, {exportScope}</span><span className="ml-auto text-xs text-ink3">scores and reasons</span></a>
                      <a className="menu-item" href={api.exportUrl(current.id, { ...exportOpts, format: "saasquatch" })} onClick={close}><span>For SaaSquatch import</span><span className="ml-auto text-xs text-ink3">their 8 columns</span></a>
                    </>
                  )}
                </Popover>
                <button className="btn-primary" disabled={!!jobRunning} onClick={() => startIntel(selected.size ? { lead_ids: [...selected] } : { top_n: 25 })} title="Read websites for exit signals">
                  {jobRunning ? <Spinner /> : null}{jobRunning ? `Checking ${job!.done} of ${job!.total}` : selected.size ? `Run Web Intel on ${selected.size} selected` : "Run Web Intel on top 25"}
                </button>
              </PageHeader>

              <section className="panel">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3 py-2.5">
                  <Filters f={filters} set={setFilters} stats={stats} />
                  {highlight && <button className="btn-ghost" onClick={() => setHighlight(null)}><X size={14} /> Clear credit picks</button>}
                </div>
                {!jobRunning && stats.quadrants.unscored > 0 && stats.funnel.intel_done === 0 && (
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-line px-3 py-2 text-sm text-ink2">
                    <span>{stats.quadrants.unscored} of {stats.funnel.rows_out} companies have too little data to rank yet. Web Intel fills in founding year, owner and contact details from their websites.</span>
                    <button className="focusable cursor-pointer text-accent hover:underline" onClick={() => startIntel({ top_n: 25 })}>Run it on the first 25</button>
                  </div>
                )}
                <LeadTable leads={leads.items} selected={selected} setSelected={setSelected} onOpen={setDrawer} order={order} visible={visible} sort={sort} setSort={setSort} highlight={highlight} loading={loading} />
                <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-xs text-ink2">
                  <span>{leads.total ? `${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, leads.total)} of ${leads.total.toLocaleString()}` : "0"} companies{selected.size ? ` · ${selected.size} selected` : ""}{highlight ? " · credit picks highlighted" : ""}</span>
                  <span className="inline-flex items-center gap-1">
                    <button className="btn-icon" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Previous page"><ChevronLeft size={14} /></button>
                    <span className="tabular-nums">{page} / {pages}</span>
                    <button className="btn-icon" disabled={page >= pages} onClick={() => setPage(page + 1)} aria-label="Next page"><ChevronRight size={14} /></button>
                  </span>
                </div>
              </section>
            </div>
          )}
        </main>
      </div>
      <MobileNav view={view} setView={setView} />

      {drawer != null && <LeadDrawer leadId={drawer} onClose={() => setDrawer(null)} onChanged={() => { refreshStats(); refreshLeads(); }} />}
      {busy && <div className="fixed bottom-16 left-1/2 z-toast -translate-x-1/2 rounded-md border border-line bg-surface2 px-3 py-2 text-sm text-ink shadow-pop md:bottom-4"><span className="inline-flex items-center gap-2"><Spinner /> {busy}…</span></div>}
      {toast && <div role="status" className={clsx("fixed bottom-16 right-4 z-toast max-w-md rounded-md border px-3 py-2 text-sm shadow-pop md:bottom-4", toast.kind === "ok" ? "border-line bg-surface2 text-ink" : "border-danger/50 bg-surface2 text-ink")}>{toast.text}</div>}
    </div>
  );
}
