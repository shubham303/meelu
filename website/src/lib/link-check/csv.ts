import type { CheckedLink, LinkCheckResult } from "./types";

function cell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function toCsv(headers: string[], rows: unknown[][]): string {
  return [headers, ...rows].map((row) => row.map(cell).join(",")).join("\r\n");
}

const STATE_LABEL: Record<CheckedLink["state"], string> = {
  broken: "Broken",
  blocked: "Blocked / unverified",
  "no-answer": "No answer",
  redirect: "Redirect",
  ok: "OK",
  unchecked: "Not checked",
};

/** One row per source page, which is the shape you fix links in. */
function rowsFor(links: CheckedLink[]): unknown[][] {
  const rows: unknown[][] = [];
  for (const link of links) {
    if (link.sources.length === 0) {
      rows.push([
        STATE_LABEL[link.state],
        link.status,
        link.reason,
        link.url,
        link.side,
        link.asset,
        link.redirectTo,
        "",
        "",
        link.sourceCount,
      ]);
      continue;
    }
    for (const source of link.sources) {
      rows.push([
        STATE_LABEL[link.state],
        link.status,
        link.reason,
        link.url,
        link.side,
        link.asset,
        link.redirectTo,
        source.page,
        source.anchor,
        link.sourceCount,
      ]);
    }
  }
  return rows;
}

const HEADERS = [
  "Status",
  "HTTP code",
  "Reason",
  "Broken URL",
  "Internal or external",
  "Link or image",
  "Redirects to",
  "Found on page",
  "Anchor or alt text",
  "Times linked",
];

export function brokenLinksCsv(result: LinkCheckResult): string {
  const broken = result.links.filter(
    (l) => l.state === "broken" || l.state === "no-answer",
  );
  return toCsv(HEADERS, rowsFor(broken));
}

export function allLinksCsv(result: LinkCheckResult): string {
  return toCsv(HEADERS, rowsFor(result.links));
}

export function pagesCsv(result: LinkCheckResult): string {
  return toCsv(
    ["Page", "HTTP code", "Links and images out", "Broken links on the page"],
    result.pages.map((p) => [p.url, p.status, p.linksOut, p.broken]),
  );
}

export function fileStem(result: LinkCheckResult): string {
  let host = "site";
  try {
    host = new URL(result.origin).hostname.replace(/^www\./, "");
  } catch {
    // Keep the fallback.
  }
  return `broken-links-${host}-${result.startedAt.slice(0, 10)}`;
}
