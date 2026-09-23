import { Download, Table2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import type { OptimizeResult } from "../types";
import { PageHeader, QuadrantMark, Spinner } from "./bits";

/** The Credits page. */
export function Optimizer({ datasetId, onHighlight, onOpen, onShowInLeads }: {
  datasetId: number; onHighlight: (ids: Set<number> | null) => void; onOpen: (id: number) => void; onShowInLeads: () => void;
}) {
  const [credits, setCredits] = useState(50);
  const [res, setRes] = useState<OptimizeResult | null>(null);
  const [busy, setBusy] = useState(false);
  const run = async (n = credits) => {
    setBusy(true);
    try { const r = await api.optimize(datasetId, n); setRes(r); onHighlight(new Set(r.picks.map((p) => p.id))); } finally { setBusy(false); }
  };
  useEffect(() => { run(); }, [datasetId]);
  const s = res?.summary;
  return (
    <div>
      <PageHeader title="Where to spend your credits" description="In SaaSquatch, seeing a scraped company is free, but unlocking its contact details (email, phone, LinkedIn) costs one credit. This page picks the companies worth a credit: good fit, likely to sell, and not reachable yet.">
        <label className="flex items-center gap-2 text-sm text-ink2" title="LeadLens is not connected to your SaaSquatch account. Type the credits your plan shows, or pick a plan.">Credits you have
          <input type="number" min={1} max={5000} className="input w-24" value={credits} onChange={(e) => setCredits(Math.max(1, Number(e.target.value) || 1))} onKeyDown={(e) => e.key === "Enter" && run()} aria-label="Credits you have in SaaSquatch" />
        </label>
        <div className="seg h-8" role="group" aria-label="SaaSquatch plan">
          {([["Free", 5], ["Bronze", 50], ["Silver", 125], ["Gold", 292]] as [string, number][]).map(([name, n]) => (
            <button key={n} data-on={credits === n} onClick={() => { setCredits(n); run(n); }} title={`${name} plan: ${n} credits a month`}>{name} <span className="text-ink3">{n}</span></button>
          ))}
        </div>
        <button className="btn-primary" onClick={() => run()} disabled={busy}>{busy ? <Spinner /> : null} Plan {credits} credits</button>
      </PageHeader>

      {s && (
        <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
          <section className="panel self-start">
            <dl className="divide-y divide-line px-4 text-sm">
              {[
                ["Credits to spend", s.credits_used, "on companies worth unlocking"],
                ["Call-first among them", s.call_first_in_picks, "your first dials"],
                ["Free to call today", s.already_reachable_free, "already have email and phone"],
                ["Saved by dedupe", s.credits_saved_by_dedupe, "duplicate rows you won't pay for"],
                ["Avoided on low value", s.credits_avoided_low_value, "not worth unlocking"],
                ["Good leads beyond balance", Math.max(0, s.candidates_needing_credit - s.credits_used), "next month's credits"],
              ].map(([k, v, sub]) => (
                <div key={String(k)} className="flex items-baseline justify-between gap-3 py-2.5"><dt><div className="text-ink">{k}</div><div className="text-xs text-ink3">{sub}</div></dt><dd className="font-semibold tabular-nums text-ink">{v}</dd></div>
              ))}
            </dl>
            <div className="flex flex-wrap gap-2 border-t border-line p-3">
              <button className="btn-secondary" onClick={onShowInLeads}><Table2 size={14} /> Show picks in Leads</button>
              {res && <a className="btn-secondary" href={api.exportUrl(datasetId, { ids: res.picks.map((p) => p.id) })}><Download size={14} /> Export picks</a>}
            </div>
          </section>

          <section className="panel overflow-hidden">
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line px-4 py-2.5">
              <span className="text-sm font-medium text-ink">Unlock in this order</span>
              <span className="text-xs text-ink2">Companies that already have an email and phone are skipped: they cost nothing to call.</span>
            </div>
            <div className="overflow-auto">
              <table className="w-full">
                <thead><tr><th className="th w-10">#</th><th className="th">Company</th><th className="th">Quadrant</th><th className="th text-right">Fit</th><th className="th text-right">Exit</th><th className="th">Credit unlocks</th></tr></thead>
                <tbody>
                  {res!.picks.map((p, i) => (
                    <tr key={p.id} onClick={() => onOpen(p.id)} className="cursor-pointer transition-colors hover:bg-surface2/60">
                      <td className="td text-ink3">{i + 1}</td>
                      <td className="td font-medium">{p.company}</td>
                      <td className="td"><QuadrantMark q={p.quadrant} /></td>
                      <td className="td text-right tabular-nums">{p.fit_score}</td>
                      <td className="td text-right tabular-nums">{p.exit_score}</td>
                      <td className="td text-ink2">{p.missing.join(" and ")}</td>
                    </tr>
                  ))}
                  {res!.picks.length === 0 && <tr><td colSpan={6} className="px-4 py-10 text-center text-sm text-ink2">Nothing needs a credit. Every good lead already has contact details.</td></tr>}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
