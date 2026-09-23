import { flexRender, getCoreRowModel, useReactTable, type ColumnDef as TColumnDef, type VisibilityState } from "@tanstack/react-table";
import clsx from "clsx";
import { ArrowDown, ArrowUp } from "lucide-react";
import { useMemo } from "react";
import type { Lead } from "../types";
import { FLAG_LABEL, STATUS_LABEL, fitConfidence, money, num } from "../lib/format";
import { QuadrantMark, ReachIcons, Score } from "./bits";
import type { ColumnDef } from "./ColumnBuilder";

export const COLUMNS: ColumnDef[] = [
  { id: "select", label: "Select", locked: true },
  { id: "quadrant", label: "Quadrant" }, { id: "company", label: "Company" }, { id: "fit", label: "Fit" }, { id: "exit", label: "Exit-readiness" },
  { id: "revenue", label: "Revenue" }, { id: "employees", label: "Employees" }, { id: "founded", label: "Founded" }, { id: "location", label: "Location" },
  { id: "industry", label: "Industry" }, { id: "reach", label: "Reach" }, { id: "intel", label: "Web Intel" }, { id: "quality", label: "Data quality" },
  { id: "owner", label: "Owner" }, { id: "business_type", label: "Business type" }, { id: "category", label: "Category" }, { id: "bbb", label: "BBB rating" },
  { id: "flags", label: "Flags" }, { id: "email", label: "Email" }, { id: "phone", label: "Phone" }, { id: "website", label: "Website" }, { id: "source", label: "Source" },
];

const SORT_KEY: Record<string, string> = { fit: "fit_score", exit: "exit_score", quality: "quality_score", company: "company", revenue: "revenue_usd", employees: "employees", founded: "year_founded", location: "state", industry: "industry" };
const cell = (v: string | number | null | undefined) => (v == null || v === "" ? <span className="text-ink3">—</span> : <span className="text-ink2">{v}</span>);

