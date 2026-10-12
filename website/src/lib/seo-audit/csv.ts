import type { Finding } from "./types";
import type { SlimPage, SlimResult } from "./audit";

function cell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = Array.isArray(value) ? value.join(" | ") : String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function toCsv(headers: string[], rows: unknown[][]): string {
  return [headers, ...rows].map((row) => row.map(cell).join(",")).join("\r\n");
}

export function issuesCsv(findings: Finding[]): string {
  return toCsv(
    ["Severity", "Check", "Category", "URL", "Detail", "Why it matters", "How to fix"],
    findings.map((f) => [
      f.severity,
      f.label,
      f.category,
      f.url ?? "(site-wide)",
      f.detail,
      f.why,
      f.fix,
    ]),
  );
}

export function pagesCsv(pages: SlimPage[]): string {
  return toCsv(
    [
      "URL",
      "Status",
      "State",
      "Response (ms)",
      "Size (bytes)",
      "Redirect hops",
      "Redirects to",
      "In sitemap",
      "Blocked by robots",
      "Depth",
      "Inlinks",
      "Page type",
      "Title",
      "Title length",
      "Title pixels",
      "Meta description",
      "Meta description length",
      "H1",
      "H1 count",
      "Word count",
      "Canonical",
      "Meta robots",
      "X-Robots-Tag",
      "Has viewport",
      "Lang",
      "Mixed content",
      "Open Graph",
      "Images",
      "Images missing alt",
      "Internal links out",
      "External links out",
      "Schema types",
      "Hreflang variants",
      "Fetch error",
    ],
    pages.map((p) => [
      p.url,
      p.status,
      p.state,
      p.responseMs,
      p.bytes,
      p.redirectHops,
      p.redirectTo,
      p.inSitemap,
      p.blockedByRobots,
      p.depth,
      p.inlinks,
      p.kind,
      p.title,
      p.title?.length ?? 0,
      p.titlePixels,
      p.metaDescription,
      p.metaDescription?.length ?? 0,
      p.h1[0] ?? "",
      p.h1.length,
      p.wordCount,
      p.canonical,
      p.robotsDirectives,
      p.xRobotsTag,
      p.hasViewport,
      p.lang,
      p.mixedContent,
      p.openGraph,
      p.imageCount,
      p.imagesMissingAlt,
      p.outLinkCount,
      p.externalLinkCount,
      p.schemaTypes,
      p.hreflangCount,
      p.fetchError,
    ]),
  );
}

export function summaryCsv(result: SlimResult): string {
  const byCheck = new Map<string, { label: string; severity: string; count: number }>();
  for (const f of result.findings) {
    const row = byCheck.get(f.id) ?? { label: f.label, severity: f.severity, count: 0 };
    row.count += 1;
    byCheck.set(f.id, row);
  }
  return toCsv(
    ["Check", "Severity", "Pages affected"],
    [...byCheck.values()]
      .sort((a, b) => b.count - a.count)
      .map((r) => [r.label, r.severity, r.count]),
  );
}

export function fileStem(result: SlimResult): string {
  const host = (() => {
    try {
      return new URL(result.origin).hostname.replace(/^www\./, "");
    } catch {
      return "site";
    }
  })();
  return `seo-audit-${host}-${result.startedAt.slice(0, 10)}`;
}
