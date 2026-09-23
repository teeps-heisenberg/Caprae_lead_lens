import clsx from "clsx";
import { Globe, Linkedin, Mail, Phone } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Lead, Quadrant } from "../types";
import { QUADRANT, scoreTint, scoreWeight } from "../lib/format";

export function QuadrantDot({ q, size = 8 }: { q: Quadrant; size?: number }) {
  const c = QUADRANT[q];
  return <span className="inline-block shrink-0 rounded-full" style={{ width: size, height: size, background: c.hollow ? "transparent" : c.color, boxShadow: c.hollow ? `inset 0 0 0 1.5px ${c.color}` : undefined }} />;
}

/** Tinted chip: the quadrant is the one thing a user scans for, so it gets a real colored surface. */
export function QuadrantMark({ q, className }: { q: Quadrant; className?: string }) {
  const c = QUADRANT[q];
  return (
    <span className={clsx("inline-flex h-6 items-center gap-1.5 whitespace-nowrap rounded-full px-2 text-xs font-medium", className)} style={{ background: c.soft, color: c.color }} title={c.hint}>
      <QuadrantDot q={q} size={7} />{c.label}
    </span>
  );
}

export function Score({ value, grade, confidence }: { value: number; grade?: string; confidence?: number }) {
  return (
    <span className="inline-flex items-baseline gap-1.5 tabular-nums">
      <span className={clsx("text-[15px]", scoreTint(value), scoreWeight(value))}>{value}</span>
      {grade && <span className="text-xs text-ink3">{grade}</span>}
      {confidence != null && confidence < 100 && (
        <span className="text-xs text-ink3" title={`Scored on ${confidence}% of the weights. The rest is unknown in this export.`}>·{confidence}%</span>
      )}
    </span>
  );
}

export function ReachIcons({ l }: { l: Lead }) {
  const item = (ok: boolean, Icon: typeof Mail, label: string) => (
    <span title={`${label}: ${ok ? "yes" : "missing"}`} className={ok ? "text-ink2" : "text-line-strong"}><Icon size={14} strokeWidth={1.75} /></span>
  );
  return <span className="inline-flex items-center gap-1.5">{item(!!l.email, Mail, "Email")}{item(!!l.phone, Phone, "Phone")}{item(!!l.linkedin, Linkedin, "LinkedIn")}{item(!!l.website, Globe, "Website")}</span>;
}

export function Spinner({ className }: { className?: string }) {
  return <span className={clsx("inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent opacity-70", className)} aria-label="Loading" />;
}

/** Anchored menu. Closes on outside click or Escape. */
export function Popover({ button, children, align = "left", width }: { button: (open: boolean) => ReactNode; children: (close: () => void) => ReactNode; align?: "left" | "right"; width?: number }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc); document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);
  return (
    <div ref={ref} className="relative">
      <div onClick={() => setOpen((o) => !o)}>{button(open)}</div>
      {open && <div className={clsx("menu", align === "right" ? "right-0" : "left-0")} style={width ? { width } : undefined}>{children(() => setOpen(false))}</div>}
    </div>
  );
}

export function PageHeader({ title, description, children }: { title: string; description?: string; children?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-lg font-semibold text-ink">{title}</h1>
        {description && <p className="mt-0.5 text-sm text-ink2">{description}</p>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  );
}
