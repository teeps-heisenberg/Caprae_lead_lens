import clsx from "clsx";
import { Coins, Database, LayoutDashboard, Radar, Table2 } from "lucide-react";
import { API } from "../api";
import type { Meta } from "../types";

export type View = "overview" | "leads" | "credits" | "datasets";

export const NAV: { id: View; label: string; icon: typeof Table2 }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "leads", label: "Leads", icon: Table2 },
  { id: "credits", label: "Credits", icon: Coins },
  { id: "datasets", label: "Datasets", icon: Database },
];

export function Sidebar({ view, setView, meta, counts }: { view: View; setView: (v: View) => void; meta: Meta | null; counts: Partial<Record<View, number>> }) {
  return (
    <aside className="hidden w-[208px] shrink-0 flex-col border-r border-line bg-surface2 md:flex">
      <div className="flex h-12 items-center gap-2 px-4 text-sm font-semibold text-ink"><Radar size={16} className="text-accent" /> LeadLens</div>
      <nav className="flex-1 px-2 pt-1" aria-label="Main">
        {NAV.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setView(id)} aria-current={view === id ? "page" : undefined}
            className={clsx("focusable mb-0.5 flex h-9 w-full cursor-pointer items-center gap-2.5 rounded-md px-2.5 text-sm transition-colors duration-150",
              view === id ? "bg-surface font-medium text-ink shadow-[0_1px_2px_oklch(0_0_0/0.06)] ring-1 ring-line" : "text-ink2 hover:bg-surface/70 hover:text-ink")}>
            <Icon size={16} strokeWidth={1.75} className={view === id ? "text-accent" : "text-ink3"} />
            <span className="flex-1 text-left">{label}</span>
            {counts[id] != null && <span className="text-xs tabular-nums text-ink3">{counts[id]!.toLocaleString()}</span>}
          </button>
        ))}
      </nav>
      <div className="border-t border-line px-4 py-3 text-xs text-ink3">
        {meta && (
          <div className="mb-1" title="Web Intel reads company websites. Demo companies have bundled sample sites; real companies are fetched from the web. Gemini or rules then turn the text into judgements.">
            Web Intel: {meta.enrich_mode === "live" ? "real web" : meta.enrich_mode === "fixture" ? "sample sites only" : "sample sites + real web"}
            <br />Reader: {meta.llm_provider === "gemini" ? "Gemini" : "rules only"}
          </div>
        )}
        <a className="text-ink2 hover:text-ink" href={`${API}/docs`} target="_blank" rel="noreferrer">API documentation</a>
      </div>
    </aside>
  );
}

/** Phone and tablet: the same four destinations as a bottom tab bar. */
export function MobileNav({ view, setView }: { view: View; setView: (v: View) => void }) {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-sticky grid grid-cols-4 border-t border-line bg-surface2 md:hidden" aria-label="Main">
      {NAV.map(({ id, label, icon: Icon }) => (
        <button key={id} onClick={() => setView(id)} aria-current={view === id ? "page" : undefined}
          className={clsx("focusable flex h-14 cursor-pointer flex-col items-center justify-center gap-1 text-xs", view === id ? "text-ink" : "text-ink3")}>
          <Icon size={18} strokeWidth={1.75} className={view === id ? "text-accent" : undefined} />{label}
        </button>
      ))}
    </nav>
  );
}
