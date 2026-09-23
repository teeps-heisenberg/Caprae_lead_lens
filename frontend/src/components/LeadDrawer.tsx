import clsx from "clsx";
import { Check, Copy, ExternalLink, RefreshCw, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { api } from "../api";
import type { Breakdown, Lead } from "../types";
import { FLAG_LABEL, STATUS_LABEL, fitConfidence, money, num, scoreTint } from "../lib/format";
import { QuadrantMark, Spinner } from "./bits";

function Factors({ items }: { items: Breakdown[] }) {
  return (
    <ul className="divide-y divide-line">
      {items.filter((b) => b.confidence == null).map((b) => (
        <li key={b.factor} className={clsx("flex items-baseline gap-3 py-1.5 text-sm", b.known === false && "opacity-60")}>
          <span className="w-[132px] shrink-0 text-ink2">{b.factor}</span>
          <span className="min-w-0 flex-1 truncate text-ink" title={b.reason}>{b.reason}</span>
          <span className="w-12 shrink-0 text-right tabular-nums text-ink2">{b.points}<span className="text-ink3">/{b.max}</span></span>
        </li>
      ))}
    </ul>
  );
}

function Section({ title, children, right }: { title: string; children: ReactNode; right?: ReactNode }) {
  return (
    <section className="border-t border-line px-5 py-4">
      <div className="mb-2 flex items-center justify-between"><h3 className="text-sm font-medium text-ink">{title}</h3>{right}</div>
      {children}
    </section>
  );
}

function Facts({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
      {items.map(([k, v]) => <div key={k} className="min-w-0"><dt className="text-xs text-ink3">{k}</dt><dd className="truncate text-ink" title={typeof v === "string" ? v : undefined}>{v}</dd></div>)}
    </dl>
  );
}

function CopyBtn({ text }: { text: string }) {
  const [ok, setOk] = useState(false);
  return <button className="btn-ghost h-7 text-xs" onClick={() => { navigator.clipboard?.writeText(text); setOk(true); setTimeout(() => setOk(false), 1200); }}>{ok ? <Check size={13} /> : <Copy size={13} />} {ok ? "Copied" : "Copy"}</button>;
}

const yn = (v: boolean | null) => (v == null ? "unknown" : v ? "yes" : "no");

export function LeadDrawer({ leadId, onClose, onChanged }: { leadId: number; onClose: () => void; onChanged: () => void }) {
  const [data, setData] = useState<{ lead: Lead; raw_rows: { id: number; row_index: number; payload: Record<string, string> }[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const load = () => api.lead(leadId).then(setData).catch(() => setData(null));
  useEffect(() => { setData(null); load(); }, [leadId]);
  useEffect(() => { const k = (e: KeyboardEvent) => e.key === "Escape" && onClose(); window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k); }, [onClose]);
  useEffect(() => { const prev = document.body.style.overflow; document.body.style.overflow = "hidden"; return () => { document.body.style.overflow = prev; }; }, []);

  const runIntel = async () => {
    if (!data) return;
    setBusy(true);
    try {
      const job = await api.startIntel(data.lead.dataset_id, { lead_ids: [data.lead.id] });
      // Live fetch + Gemini can take a while on a slow site: wait for the job itself, up to 5 minutes.
      for (let i = 0; i < 300; i++) {
        await new Promise((r) => setTimeout(r, 1000));
        const j = await api.job(job.id);
        if (j.status === "done" || j.status === "failed") break;
      }
      await load(); onChanged();
    } finally { setBusy(false); }
  };

  const l = data?.lead; const wi = l?.web_intel; const ex = wi?.extracted && "pages_read" in wi.extracted ? wi.extracted : null; const ai = wi?.llm ?? null;
  const flags = l?.flags.filter((f) => f !== "merged_duplicate") ?? [];
  return (
    <>
      <div className="fixed inset-0 z-backdrop bg-black/50" onClick={onClose} />
      <aside role="dialog" aria-modal="true" aria-label={l ? l.company : "Company details"} className="fixed right-0 top-0 z-sheet flex h-full w-full max-w-[540px] flex-col border-l border-line bg-surface shadow-pop">
        {!l ? (
          <div className="space-y-3 p-5">
            <span className="skeleton block h-4 w-24" /><span className="skeleton block h-6 w-64" /><span className="skeleton block h-4 w-40" />
            <div className="grid grid-cols-3 gap-3 pt-2">{[0, 1, 2].map((i) => <span key={i} className="skeleton block h-16" />)}</div>
          </div>
        ) : (
          <>
            <header className="px-5 pb-4 pt-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <QuadrantMark q={l.quadrant} className="text-xs" />
                  <h2 className="mt-1 truncate text-lg font-semibold text-ink">{l.company}</h2>
                  <div className="text-sm text-ink2">{[l.industry, l.city && `${l.city}, ${l.state ?? ""}`].filter(Boolean).join(" · ")}</div>
                </div>
                <button className="btn-icon shrink-0" onClick={onClose} aria-label="Close"><X size={16} /></button>
              </div>
              <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
                {l.website && <a className="focusable text-ink2 hover:text-ink" href={l.website} target="_blank" rel="noreferrer">{l.domain}</a>}
                {l.linkedin && <a className="focusable text-ink2 hover:text-ink" href={l.linkedin} target="_blank" rel="noreferrer">LinkedIn</a>}
                {l.email && <a className="focusable text-ink2 hover:text-ink" href={`mailto:${l.email}`}>{l.email}</a>}
                {l.phone && <a className="focusable text-ink2 hover:text-ink" href={`tel:${l.phone}`}>{l.phone}</a>}
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3">
                {([["Acquisition fit", l.fit_score, fitConfidence(l.fit_breakdown)], ["Exit-readiness", l.exit_score, null], ["Data quality", l.quality_score, null]] as [string, number, number | null][]).map(([t, v, c]) => (
                  <div key={t} className="rounded-md border border-line px-3 py-2">
                    <div className="text-xs text-ink3">{t}</div>
                    <div className="flex items-baseline gap-1.5"><span className={clsx("text-xl font-semibold tabular-nums", scoreTint(v))}>{v}</span>{c != null && c < 100 && <span className="text-xs text-ink3">{c}% known</span>}</div>
                  </div>
                ))}
              </div>
            </header>

            <div className="flex-1 overflow-auto">
              <Section title="Why this fit score"><Factors items={l.fit_breakdown} /></Section>
              <Section title="Why this exit-readiness score"><Factors items={l.exit_breakdown} /></Section>

              <Section title="Web Intel" right={<button className="btn-ghost h-7 text-xs" onClick={runIntel} disabled={busy || !l.domain}>{busy ? <Spinner /> : <RefreshCw size={13} />} {l.intel_at ? "Re-check" : "Check website"}</button>}>
                {!l.intel_at ? (
                  <p className="text-sm text-ink2">{l.domain ? "Not checked yet. Reads the company website, the Wayback Machine and DNS for exit signals." : "No website on record."}</p>
                ) : l.fetch_status !== "ok" ? (
                  <p className="text-sm text-ink2">{STATUS_LABEL[l.fetch_status ?? ""] ?? l.fetch_status}. Scored from export data only.</p>
                ) : (
                  <div className="space-y-4">
                    {ai && (
                      <div className="space-y-3 text-sm">
                        <div className="rounded-md border border-line bg-surface2/50 p-3">
                          <p className="text-ink">{ai.analyst_note}</p>
                          {ai.exit_reasoning && <p className="mt-1.5 text-ink2">{ai.exit_reasoning}</p>}
                          <p className="mt-2 text-xs text-ink3">{ai._provider?.startsWith("gemini") ? "Gemini" : "Rule-based"} · {ai.what_they_sell}</p>
                        </div>
                        <dl className="space-y-2">
                          {([["Owner-operated", ai.owner_operated], ["Independent", ai.independence]] as const).map(([k, j]) => (
                            <div key={k}><dt className="text-xs text-ink3">{k}: <span className="text-ink2">{yn(j.value)}</span></dt><dd className="text-ink">{j.evidence}</dd></div>
                          ))}
                        </dl>
                        {ai.succession_signals.length > 0 && (
                          <div><div className="text-xs text-ink3">Succession signals</div><ul className="mt-1 list-disc space-y-0.5 pl-4 text-ink">{ai.succession_signals.map((s) => <li key={s}>{s}</li>)}</ul></div>
                        )}
                        <div className="rounded-md border border-line px-3 py-2.5">
                          <div className="flex items-center justify-between"><span className="text-xs text-ink3">Opening line for outreach</span><CopyBtn text={ai.outreach_angle} /></div>
                          <p className="mt-1 text-ink">{ai.outreach_angle}</p>
                        </div>
                      </div>
                    )}
                    {ex && (
                      <Facts items={[
                        ["Pages read", ex.pages_read.join(", ")], ["Footer © year", ex.copyright_year ?? "—"], ["“Since” year", ex.since_year ?? "—"],
                        ["Wayback first / last", `${ex.wayback_first_year ?? "—"} / ${ex.wayback_last_year ?? "—"}`], ["Careers page", ex.has_careers_page ? "yes" : "no"], ["Blog or news", ex.has_blog ? "yes" : "no"],
                        ["Family language", ex.family_phrases.join(", ") || "—"], ["Parent or PE mention", ex.acquisition_phrases.join(", ") || "—"],
                        ["Founder named", ex.founder_mentions.join(", ") || "—"], ["Mail server", ex.mx_ok == null ? "—" : ex.mx_ok ? "ok" : "none"],
                        ["Emails on site", ex.emails_on_site.join(", ") || "—"], ["Site technology", ex.tech_hints.join(", ") || "—"],
                      ]} />
                    )}
                    {wi?.from_cache && <div className="text-xs text-ink3">Served from 7-day cache.</div>}
                  </div>
                )}
              </Section>

              <Section title="Company data">
                <Facts items={[["Revenue", money(l.revenue_usd)], ["Employees", num(l.employees)], ["Founded", l.year_founded ?? "—"], ["Business type", l.business_type ?? "—"],
                  ["Category", l.category ?? "—"], ["BBB rating", l.bbb_rating ?? "—"], ["Owner", l.owner_name ? `${l.owner_name}${l.owner_title ? `, ${l.owner_title}` : ""}` : "—"],
                  ["Ownership type", l.ownership_type ?? "—"], ["Parent company", l.parent_company ?? "—"], ["Address", [l.street, l.city, l.state].filter(Boolean).join(", ") || "—"], ["Source", l.source ?? "—"]]} />
              </Section>

              {(flags.length > 0 || l.conflicts.length > 0) && (
                <Section title="Data notes">
                  <ul className="space-y-1 text-sm">
                    {flags.map((f) => <li key={f} className="text-ink2">{FLAG_LABEL[f] ?? f}</li>)}
                    {l.conflicts.map((c) => <li key={c.field} className="text-ink2">Conflict on {c.field}: kept <span className="text-ink">{String(c.chosen)}</span> over {c.options.filter((o) => String(o.value) !== String(c.chosen)).map((o) => String(o.value)).join(", ")}</li>)}
                  </ul>
                </Section>
              )}

              {data.raw_rows.length > 1 && (
                <Section title={`Merged from ${data.raw_rows.length} export rows`}>
                  <table className="w-full text-xs">
                    <thead><tr>{["Row", "Company", "Revenue", "Employees", "Email"].map((h) => <th key={h} className="th !static !h-7 !px-2">{h}</th>)}</tr></thead>
                    <tbody>{data.raw_rows.map((r) => <tr key={r.id}><td className="td !h-8 !px-2 text-ink3">#{r.row_index + 1}</td><td className="td !h-8 !px-2">{r.payload["Company"]}</td><td className="td !h-8 !px-2">{r.payload["Revenue"]}</td><td className="td !h-8 !px-2">{r.payload["Employees Count"]}</td><td className="td !h-8 !px-2">{r.payload["Email"]}</td></tr>)}</tbody>
                  </table>
                </Section>
              )}
            </div>

            <footer className="flex items-center justify-between border-t border-line px-5 py-2.5 text-xs text-ink3">
              <span>Lead #{l.id}{l.intel_at && ` · checked ${new Date(l.intel_at).toLocaleString()}`}</span>
              {l.website && <a className="focusable inline-flex items-center gap-1 text-ink2 hover:text-ink" href={l.website} target="_blank" rel="noreferrer">Open site <ExternalLink size={11} /></a>}
            </footer>
          </>
        )}
      </aside>
    </>
  );
}
