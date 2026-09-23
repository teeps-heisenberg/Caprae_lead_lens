import type { Dataset, Job, Lead, LeadFilters, Meta, OptimizeResult, Stats } from "./types";

export const API = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") || "http://localhost:8787";
const V1 = `${API}/api/v1`;

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${V1}${path}`, init);
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try { const j = await r.json(); msg = j.detail ? (typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail)) : msg; } catch { /* ignore */ }
    throw new Error(msg);
  }
  return r.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({ method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  meta: () => req<Meta>("/meta"),
  datasets: () => req<Dataset[]>("/datasets"),
  loadDemo: (which: "synthetic" | "real", preset: string) => req<Dataset>(`/datasets/demo?which=${which}&preset=${preset}`, { method: "POST" }),
  upload: (file: File, preset: string) => { const fd = new FormData(); fd.append("file", file); return req<Dataset>(`/datasets/upload?preset=${preset}`, { method: "POST", body: fd }); },
  deleteDataset: (id: number) => fetch(`${V1}/datasets/${id}`, { method: "DELETE" }),
  stats: (id: number) => req<Stats>(`/datasets/${id}/stats`),
  leads: (id: number, f: LeadFilters, sort: string, order: "asc" | "desc", page: number, size: number) => {
    const p = new URLSearchParams({ sort, order, page: String(page), size: String(size), min_fit: String(f.minFit), min_exit: String(f.minExit) });
    if (f.quadrant.length) p.set("quadrant", f.quadrant.join(","));
    if (f.grade.length) p.set("grade", f.grade.join(""));
    if (f.state) p.set("state", f.state);
    if (f.industry) p.set("industry", f.industry);
    if (f.hasEmail) p.set("has_email", f.hasEmail === "1" ? "true" : "false");
    if (f.hasPhone) p.set("has_phone", f.hasPhone === "1" ? "true" : "false");
    if (f.intel) p.set("intel", f.intel === "1" ? "true" : "false");
    if (f.q) p.set("q", f.q);
    return req<{ total: number; page: number; size: number; items: Lead[] }>(`/datasets/${id}/leads?${p}`);
  },
  lead: (id: number) => req<{ lead: Lead; raw_rows: { id: number; row_index: number; payload: Record<string, string> }[] }>(`/leads/${id}`),
  startIntel: (id: number, body: { lead_ids?: number[]; top_n?: number }) => req<Job>(`/datasets/${id}/intel`, json(body)),
  job: (id: number) => req<Job>(`/jobs/${id}`),
  rescore: (id: number, preset: string) => req<{ rescored: number }>(`/datasets/${id}/rescore`, json({ preset })),
  optimize: (id: number, credits: number) => req<OptimizeResult>(`/datasets/${id}/optimize?credits=${credits}`),
  exportUrl: (id: number, opts: { ids?: number[]; quadrant?: string[]; format?: "full" | "saasquatch" }) => {
    const p = new URLSearchParams();
    if (opts.format) p.set("format", opts.format);
    if (opts.ids?.length) p.set("ids", opts.ids.join(","));
    if (opts.quadrant?.length) p.set("quadrant", opts.quadrant.join(","));
    return `${V1}/datasets/${id}/export?${p}`;
  },
};
