import type { Lead, LeadReviewStatus, LeadRun, LeadSource } from "@demo/lib/types";

export const MAX_BRIEFS = 10;
export const DISCARD_KEEP_DAYS = 30;

export const SOURCE_OPTIONS: Array<{ id: LeadSource; label: string; hint: string }> = [
  {
    id: "posts",
    label: "Post authors",
    hint: "People who recently posted about it on Reddit, X, LinkedIn, Bluesky, HN, GitHub or Dev.to",
  },
  {
    id: "linkedin",
    label: "LinkedIn people",
    hint: "Profiles that match the job titles and industries in your brief",
  },
  {
    id: "web",
    label: "Web search",
    hint: "Websites and directories; an email only when it is printed on the page",
  },
];

export const DEFAULT_SOURCES: LeadSource[] = ["posts", "linkedin"];

const PLATFORM_LABELS: Record<string, string> = {
  reddit: "Reddit",
  x: "X",
  linkedin: "LinkedIn",
  bluesky: "Bluesky",
  facebook: "Facebook",
  hackernews: "Hacker News",
  github: "GitHub",
  devto: "Dev.to",
  stackexchange: "Stack Exchange",
  web: "Web",
};

export function platformLabel(id: string): string {
  return PLATFORM_LABELS[id] ?? id;
}

export function sourceLabel(id: string): string {
  if (id === "linkedin") return "LinkedIn";
  if (id === "web") return "Web search";
  if (id.startsWith("posts:")) return `${platformLabel(id.slice(6))} posts`;
  return SOURCE_OPTIONS.find((s) => s.id === id)?.label ?? id;
}

export function chipLabel(id: LeadSource): string {
  return id === "posts" ? "Post authors" : id === "linkedin" ? "LinkedIn" : "Web";
}

export type RunStep = "plan" | "collect" | "screen" | "enrich" | "judge";

export const STEPS: RunStep[] = ["plan", "collect", "screen", "enrich", "judge"];

export interface SourceProgress {
  status: "running" | "done" | "error";
  candidates: number;
  fromVendor?: number;
  fromStore?: number;
  error?: string;
}

export interface RoundProgress {
  round: number;
  maxRounds: number;
  kept: number;
  target: number;
}

export interface LiveRun {
  round: RoundProgress | null;
  step: RunStep | null;
  briefs: number;
  searches: number;
  sources: Record<string, SourceProgress>;
  screened: { screened: number; total: number; kept: number } | null;
  enriched: { status: string; people: number; fromVendor: number; fromStore: number; error?: string } | null;
  judged: { judged: number; total: number; kept: number } | null;
  error: string | null;
}

export const EMPTY_LIVE: LiveRun = {
  round: null,
  step: null,
  briefs: 0,
  searches: 0,
  sources: {},
  screened: null,
  enriched: null,
  judged: null,
  error: null,
};

const n = (v: unknown) => Number(v ?? 0) || 0;

export function liveAfter(prev: LiveRun, event: string, d: Record<string, unknown>): LiveRun {
  if (event === "round") {
    return {
      ...EMPTY_LIVE,
      step: "collect",
      briefs: prev.briefs,
      searches: prev.searches,
      round: { round: n(d.round), maxRounds: n(d.maxRounds), kept: n(d.kept), target: n(d.target) },
    };
  }
  if (event === "stage") {
    const step = String(d.stage) as RunStep;
    return STEPS.includes(step) ? { ...prev, step } : prev;
  }
  if (event === "plan") return { ...prev, briefs: n(d.briefs), searches: n(d.searches) };
  if (event === "source") {
    const key = String(d.key ?? "");
    if (!key) return prev;
    return {
      ...prev,
      sources: {
        ...prev.sources,
        [key]: {
          status: (d.status as SourceProgress["status"]) ?? "running",
          candidates: n(d.candidates),
          fromVendor: d.fromVendor === undefined ? undefined : n(d.fromVendor),
          fromStore: d.fromStore === undefined ? undefined : n(d.fromStore),
          error: d.error ? String(d.error) : undefined,
        },
      },
    };
  }
  if (event === "screened") {
    return { ...prev, screened: { screened: n(d.screened), total: n(d.total), kept: n(d.kept) } };
  }
  if (event === "enriched") {
    return {
      ...prev,
      enriched: {
        status: String(d.status ?? "running"),
        people: n(d.people),
        fromVendor: n(d.fromVendor),
        fromStore: n(d.fromStore),
        error: d.error ? String(d.error) : undefined,
      },
    };
  }
  if (event === "judged") {
    return { ...prev, judged: { judged: n(d.judged), total: n(d.total), kept: n(d.kept) } };
  }
  return prev;
}

export interface SourceTotals {
  posts: number;
  postsStored: number;
  linkedin: number;
  web: number;
  running: boolean;
}

export function sourceTotals(stats: Record<string, { candidates?: number; fromStore?: number; status?: string }>): SourceTotals {
  const out: SourceTotals = { posts: 0, postsStored: 0, linkedin: 0, web: 0, running: false };
  for (const [key, s] of Object.entries(stats)) {
    if (s.status === "running") out.running = true;
    if (key.startsWith("posts:")) {
      out.posts += n(s.candidates);
      out.postsStored += n(s.fromStore);
    } else if (key === "linkedin") out.linkedin += n(s.candidates);
    else if (key === "web") out.web += n(s.candidates);
  }
  return out;
}

export function leadsPath(params: Record<string, string | number | null | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== "") q.set(k, String(v));
  }
  return `/api/v1/find-leads/leads?${q.toString()}`;
}

export function ago(iso: string | null | undefined): string {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const mins = Math.max(0, Math.round((Date.now() - t) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return days === 1 ? "yesterday" : `${days} days ago`;
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export function runStamp(run: LeadRun): string {
  const d = new Date(run.startedAt);
  if (Number.isNaN(d.getTime())) return "";
  return `${d.toLocaleDateString(undefined, { day: "numeric", month: "short" })}, ${d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`;
}

export function daysLeft(discardedAt: string | null): number | null {
  if (!discardedAt) return null;
  const t = new Date(discardedAt).getTime();
  if (Number.isNaN(t)) return null;
  const left = DISCARD_KEEP_DAYS - Math.floor((Date.now() - t) / 86_400_000);
  return Math.max(0, left);
}

export function contactLink(lead: Lead): { href: string; label: string } | null {
  if (lead.profileUrl) {
    return {
      href: lead.profileUrl,
      label: lead.platform === "web" ? "Open website" : `Open ${platformLabel(lead.platform)} profile`,
    };
  }
  const first = lead.evidence[0]?.url;
  return first ? { href: first, label: "Open post" } : null;
}

export function byline(lead: Lead): string {
  const bits: string[] = [platformLabel(lead.platform)];
  if (lead.handle) bits.push(lead.platform === "reddit" ? `u/${lead.handle}` : `@${lead.handle}`);
  else if (lead.source === "linkedin") bits.push("people search");
  const when = lead.evidence[0]?.at;
  if (when) bits.push(`posted ${ago(when)}`);
  return bits.join(" · ");
}

export const TAB_LABEL: Record<LeadReviewStatus, string> = {
  new: "New",
  contacted: "Contacted",
  discarded: "Discarded",
};