export function LeadTable({ leads, selected, setSelected, onOpen, order, visible, sort, setSort, highlight, loading }: {
  leads: Lead[]; selected: Set<number>; setSelected: (s: Set<number>) => void; onOpen: (id: number) => void;
  order: string[]; visible: Record<string, boolean>; sort: { id: string; desc: boolean }; setSort: (s: { id: string; desc: boolean }) => void;
  highlight: Set<number> | null; loading: boolean;
}) {
  const allSelected = leads.length > 0 && leads.every((l) => selected.has(l.id));
  const columns = useMemo<TColumnDef<Lead>[]>(() => [
    { id: "select", header: () => <input type="checkbox" aria-label="Select all on this page" checked={allSelected} onChange={() => setSelected(allSelected ? new Set() : new Set(leads.map((l) => l.id)))} />,
      cell: ({ row }) => <input type="checkbox" aria-label={`Select ${row.original.company}`} checked={selected.has(row.original.id)} onClick={(e) => e.stopPropagation()} onChange={() => { const s = new Set(selected); s.has(row.original.id) ? s.delete(row.original.id) : s.add(row.original.id); setSelected(s); }} /> },
    { id: "quadrant", header: "Quadrant", cell: ({ row }) => <QuadrantMark q={row.original.quadrant} /> },
    { id: "company", header: "Company", cell: ({ row }) => (
      <div className="min-w-0">
        <div className="flex items-center gap-2 truncate font-medium text-ink">{row.original.company}{row.original.merged_from.length > 1 && <span className="kbd" title={`Merged from ${row.original.merged_from.length} export rows`}>×{row.original.merged_from.length}</span>}</div>
        <div className="truncate text-xs text-ink3">{row.original.domain ?? "no website"}</div>
      </div>) },
    { id: "fit", header: "Fit", cell: ({ row }) => <Score value={row.original.fit_score} grade={row.original.fit_grade} confidence={fitConfidence(row.original.fit_breakdown)} /> },
    { id: "exit", header: "Exit", cell: ({ row }) => <Score value={row.original.exit_score} /> },
    { id: "revenue", header: "Revenue", cell: ({ row }) => <span className="tabular-nums">{cell(row.original.revenue_usd == null ? null : money(row.original.revenue_usd))}</span> },
    { id: "employees", header: "Employees", cell: ({ row }) => <span className="tabular-nums">{cell(row.original.employees == null ? null : num(row.original.employees))}</span> },
    { id: "founded", header: "Founded", cell: ({ row }) => <span className="tabular-nums">{cell(row.original.year_founded)}</span> },
    { id: "location", header: "Location", cell: ({ row }) => cell([row.original.city, row.original.state].filter(Boolean).join(", ")) },
    { id: "industry", header: "Industry", cell: ({ row }) => cell(row.original.industry) },
    { id: "reach", header: "Reach", cell: ({ row }) => <ReachIcons l={row.original} /> },
    { id: "intel", header: "Web Intel", cell: ({ row }) => {
      const s = row.original.fetch_status; const ai = row.original.web_intel?.llm?._provider?.startsWith("gemini");
      if (!s) return <span className="text-sm text-ink3">Not checked</span>;
      if (s === "ok") return <span className="inline-flex items-center gap-1.5 text-sm text-ink2"><span className="h-1.5 w-1.5 rounded-full bg-success" />Checked{ai ? " · AI" : ""}</span>;
      return <span className="inline-flex items-center gap-1.5 text-sm text-ink2"><span className="h-1.5 w-1.5 rounded-full bg-amber" />{STATUS_LABEL[s] ?? s}</span>;
    } },
    { id: "quality", header: "Quality", cell: ({ row }) => <Score value={row.original.quality_score} /> },
    { id: "owner", header: "Owner", cell: ({ row }) => row.original.owner_name ? <div><div className="text-ink">{row.original.owner_name}</div><div className="text-xs text-ink3">{row.original.owner_title ?? ""}</div></div> : cell(null) },
    { id: "business_type", header: "Type", cell: ({ row }) => cell(row.original.business_type) },
    { id: "category", header: "Category", cell: ({ row }) => <span className="block max-w-[240px] truncate" title={row.original.category ?? ""}>{cell(row.original.category)}</span> },
    { id: "bbb", header: "BBB", cell: ({ row }) => cell(row.original.bbb_rating) },
    { id: "flags", header: "Flags", cell: ({ row }) => { const fl = row.original.flags.filter((f) => f !== "merged_duplicate"); return fl.length ? <span className="text-sm text-amber" title={fl.map((f) => FLAG_LABEL[f] ?? f).join("\n")}>{fl.length} note{fl.length > 1 ? "s" : ""}</span> : <span className="text-sm text-ink3">clean</span>; } },
    { id: "email", header: "Email", cell: ({ row }) => cell(row.original.email) },
    { id: "phone", header: "Phone", cell: ({ row }) => <span className="tabular-nums">{cell(row.original.phone)}</span> },
    { id: "website", header: "Website", cell: ({ row }) => row.original.website ? <a className="focusable text-ink2 underline decoration-lineStrong underline-offset-2 hover:text-ink" href={row.original.website} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>{row.original.domain}</a> : cell(null) },
    { id: "source", header: "Source", cell: ({ row }) => cell(row.original.source) },
  ], [leads, selected, allSelected, setSelected]);

  const columnVisibility: VisibilityState = Object.fromEntries(COLUMNS.map((c) => [c.id, c.locked || visible[c.id] !== false]));
  const columnOrder = ["select", ...order.filter((id) => id !== "select")];
  const table = useReactTable({ data: leads, columns, getCoreRowModel: getCoreRowModel(), state: { columnVisibility, columnOrder } });
  const stickyHead = (id: string) => (id === "select" ? "sticky left-0 z-20" : id === "company" ? "sticky left-10 z-20" : "");
  const stickyCell = (id: string) => (id === "select" ? "sticky left-0 z-10 bg-surface" : id === "company" ? "sticky left-10 z-10 bg-surface" : "");

  return (
    <div className="overflow-auto">
      <table className="w-full border-separate border-spacing-0">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => {
                const sk = SORT_KEY[h.column.id]; const active = sort.id === sk;
                return (
                  <th key={h.id} aria-sort={active ? (sort.desc ? "descending" : "ascending") : undefined} className={clsx("th", stickyHead(h.column.id), h.column.id === "select" && "w-10", sk && "cursor-pointer select-none hover:text-ink")} onClick={() => sk && setSort({ id: sk, desc: active ? !sort.desc : true })}>
                    <span className="inline-flex items-center gap-1">{flexRender(h.column.columnDef.header, h.getContext())}{active && (sort.desc ? <ArrowDown size={12} /> : <ArrowUp size={12} />)}</span>
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody className={clsx("transition-opacity duration-150", loading && "opacity-50")}>
          {loading && leads.length === 0 && [0, 1, 2, 3, 4, 5].map((i) => (
            <tr key={`sk-${i}`}>{[0, 1, 2, 3, 4].map((j) => <td key={j} className="td"><span className={clsx("skeleton block h-3", j === 1 ? "w-40" : "w-16")} /></td>)}</tr>
          ))}
          {table.getRowModel().rows.map((row) => {
            const hl = highlight?.has(row.original.id);
            return (
              <tr key={row.id} onClick={() => onOpen(row.original.id)} className={clsx("group cursor-pointer", highlight && !hl && "opacity-40")}>
                {row.getVisibleCells().map((c) => (
                  <td key={c.id} className={clsx("td transition-colors duration-150 group-hover:bg-surface2/60", stickyCell(c.column.id), selected.has(row.original.id) && "bg-accent/[0.06]", hl && "bg-accent/[0.06]")}>{flexRender(c.column.columnDef.cell, c.getContext())}</td>
                ))}
              </tr>
            );
          })}
          {leads.length === 0 && !loading && <tr><td colSpan={99} className="px-4 py-14 text-center text-sm text-ink2">No companies match these filters.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
