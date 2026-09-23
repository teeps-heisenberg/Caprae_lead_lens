import clsx from "clsx";
import { Search, SlidersHorizontal, X } from "lucide-react";
import type { LeadFilters, Quadrant, Stats } from "../types";
import { EMPTY_FILTERS } from "../types";
import { QUADRANT, QUADRANT_ORDER } from "../lib/format";
import { Popover, QuadrantDot } from "./bits";

/** Search and quadrant tabs stay visible; everything else lives in one Filters menu with a count. */
export function Filters({ f, set, stats }: { f: LeadFilters; set: (f: LeadFilters) => void; stats: Stats }) {
  const toggle = <T,>(arr: T[], v: T) => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);
  const hidden = [f.grade.length > 0, !!f.state, !!f.industry, !!f.hasEmail, !!f.hasPhone, !!f.intel].filter(Boolean).length;
  const active = JSON.stringify(f) !== JSON.stringify(EMPTY_FILTERS);
  const row = (label: string, el: JSX.Element) => <label className="flex items-center justify-between gap-3 py-1.5 text-sm text-ink2">{label}{el}</label>;
  const sel = (value: string, onChange: (v: string) => void, opts: [string, string][]) => (
    <select className="input h-7 w-[150px]" value={value} onChange={(e) => onChange(e.target.value)}>{opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
  );
  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="relative">
        <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink3" />
        <input className="input w-60 pl-8" placeholder="Search companies, cities, owners" value={f.q} onChange={(e) => set({ ...f, q: e.target.value })} aria-label="Search" />
      </label>
      <div className="seg" role="group" aria-label="Quadrant">
        <button data-on={f.quadrant.length === 0} onClick={() => set({ ...f, quadrant: [] })}>All</button>
        {QUADRANT_ORDER.map((q: Quadrant) => (
          <button key={q} data-on={f.quadrant.includes(q)} onClick={() => set({ ...f, quadrant: toggle(f.quadrant, q) })} title={QUADRANT[q].hint} aria-label={QUADRANT[q].label} className="inline-flex items-center gap-1.5">
            <QuadrantDot q={q} size={7} />{QUADRANT[q].label}
          </button>
        ))}
      </div>
      <Popover width={300} button={(open) => (
        <button className={clsx("btn-secondary", (open || hidden > 0) && "border-lineStrong")}><SlidersHorizontal size={14} /> Filters{hidden > 0 && <span className="kbd">{hidden}</span>}</button>
      )}>
        {() => (
          <div className="p-2">
            {row("Grade", <div className="seg h-7">{["A", "B", "C", "D"].map((g) => <button key={g} data-on={f.grade.includes(g)} onClick={() => set({ ...f, grade: toggle(f.grade, g) })} className="!px-2.5">{g}</button>)}</div>)}
            {row("State", sel(f.state, (v) => set({ ...f, state: v }), [["", "Any"], ...stats.filters.states.map((s) => [s, s] as [string, string])]))}
            {row("Industry", sel(f.industry, (v) => set({ ...f, industry: v }), [["", "Any"], ...stats.filters.industries.map((s) => [s, s] as [string, string])]))}
            {row("Email", sel(f.hasEmail, (v) => set({ ...f, hasEmail: v as LeadFilters["hasEmail"] }), [["", "Any"], ["1", "Has email"], ["0", "No email"]]))}
            {row("Phone", sel(f.hasPhone, (v) => set({ ...f, hasPhone: v as LeadFilters["hasPhone"] }), [["", "Any"], ["1", "Has phone"], ["0", "No phone"]]))}
            {row("Web Intel", sel(f.intel, (v) => set({ ...f, intel: v as LeadFilters["intel"] }), [["", "Any"], ["1", "Checked"], ["0", "Not checked"]]))}
          </div>
        )}
      </Popover>
      {active && <button className="btn-ghost" onClick={() => set(EMPTY_FILTERS)}><X size={14} /> Clear</button>}
    </div>
  );
}
