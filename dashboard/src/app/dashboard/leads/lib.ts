import type { BadgeTone } from "@/components/ui";
import type { LeadStage } from "@/lib/types";

export interface SourceInfo {
  id: string;
  label: string;
  access: "free" | "apify";
  available: boolean;
}

export const SOURCE_IDS = [
  "web-search",
  "hackernews",
  "apify:reddit",
  "apify:youtube",
  "apify:linkedin",
  "apify:x",
  "apify:instagram",
] as const;

export const SOURCE_LABEL: Record<string, string> = {
  "web-search": "Web search",
  hackernews: "Hacker News",
  "apify:reddit": "Reddit",
  "apify:youtube": "YouTube",
  "apify:linkedin": "LinkedIn",
  "apify:x": "X",
  "apify:instagram": "Instagram",
};

export function sourceLabel(id: string | null): string {
  if (!id) return "manual";
  return SOURCE_LABEL[id] ?? id;
}

export function defaultSources(): SourceInfo[] {
  return SOURCE_IDS.map((id) => ({
    id,
    label: SOURCE_LABEL[id],
    access: id.startsWith("apify:") ? "apify" : "free",
    available: !id.startsWith("apify:"),
  }));
}

export const STAGES: LeadStage[] = ["found", "qualified", "shortlisted"];

export const STAGE_LABEL: Record<LeadStage, string> = {
  found: "Found",
  qualified: "Qualified",
  shortlisted: "Shortlisted",
};

export const STAGE_TONE: Record<LeadStage, BadgeTone> = {
  found: "neutral",
  qualified: "accent",
  shortlisted: "good",
};

export type LeadSort = "fit" | "newest";

export function leadsQuery(
  params: Record<string, string | number | boolean | null | undefined>,
): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== "") q.set(k, String(v));
  }
  return `/api/v1/lead-management/leads?${q.toString()}`;
}
