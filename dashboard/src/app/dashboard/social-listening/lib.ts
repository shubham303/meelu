import type { BadgeTone } from "@/components/ui";
import type { SocialListeningClass, SocialListeningInboxStatus } from "@/lib/types";

export interface PlatformInfo {
  id: string;
  label: string;
  access: "direct" | "apify";
  available: boolean;
}

export type PostSort = "best" | "newest" | "engaged";

export const INTENT_TONE: Record<string, BadgeTone> = {
  seeking_tool: "accent",
  seeking_help: "accent",
  complaining: "bad",
  recommending: "good",
  praising: "good",
};

export const INTENT_OPTIONS = [
  "seeking_tool",
  "seeking_help",
  "complaining",
  "recommending",
  "praising",
  "discussion",
  "other",
];

export const CLASS_LABEL: Record<SocialListeningClass, string> = {
  praise: "praise",
  complaint: "complaint",
  feature_request: "feature request",
  question: "question",
  switch_opportunity: "switch opportunity",
};

export const CLASS_TONE: Record<SocialListeningClass, BadgeTone> = {
  praise: "good",
  complaint: "bad",
  feature_request: "warn",
  question: "neutral",
  switch_opportunity: "accent",
};

export const STATUS_LABEL: Record<SocialListeningInboxStatus, string> = {
  needs_reply: "Needs reply",
  drafted: "Drafted",
  replied: "Replied",
  skipped: "Skipped",
};

export function sentimentTone(s: string | null): BadgeTone {
  return s === "positive" ? "good" : s === "negative" ? "bad" : "neutral";
}

export function postsQuery(params: Record<string, string | number | null | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== "") q.set(k, String(v));
  }
  return `/api/v1/social-listening/posts?${q.toString()}`;
}
