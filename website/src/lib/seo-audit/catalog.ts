import { PAGE_CHECKS } from "./checks";
import type { Category, Check, Severity } from "./types";

/** Site-wide checks are generated from what the crawl found, so the list of
 *  them is written out here for the page that documents the tool. */
const SITE_CHECKS: Check[] = [
  {
    id: "robots-missing",
    label: "robots.txt missing or unreadable",
    severity: "medium",
    category: "crawlability",
    why: "An unreadable robots.txt is worse than an absent one — Google may stop crawling rather than guess what it was allowed to fetch.",
    fix: "Serve a valid robots.txt, or a clean 404.",
  },
  {
    id: "robots-blocks-assets",
    label: "robots.txt blocks CSS, JavaScript or images",
    severity: "high",
    category: "crawlability",
    why: "Google renders pages like a browser. Blocked assets mean it sees a broken version of every page.",
    fix: "Let crawlers fetch the assets even where the pages are disallowed.",
  },
  {
    id: "robots-no-sitemap",
    label: "robots.txt names no sitemap",
    severity: "medium",
    category: "crawlability",
    why: "A Sitemap: line is the one place every crawler looks for the list of pages worth reading.",
    fix: "Add the absolute sitemap URL to robots.txt.",
  },
  {
    id: "sitemap-missing",
    label: "No XML sitemap found",
    severity: "high",
    category: "crawlability",
    why: "Without one, discovery depends entirely on links, and nothing states which URLs you consider worth indexing.",
    fix: "Publish a sitemap and name it in robots.txt.",
  },
  {
    id: "sitemap-not-at-standard-url",
    label: "Sitemap not served at /sitemap.xml",
    severity: "low",
    category: "crawlability",
    why: "It is the first location guessed by anything pointed at a bare domain.",
    fix: "Serve the sitemap or sitemap index at /sitemap.xml as well.",
  },
  {
    id: "http-not-redirected",
    label: "http:// does not redirect to https://",
    severity: "high",
    category: "indexability",
    why: "Every page exists twice as far as a crawler is concerned, and links split between the two.",
    fix: "301 every http:// URL to its https:// equivalent.",
  },
  {
    id: "host-variant-duplicate",
    label: "www and non-www both serve the site",
    severity: "high",
    category: "indexability",
    why: "They are separate sites unless one redirects to the other, so every page is duplicated across two hosts.",
    fix: "Pick one host and 301 the other to it.",
  },
  {
    id: "ai-search-crawler-blocked",
    label: "AI search crawlers blocked in robots.txt",
    severity: "high",
    category: "ai-crawlers",
    why: "OAI-SearchBot, Claude-SearchBot and PerplexityBot build the indexes those assistants answer from. Blocked, the site cannot be cited at all.",
    fix: "Allow the search agents, and block only the training agents if that is the concern.",
  },
  {
    id: "ai-user-fetch-blocked",
    label: "AI assistants cannot fetch a page on request",
    severity: "medium",
    category: "ai-crawlers",
    why: "ChatGPT-User, Claude-User and Perplexity-User fetch a page only when a reader pastes the link and asks about it.",
    fix: "Allow the user-triggered agents unless there is a reason to stop a reader handing your page to an assistant.",
  },
  {
    id: "ai-training-blocked",
    label: "AI training crawlers blocked",
    severity: "low",
    category: "ai-crawlers",
    why: "Reported so the record is complete. This is usually a deliberate choice rather than a fault.",
    fix: "Nothing to do if it was intended.",
  },
  {
    id: "llms-missing",
    label: "No /llms.txt",
    severity: "low",
    category: "ai-crawlers",
    why: "A young convention, not a standard. It gives a model fetching your domain a summary written by you.",
    fix: "Publish a short markdown file at /llms.txt if the rest of the site is already in order.",
  },
];

export type CatalogEntry = Check & { scope: "page" | "site" };

export const CHECK_CATALOG: CatalogEntry[] = [
  ...PAGE_CHECKS.map(({ id, label, severity, category, why, fix }) => ({
    id,
    label,
    severity,
    category,
    why,
    fix,
    scope: "page" as const,
  })),
  ...SITE_CHECKS.map((check) => ({ ...check, scope: "site" as const })),
];

export const CHECK_TOTAL = CHECK_CATALOG.length;

export const CATEGORY_ORDER: Category[] = [
  "crawlability",
  "indexability",
  "metadata",
  "content",
  "structured-data",
  "links",
  "urls",
  "international",
  "mobile",
  "ai-crawlers",
];

export function catalogByCategory(): Array<{
  category: Category;
  checks: CatalogEntry[];
}> {
  const severityRank: Record<Severity, number> = {
    critical: 0,
    high: 1,
    medium: 2,
    low: 3,
  };
  return CATEGORY_ORDER.map((category) => ({
    category,
    checks: CHECK_CATALOG.filter((check) => check.category === category).sort(
      (a, b) => severityRank[a.severity] - severityRank[b.severity],
    ),
  })).filter((group) => group.checks.length > 0);
}
