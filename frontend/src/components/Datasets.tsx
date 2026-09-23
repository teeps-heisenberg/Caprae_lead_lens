import { FileUp, Trash2, Upload } from "lucide-react";
import type { Dataset } from "../types";
import { PageHeader } from "./bits";

const SOURCE: Record<string, string> = { upload: "Uploaded", demo_synthetic: "Demo export", demo_real: "Real websites sample" };

export function Datasets({ datasets, currentId, onSelect, onDelete, onUpload, onDemo, busy }: {
  datasets: Dataset[]; currentId: number | null; onSelect: (id: number) => void; onDelete: (id: number) => void;
  onUpload: () => void; onDemo: (which: "synthetic" | "real") => void; busy: boolean;
}) {
  return (
    <div>
      <PageHeader title="Datasets" description="Each upload is cleaned, deduplicated and scored on arrival. Original rows are kept untouched.">
        <button className="btn-secondary" onClick={() => onDemo("real")} disabled={busy} title="20 real US businesses, websites only. Best with live web mode."><FileUp size={14} /> Real websites sample</button>
        <button className="btn-secondary" onClick={() => onDemo("synthetic")} disabled={busy}><FileUp size={14} /> Load demo export</button>
        <button className="btn-primary" onClick={onUpload} disabled={busy}><Upload size={14} /> Upload export</button>
      </PageHeader>
      <section className="panel overflow-hidden">
        <table className="w-full">
          <thead><tr>{["Dataset", "Source", "Rows in", "Companies", "Duplicates merged", "Flagged", "Preset", "Added", ""].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
          <tbody>
            {datasets.map((d) => (
              <tr key={d.id} onClick={() => onSelect(d.id)} aria-selected={d.id === currentId} className="cursor-pointer transition-colors hover:bg-surface2/60 aria-selected:bg-accent/[0.06]">
                <td className="td font-medium">{d.name}{d.id === currentId && <span className="ml-2 text-xs text-accent">current</span>}</td>
                <td className="td text-ink2">{SOURCE[d.source] ?? d.source}</td>
                <td className="td tabular-nums">{d.rows_in}</td>
                <td className="td tabular-nums">{d.rows_out}</td>
                <td className="td tabular-nums">{d.rows_in - d.rows_out}</td>
                <td className="td tabular-nums">{d.rows_flagged}</td>
                <td className="td text-ink2">{d.preset === "sales" ? "Sales" : "Searcher"}</td>
                <td className="td text-ink2">{new Date(d.created_at).toLocaleDateString()}</td>
                <td className="td text-right"><button className="btn-icon" title="Remove dataset" onClick={(e) => { e.stopPropagation(); onDelete(d.id); }}><Trash2 size={14} /></button></td>
              </tr>
            ))}
            {datasets.length === 0 && <tr><td colSpan={9} className="px-4 py-10 text-center text-sm text-ink2">No datasets yet. Upload a SaaSquatch export or load the demo.</td></tr>}
          </tbody>
        </table>
      </section>
    </div>
  );
}
