import type { BadgeTone } from "@demo/components/ui";
import { apiPaged } from "@demo/lib/use-api";
import type {
  SocialListeningPost,
  SocialListeningQuery,
  SocialListeningReviewStatus,
} from "@demo/lib/types";

export interface PlatformInfo {
  id: string;
  label: string;
  access: "direct" | "apify";
  available: boolean;
}

export type TabKey = "to_reply" | "drafted" | "done";

export const TAB_STATUSES: Record<TabKey, SocialListeningReviewStatus[]> = {
  to_reply: ["to_reply"],
  drafted: ["drafted"],
  done: ["replied", "skipped", "rejected"],
};

export const OUTCOME: Partial<Record<SocialListeningReviewStatus, { label: string; tone: BadgeTone }>> = {
  replied: { label: "Replied", tone: "good" },
  skipped: { label: "Skipped", tone: "neutral" },
  rejected: { label: "Not relevant", tone: "warn" },
};

export type RunStep = "terms" | "searching" | "meaning" | "judging";

export interface LiveRun {
  step: RunStep | null;
  lines: number;
  phrases: number;
  platforms: Record<
    string,
    { status: "fetching" | "done" | "error"; fromVendor?: number; fromDatabase?: number; error?: string }
  >;
  fetched: number;
  inserted: number;
  gate: { pending: number; kept: number; dropped: number } | null;
  judged: { judged: number; total: number; kept: number } | null;
  error: string | null;
}

export const EMPTY_LIVE: LiveRun = {
  step: null,
  lines: 0,
  phrases: 0,
  platforms: {},
  fetched: 0,
  inserted: 0,
  gate: null,
  judged: null,
  error: null,
};

const STEPS: RunStep[] = ["terms", "searching", "meaning", "judging"];

export function liveAfter(prev: LiveRun, event: string, d: Record<string, unknown>): LiveRun {
  const n = (v: unknown) => Number(v ?? 0) || 0;
  if (event === "stage") {
    const step = String(d.stage) as RunStep;
    return STEPS.includes(step) ? { ...prev, step } : prev;
  }
  if (event === "terms") return { ...prev, lines: n(d.lines), phrases: n(d.phrases) };
  if (event === "platform") {
    return {
      ...prev,
      platforms: {
        ...prev.platforms,
        [String(d.platform)]: {
          status: d.status as "fetching" | "done" | "error",
          fromVendor: d.fromVendor as number | undefined,
          fromDatabase: d.fromDatabase as number | undefined,
          error: d.error as string | undefined,
        },
      },
    };
  }
  if (event === "saved") return { ...prev, fetched: n(d.fetched), inserted: n(d.inserted) };
  if (event === "gate") return { ...prev, gate: { pending: n(d.pending), kept: n(d.kept), dropped: n(d.dropped) } };
  if (event === "judged") return { ...prev, judged: { judged: n(d.judged), total: n(d.total), kept: n(d.kept) } };
  return prev;
}

export function postsPath(params: Record<string, string | number | null | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== "") q.set(k, String(v));
  }
  return `/api/v1/social-listening/posts?${q.toString()}`;
}

export function hoursAgo(iso: string | null | undefined): string {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const mins = Math.max(0, Math.round((Date.now() - t) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} h`;
  return `${Math.round(hours / 24)} d`;
}

const CSV_COLUMNS = [
  "url",
  "platform",
  "status",
  "title",
  "text",
  "authorHandle",
  "postedAt",
  "line",
  "similarity",
  "keepReason",
  "suggestedAngle",
  "replyText",
] as const;

function cell(value: unknown): string {
  const raw = value == null ? "" : String(value);
  const s = typeof value === "string" && /^[=+\-@\t\r]/.test(raw) ? `'${raw}` : raw;
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export async function downloadPostsCsv(queries: SocialListeningQuery[]): Promise<void> {
  const lineOf = new Map(queries.map((q) => [q.id, q.text]));
  const rows: SocialListeningPost[] = [];
  for (let page = 1; page <= 50; page += 1) {
    const res = await apiPaged<SocialListeningPost>(postsPath({ page, page_size: 200 }));
    rows.push(...res.data);
    if (!res.pagination.has_next) break;
  }
  const csv = [
    CSV_COLUMNS.join(","),
    ...rows.map((r) =>
      CSV_COLUMNS.map((c) => cell(c === "line" ? (r.queryId ? lineOf.get(r.queryId) : "") : r[c])).join(","),
    ),
  ].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "social-listening-posts.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}
