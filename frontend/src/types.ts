export type Quadrant = "call_first" | "enrich_later" | "unscored" | "nurture" | "skip";

export interface Breakdown { factor: string; points: number; max: number; reason: string; blend?: number; known?: boolean; confidence?: number }

export interface Judgement { value: boolean | null; evidence: string }

export interface LLMIntel {
  what_they_sell: string; business_model: string; industry_normalized: string;
  owner_operated: Judgement; independence: Judgement; succession_signals: string[];
  exit_assessment: number; exit_reasoning: string; analyst_note: string; outreach_angle: string;
  _provider?: string;
}

export interface Extracted {
  pages_read: string[]; title: string | null; meta_description: string | null;
  copyright_year: number | null; since_year: number | null; family_phrases: string[];
  acquisition_phrases: string[]; founder_mentions: string[]; has_careers_page: boolean; has_blog: boolean;
  emails_on_site: string[]; phones_on_site: string[]; social_links: Record<string, string>;
  tech_hints: string[]; wayback_first_year?: number | null; wayback_last_year?: number | null; mx_ok?: boolean | null;
}

export interface WebIntel { extracted: Extracted | Record<string, never>; llm: LLMIntel | null; status: string; from_cache: boolean; mode: string }

export interface Lead {
  id: number; dataset_id: number; company: string; domain: string | null; industry: string | null; category: string | null;
  business_type: string | null; employees: number | null; revenue_usd: number | null; year_founded: number | null;
  bbb_rating: string | null; street: string | null; city: string | null; state: string | null; website: string | null;
  linkedin: string | null; email: string | null; phone: string | null; owner_name: string | null; owner_title: string | null;
  parent_company: string | null; ownership_type: string | null;
  source: string | null; merged_from: number[]; conflicts: { field: string; chosen: unknown; options: { value: unknown; row: number }[] }[];
  flags: string[]; quality_score: number; fit_score: number; fit_grade: "A" | "B" | "C" | "D"; fit_breakdown: Breakdown[];
  exit_score: number; exit_breakdown: Breakdown[]; quadrant: Quadrant; web_intel: WebIntel | null;
  fetch_status: string | null; intel_at: string | null;
}

export interface Dataset { id: number; name: string; source: string; created_at: string; rows_in: number; rows_out: number; dup_clusters: number; rows_flagged: number; preset: string; weights: Record<string, unknown> }

export interface Stats {
  dataset: Dataset;
  funnel: { rows_in: number; rows_out: number; duplicates_removed: number; dup_clusters: number; rows_flagged: number; with_contact: number; intel_done: number; call_first: number };
  quadrants: Record<Quadrant, number>; grades: Record<string, number>;
  averages: { fit: number; exit: number; quality: number };
  filters: { states: string[]; industries: string[] };
  points: { id: number; company: string; fit: number; exit: number; quadrant: Quadrant }[];
}

export interface Job { id: number; dataset_id: number; kind: string; status: "queued" | "running" | "done" | "failed"; total: number; done: number; error: string | null }

export interface Meta {
  enrich_mode: "auto" | "fixture" | "live"; llm_provider: string;
  presets: Record<string, { label: string; description: string; fit: Record<string, number>; exit: Record<string, number> }>;
  thresholds: { fit: number; exit: number }; grades: Record<string, number>;
}

export interface OptimizeResult {
  credits: number;
  picks: { id: number; company: string; quadrant: Quadrant; fit_score: number; exit_score: number; missing: string[] }[];
  summary: { credits_used: number; credits_left: number; candidates_needing_credit: number; already_reachable_free: number; credits_avoided_low_value: number; credits_saved_by_dedupe: number; call_first_in_picks: number };
  free_calls: { id: number; company: string; quadrant: Quadrant }[];
}

export interface LeadFilters {
  quadrant: Quadrant[]; grade: string[]; state: string; industry: string; hasEmail: "" | "1" | "0"; hasPhone: "" | "1" | "0";
  intel: "" | "1" | "0"; q: string; minFit: number; minExit: number;
}

export const EMPTY_FILTERS: LeadFilters = { quadrant: [], grade: [], state: "", industry: "", hasEmail: "", hasPhone: "", intel: "", q: "", minFit: 0, minExit: 0 };
