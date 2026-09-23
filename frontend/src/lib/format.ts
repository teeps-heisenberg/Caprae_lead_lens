import type { Quadrant } from "../types";

export const money = (v: number | null | undefined): string => {
  if (v == null) return "—";
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `$${Math.round(v / 1e3)}K`;
  return `$${v}`;
};

export const num = (v: number | null | undefined): string => (v == null ? "—" : v.toLocaleString());

// Categorical colors for the five quadrants. Call first shares the accent hue on purpose: the accent means "act".
// Needs Web Intel is drawn hollow so it is distinguishable from Skip without relying on hue alone.
// `color` is the solid (dots, text), `soft` the chip background. All text-on-soft pairs clear 4.5:1.
export const QUADRANT: Record<Quadrant, { label: string; color: string; soft: string; hollow?: boolean; hint: string }> = {
  call_first: { label: "Call first", color: "oklch(0.50 0.19 345)", soft: "oklch(0.95 0.035 345)", hint: "Good business, owner likely open to selling" },
  enrich_later: { label: "Enrich later", color: "oklch(0.48 0.16 250)", soft: "oklch(0.95 0.03 250)", hint: "Good business, no exit signal yet" },
  unscored: { label: "Needs Web Intel", color: "oklch(0.45 0.02 345)", soft: "oklch(0.965 0.004 345)", hollow: true, hint: "Too little data in the export to judge. Run Web Intel." },
  nurture: { label: "Nurture", color: "oklch(0.52 0.14 70)", soft: "oklch(0.96 0.045 85)", hint: "Exit signals, but weak fit" },
  skip: { label: "Skip", color: "oklch(0.50 0.01 345)", soft: "oklch(0.955 0.004 345)", hint: "Neither fit nor exit signal" },
};
export const QUADRANT_ORDER: Quadrant[] = ["call_first", "enrich_later", "unscored", "nurture", "skip"];

export const FLAG_LABEL: Record<string, string> = {
  revenue_suspect: "Revenue value looks wrong", revenue_unparseable: "Revenue not parseable", revenue_range_midpoint: "Revenue was a range (midpoint used)",
  employees_fractional: "Fractional headcount (rounded)", employees_range_midpoint: "Headcount was a range (midpoint used)", employees_unparseable: "Headcount not parseable",
  year_unparseable: "Founding year not parseable", year_out_of_range: "Founding year impossible", website_invalid: "Website not a valid URL",
  email_invalid: "Email malformed", email_disposable: "Disposable email", email_freemail: "Free-mail address, not a company inbox", email_domain_mismatch: "Email domain differs from website",
  phone_invalid: "Phone invalid", phone_unverified: "Phone possible but unverified", state_unrecognised: "State not a US state", linkedin_invalid: "LinkedIn URL invalid",
  company_missing: "Company name missing", merged_duplicate: "Merged from duplicate rows",
  year_from_website: "Founding year found on website", year_from_wayback: "Founding year estimated from first web archive",
  owner_from_website: "Owner name found on website", email_is_owner_direct: "Email is the owner's direct address", phone_is_owner_direct: "Phone is the owner's direct line",
  phone_from_website: "Phone found on website", email_from_website: "Email found on website",
};

export const STATUS_LABEL: Record<string, string> = {
  ok: "Checked", thin: "Needs browser rendering", no_site: "No website", timeout: "Timed out", blocked: "Blocked", error: "Fetch error", fixture_missing: "Unreachable",
};

export const fitConfidence = (bd: { confidence?: number }[]): number => bd.find((b) => b.confidence != null)?.confidence ?? 100;

// Score emphasis: strong scores are brighter, weak ones recede. Never a rainbow.
// Strong scores read green (a good state), middling ones plain, weak ones recede. No rainbow.
export const scoreTint = (v: number): string => (v >= 80 ? "text-success" : v >= 62 ? "text-ink" : v >= 40 ? "text-ink2" : "text-ink3");
export const scoreWeight = (v: number): string => (v >= 80 ? "font-semibold" : "font-medium");
