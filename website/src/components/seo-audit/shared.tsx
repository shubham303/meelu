import type { Category, Severity } from "@/lib/seo-audit/types";

export const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low"];

export const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

export const SEVERITY_CLASS: Record<Severity, string> = {
  critical: "border-bad/25 bg-bad/10 text-bad",
  high: "border-warn/25 bg-warn/10 text-warn",
  medium: "border-accent/25 bg-accent/10 text-accent",
  low: "border-edge2 bg-panel2 text-sub",
};

export const SEVERITY_DOT: Record<Severity, string> = {
  critical: "bg-bad",
  high: "bg-warn",
  medium: "bg-accent",
  low: "bg-faint",
};

export const CATEGORY_LABEL: Record<Category, string> = {
  crawlability: "Crawling & robots.txt",
  indexability: "Indexing & canonicals",
  metadata: "Titles & meta",
  content: "Content & headings",
  links: "Internal links",
  "structured-data": "Structured data",
  international: "hreflang & language",
  mobile: "Mobile & speed",
  urls: "URL structure",
  "ai-crawlers": "AI search access",
};

export function SeverityPill({
  severity,
  count,
}: {
  severity: Severity;
  count?: number;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[11px] font-medium ${SEVERITY_CLASS[severity]}`}
    >
      <span className={`size-1.5 rounded-full ${SEVERITY_DOT[severity]}`} />
      {SEVERITY_LABEL[severity]}
      {count !== undefined && <span className="tabular-nums">{count}</span>}
    </span>
  );
}

export function scoreTone(score: number): string {
  if (score >= 85) return "text-good";
  if (score >= 60) return "text-warn";
  return "text-bad";
}

export function shortUrl(url: string, origin: string): string {
  if (url.startsWith(origin)) {
    const rest = url.slice(origin.length);
    return rest === "" ? "/" : rest;
  }
  return url.replace(/^https?:\/\//, "");
}
