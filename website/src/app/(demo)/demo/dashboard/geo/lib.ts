import type { BadgeTone } from "@demo/components/ui";
import type { GeoCheck, GeoIntent, GeoPlatform, GeoPointStatus, GeoQuery, GeoVerdict } from "@demo/lib/types";

export const VERDICT: Record<GeoVerdict, { label: string; tone: BadgeTone; hint: string }> = {
  no_page: {
    label: "No page",
    tone: "bad",
    hint: "Nothing on the site answers this question yet.",
  },
  partial: {
    label: "Partly answered",
    tone: "warn",
    hint: "A page comes close but misses part of what the question asks.",
  },
  low_rank: {
    label: "Answered, low rank",
    tone: "accent",
    hint: "The page answers fully, but it ranks below Google's first page, so AI search rarely finds it.",
  },
  covered: {
    label: "Covered",
    tone: "good",
    hint: "The page answers and ranks on Google's first page.",
  },
};

export const INTENT: Record<GeoIntent, string> = {
  informational: "Informational",
  commercial: "Commercial",
  transactional: "Transactional",
  navigational: "Navigational",
};

export const PLATFORM: Record<GeoPlatform, string> = {
  chat_gpt: "ChatGPT",
  claude: "Claude",
  ai_overview: "AI Overview",
};

export const POINT: Record<GeoPointStatus, { mark: string; className: string; label: string }> = {
  answers: { mark: "✓", className: "text-good", label: "Answered" },
  partly: { mark: "~", className: "text-warn", label: "Partly answered" },
  missing: { mark: "✕", className: "text-bad", label: "Missing" },
};

export function finishedCheck(q: GeoQuery): GeoCheck | undefined {
  const c = q.latestCheck;
  return c && c.status === "done" ? c : undefined;
}

export function isRunning(q: GeoQuery): boolean {
  return q.latestCheck?.status === "running";
}

export function citedBy(check: GeoCheck | undefined): string {
  const names = (check?.aiAnswers ?? []).filter((a) => a.citedUs).map((a) => PLATFORM[a.platform]);
  return names.length ? names.join(", ") : "—";
}

export function pathOf(url: string | undefined): string {
  if (!url) return "—";
  try {
    const u = new URL(url);
    return u.pathname + u.search || "/";
  } catch {
    return url;
  }
}
