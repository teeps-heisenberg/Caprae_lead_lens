import { ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import type { Lead, OptimizeResult, Stats } from "../types";
import { QuadrantChart } from "./QuadrantChart";
import { QuadrantMark, Score } from "./bits";

/** The Overview page: funnel and chart, then the two things a searcher does next: who to call, where credits go. */
export function Overview({ stats, thresholds, onPick, onSeeCallFirst, onOpenCredits, onRunIntel, highlight }: {
  stats: Stats; thresholds: { fit: number; exit: number }; onPick: (id: number) => void;
  onSeeCallFirst: () => void; onOpenCredits: () => void; onRunIntel: () => void; highlight: Set<number> | null;
}) {
  const f = stats.funnel;
  const [top, setTop] = useState<Lead[]>([]);
  const [plan, setPlan] = useState<OptimizeResult | null>(null);
  useEffect(() => {
    api.leads(stats.dataset.id, { quadrant: ["call_first"], grade: [], state: "", industry: "", hasEmail: "", hasPhone: "", intel: "", q: "", minFit: 0, minExit: 0 }, "priority", "desc", 1, 8).then((r) => setTop(r.items)).catch(() => setTop([]));
    api.optimize(stats.dataset.id, 50).then(setPlan).catch(() => setPlan(null));
  }, [stats]);

  const rows: [string, number, string][] = [
    ["Rows in export", f.rows_in, ""],
    ["Unique companies", f.rows_out, `${f.duplicates_removed} duplicate rows merged`],
    ["Values fixed or flagged", f.rows_flagged, "bad revenue, headcount, emails"],
    ["Reachable now", f.with_contact, "have an email or phone"],
    ["Web Intel checked", f.intel_done, "websites read for exit signals"],
  ];
  const needsIntel = stats.quadrants.unscored > 0 && f.intel_done === 0;

  return (
    <div className="space-y-4">
      {needsIntel && (
        <div className="panel flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm">
          <span className="text-ink">{stats.quadrants.unscored} of {f.rows_out} companies have too little data to rank yet. Web Intel reads their websites and fills in founding year, owner and contact details.</span>
          <button className="btn-primary" onClick={onRunIntel}>Run Web Intel on the first 25</button>
        </div>
      )}

      <section className="panel grid md:grid-cols-[300px_1fr]">
        <div className="flex flex-col justify-between border-b border-line p-4 md:border-b-0 md:border-r">
          <dl className="space-y-3">
            {rows.map(([k, v, sub]) => (
              <div key={k} className="flex items-baseline justify-between gap-3">
                <dt className="min-w-0"><div className="text-sm text-ink">{k}</div>{sub && <div className="text-xs text-ink3">{sub}</div>}</dt>
                <dd className="text-[15px] font-semibold tabular-nums text-ink">{v.toLocaleString()}</dd>
              </div>
            ))}
          </dl>
          <button onClick={onSeeCallFirst} className="focusable group mt-4 flex cursor-pointer items-center justify-between rounded-md border border-accent/40 bg-accent/[0.07] px-3 py-2.5 text-left transition-colors hover:bg-accent/[0.12]">
            <span><span className="block text-sm font-medium text-ink">Call first</span><span className="block text-xs text-ink2">good fit and exit signals</span></span>
            <span className="inline-flex items-center gap-1 text-xl font-semibold tabular-nums text-ink">{f.call_first}<ArrowRight size={16} className="text-accent transition-transform group-hover:translate-x-0.5" /></span>
          </button>
        </div>
        <div className="p-4"><QuadrantChart stats={stats} thresholds={thresholds} onPick={onPick} highlight={highlight} /></div>
      </section>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <section className="panel">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <h2 className="text-sm font-medium text-ink">Who to call first</h2>
            <button className="btn-ghost h-7 text-xs" onClick={onSeeCallFirst}>All {f.call_first} in Leads <ArrowRight size={12} /></button>
          </div>
          {top.length === 0 ? <p className="px-4 py-6 text-sm text-ink2">No Call-first companies yet. Run Web Intel to surface exit signals.</p> : (
            <ul>
              {top.map((l) => (
                <li key={l.id}>
                  <button onClick={() => onPick(l.id)} className="focusable flex w-full cursor-pointer items-center gap-3 px-4 py-2 text-left transition-colors hover:bg-surface2/60">
                    <span className="min-w-0 flex-1"><span className="block truncate text-sm text-ink">{l.company}</span><span className="block truncate text-xs text-ink3">{[l.industry, l.city].filter(Boolean).join(" · ")}</span></span>
                    <span className="hidden sm:block"><QuadrantMark q={l.quadrant} className="text-xs" /></span>
                    <span className="w-24 text-right text-sm tabular-nums text-ink2"><Score value={l.fit_score} /> <span className="text-ink3">/</span> <Score value={l.exit_score} /></span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <h2 className="text-sm font-medium text-ink">Where 50 credits would go<span className="block text-xs font-normal text-ink2">1 credit = 1 contact unlock in SaaSquatch</span></h2>
            <button className="btn-ghost h-7 text-xs" onClick={onOpenCredits}>Plan credits <ArrowRight size={12} /></button>
          </div>
          {plan ? (
            <dl className="divide-y divide-line px-4 text-sm">
              {[
                ["Unlock now", plan.summary.credits_used, "companies worth a credit"],
                ["Call-first among them", plan.summary.call_first_in_picks, "your first dials"],
                ["Free to call today", plan.summary.already_reachable_free, "already have email and phone"],
                ["Saved by dedupe", plan.summary.credits_saved_by_dedupe, "duplicate rows you won't pay for"],
                ["Avoided on low value", plan.summary.credits_avoided_low_value, "not worth unlocking"],
              ].map(([k, v, sub]) => (
                <div key={String(k)} className="flex items-baseline justify-between gap-3 py-2.5"><dt><div className="text-ink">{k}</div><div className="text-xs text-ink3">{sub}</div></dt><dd className="font-semibold tabular-nums text-ink">{v}</dd></div>
              ))}
            </dl>
          ) : <p className="px-4 py-6 text-sm text-ink2">Planning…</p>}
        </section>
      </div>
    </div>
  );
}
