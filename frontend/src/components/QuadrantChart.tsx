import { CartesianGrid, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import type { Stats } from "../types";
import { QUADRANT, QUADRANT_ORDER } from "../lib/format";
import { QuadrantDot } from "./bits";

export function QuadrantChart({ stats, thresholds, onPick, highlight, height = 220 }: {
  stats: Stats; thresholds: { fit: number; exit: number }; onPick: (id: number) => void; highlight: Set<number> | null; height?: number;
}) {
  const data = stats.points.map((p) => ({ ...p, x: p.fit, y: p.exit, on: !highlight || highlight.has(p.id) }));
  const groups = QUADRANT_ORDER.map((q) => ({ q, items: data.filter((d) => d.quadrant === q) }));
  const tick = { fill: "oklch(0.52 0.014 345)", fontSize: 11 };
  const axis = "oklch(0.85 0.006 345)";
  return (
    <div className="flex h-full flex-col">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <div className="text-sm font-medium text-ink">Acquisition fit <span className="text-ink3">×</span> exit-readiness</div>
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-ink2">
          {groups.map(({ q, items }) => <span key={q} className="inline-flex items-center gap-1.5"><QuadrantDot q={q} size={7} />{QUADRANT[q].label} <span className="text-ink3">{items.length}</span></span>)}
        </div>
      </div>
      <div className="flex-1" style={{ minHeight: height }}>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="oklch(0.93 0.004 345)" vertical={false} />
            <XAxis type="number" dataKey="x" domain={[0, 100]} tick={tick} stroke={axis} tickLine={false} ticks={[0, 25, 50, 75, 100]} />
            <YAxis type="number" dataKey="y" domain={[0, 100]} tick={tick} stroke={axis} tickLine={false} ticks={[0, 50, 100]} />
            <ReferenceLine x={thresholds.fit} stroke="oklch(0.72 0.01 345)" strokeDasharray="3 4" />
            <ReferenceLine y={thresholds.exit} stroke="oklch(0.72 0.01 345)" strokeDasharray="3 4" />
            <Tooltip cursor={false} content={({ payload }) => {
              const p = payload?.[0]?.payload as (typeof data)[number] | undefined;
              if (!p) return null;
              return (
                <div className="rounded-md border border-line bg-surface px-2.5 py-1.5 text-xs shadow-pop">
                  <div className="font-medium text-ink">{p.company}</div>
                  <div className="text-ink2">Fit {p.fit} · Exit {p.exit} · {QUADRANT[p.quadrant].label}</div>
                </div>
              );
            }} />
            {groups.map(({ q, items }) => (
              <Scatter key={q} data={items} onClick={(d) => onPick((d as unknown as { id: number }).id)} cursor="pointer"
                shape={(props: unknown) => {
                  const { cx, cy, payload } = props as { cx: number; cy: number; payload: { on: boolean } };
                  const c = QUADRANT[q];
                  return c.hollow
                    ? <circle cx={cx} cy={cy} r={3} fill="none" stroke={c.color} strokeWidth={1.5} strokeOpacity={payload.on ? 0.9 : 0.15} />
                    : <circle cx={cx} cy={cy} r={payload.on && highlight ? 4 : 3} fill={c.color} fillOpacity={payload.on ? 0.9 : 0.15} />;
                }} />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
