export type LinkState =
  | "ok"
  | "broken"
  | "redirect"
  | "blocked"
  | "no-answer"
  | "unchecked";

export type LinkSource = {
  page: string;
  anchor: string;
  rel: string | null;
};

export type CheckedLink = {
  url: string;
  state: LinkState;
  status: number | null;
  /** Plain-language reason, e.g. "HTTP 404 — page not found". */
  reason: string;
  side: "internal" | "external";
  asset: "link" | "image";
  redirectTo: string | null;
  redirectHops: number;
  responseMs: number | null;
  /** Capped at a handful; sourceCount holds the real number. */
  sources: LinkSource[];
  sourceCount: number;
};

export type LinkCheckSummary = {
  pagesCrawled: number;
  linksFound: number;
  linksChecked: number;
  uncheckedCount: number;
  broken: number;
  redirects: number;
  blocked: number;
  noAnswer: number;
  ok: number;
  brokenInternal: number;
  brokenExternal: number;
  brokenImages: number;
  durationMs: number;
  limitReached: boolean;
};

export type LinkCheckResult = {
  input: string;
  origin: string;
  scope: "site" | "sitemap" | "page";
  startedAt: string;
  summary: LinkCheckSummary;
  links: CheckedLink[];
  /** One row per crawled page, so a visitor can see where the rot is. */
  pages: Array<{
    url: string;
    status: number | null;
    linksOut: number;
    broken: number;
  }>;
  notes: string[];
};
