import clsx from "clsx";
import { Columns3, Eye, EyeOff, GripVertical } from "lucide-react";
import { useState } from "react";
import { Popover } from "./bits";

export interface ColumnDef { id: string; label: string; locked?: boolean }

export const VIEW_PRESETS: Record<string, { label: string; visible: string[] }> = {
  searcher: { label: "Searcher", visible: ["quadrant", "company", "fit", "exit", "revenue", "employees", "founded", "location", "industry", "reach", "intel"] },
  sales: { label: "Sales", visible: ["company", "fit", "reach", "owner", "industry", "employees", "revenue", "location", "intel"] },
  quality: { label: "Data quality", visible: ["company", "quality", "flags", "email", "phone", "website", "revenue", "employees", "founded"] },
};

export function ColumnBuilder({ columns, order, visible, setOrder, setVisible }: {
  columns: ColumnDef[]; order: string[]; visible: Record<string, boolean>;
  setOrder: (o: string[]) => void; setVisible: (v: Record<string, boolean>) => void;
}) {
  const [drag, setDrag] = useState<string | null>(null);
  const ordered = [...order.filter((id) => columns.some((c) => c.id === id)), ...columns.map((c) => c.id).filter((id) => !order.includes(id))];
  const byId = Object.fromEntries(columns.map((c) => [c.id, c]));
  const applyPreset = (key: string) => {
    const p = VIEW_PRESETS[key];
    setVisible(Object.fromEntries(columns.map((c) => [c.id, c.locked || p.visible.includes(c.id)])));
    setOrder([...columns.filter((c) => c.locked).map((c) => c.id), ...p.visible, ...columns.map((c) => c.id).filter((id) => !p.visible.includes(id) && !byId[id].locked)]);
  };
  return (
    <Popover align="right" width={260} button={() => <button className="btn-secondary" title="Show, hide and reorder columns"><Columns3 size={14} /> Columns</button>}>
      {() => (
        <div className="p-1">
          <div className="flex items-center justify-between px-2 py-1.5">
            <span className="text-xs text-ink3">Views</span>
            <div className="flex gap-1">{Object.entries(VIEW_PRESETS).map(([k, p]) => <button key={k} className="btn-ghost h-6 px-2 text-xs" onClick={() => applyPreset(k)}>{p.label}</button>)}</div>
          </div>
          <div className="mx-2 my-1 border-t border-line" />
          <ul className="max-h-[340px] overflow-auto">
            {ordered.map((id) => {
              const c = byId[id]; const on = visible[id] !== false;
              return (
                <li key={id} draggable={!c.locked} onDragStart={() => setDrag(id)} onDragOver={(e) => e.preventDefault()}
                  onDrop={() => { if (!drag || drag === id || c.locked) return; const o = ordered.filter((x) => x !== drag); o.splice(o.indexOf(id), 0, drag); setOrder(o); setDrag(null); }}
                  className={clsx("flex items-center gap-2 rounded px-2 py-1.5 text-sm", drag === id ? "bg-surface" : "hover:bg-surface", c.locked && "opacity-50")}>
                  <GripVertical size={14} className={clsx("text-ink3", !c.locked && "cursor-grab")} />
                  <span className={clsx("flex-1", on ? "text-ink" : "text-ink3")}>{c.label}</span>
                  {!c.locked && <button className="btn-icon h-6 w-6" aria-label={on ? `Hide ${c.label}` : `Show ${c.label}`} onClick={() => setVisible({ ...visible, [id]: !on })}>{on ? <Eye size={14} /> : <EyeOff size={14} />}</button>}
                </li>
              );
            })}
          </ul>
          <div className="px-2 py-1.5 text-xs text-ink3">Drag to reorder. Saved in this browser.</div>
        </div>
      )}
    </Popover>
  );
}
