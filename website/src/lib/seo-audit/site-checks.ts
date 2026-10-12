import type { AiCrawlerVerdict, Check, Robots } from "./types";
import { disallowsAssets, sitemapsIn } from "./robots";
import { STANDARD_SITEMAP_PATH } from "./sitemap";

export type SiteFinding = Check & { detail: string };

export type SiteInput = {
  origin: string;
  robots: Robots;
  llmsStatus: number | null;
  sitemapsUsed: string[];
  sitemapUrlCount: number;
  sitemapAtRoot: boolean;
  aiCrawlers: AiCrawlerVerdict[];
  /** Null when the variant was not probed. */
  httpRedirects: boolean | null;
  hostVariantRedirects: boolean | null;
  hostVariantUrl: string | null;
};

export function siteFindings(input: SiteInput): SiteFinding[] {
  const {
    origin,
    robots,
    llmsStatus,
    sitemapsUsed,
    sitemapUrlCount,
    sitemapAtRoot,
    aiCrawlers,
    httpRedirects,
    hostVariantRedirects,
    hostVariantUrl,
  } = input;

  const out: SiteFinding[] = [];
  const body = robots.body ?? "";
  const add = (check: Check, detail: string) => out.push({ ...check, detail });

  if (robots.fetched && (robots.status === 404 || robots.status === 410)) {
    add(
      {
        id: "robots-missing",
        label: "No robots.txt",
        severity: "low",
        category: "crawlability",
        why: "Not a problem on its own — a site that wants everything crawled needs no file. It does mean there is nowhere to point a crawler at the sitemap, and nowhere to keep one out of an admin path.",
        fix: `Publish ${origin}/robots.txt with a Sitemap: line at minimum.`,
      },
      `HTTP ${robots.status} at ${origin}/robots.txt`,
    );
  }

  if (robots.fetched && robots.status !== null && ![200, 404, 410].includes(robots.status)) {
    add(
      {
        id: "robots-unreadable",
        label: "robots.txt could not be read",
        severity: "critical",
        category: "crawlability",
        why: "This is worse than not having one. Faced with an unreadable robots.txt, Google may stop crawling the site altogether rather than guess what it was allowed to fetch.",
        fix: "Fix the server, or return a clean 404.",
      },
      `HTTP ${robots.status} at ${origin}/robots.txt`,
    );
  }
  if (robots.error) {
    add(
      {
        id: "robots-unreadable",
        label: "robots.txt could not be read",
        severity: "critical",
        category: "crawlability",
        why: "Faced with an unreadable robots.txt, Google may stop crawling the site altogether rather than guess what it was allowed to fetch.",
        fix: "Fix the server, or return a clean 404.",
      },
      robots.error,
    );
  }

  if (robots.status === 200 && disallowsAssets(body)) {
    add(
      {
        id: "robots-blocks-assets",
        label: "robots.txt blocks CSS, JavaScript or images",
        severity: "high",
        category: "crawlability",
        why: "Google renders a page the way a browser does, so blocking the assets means it sees a broken version of every page that depends on them — most often judging the page mobile-unfriendly or thin.",
        fix: "Assets should be crawlable even when the pages using them are not.",
      },
      "a Disallow rule covers an asset path",
    );
  }

  if (robots.status === 200 && sitemapsIn(body).length === 0) {
    add(
      {
        id: "robots-no-sitemap",
        label: "robots.txt names no sitemap",
        severity: "medium",
        category: "crawlability",
        why: "A Sitemap: line is the one place every crawler looks for the list of pages worth reading, and the only route that does not depend on guessing a filename.",
        fix: `Add "Sitemap: ${origin}${STANDARD_SITEMAP_PATH}" to robots.txt.`,
      },
      "no Sitemap: directive",
    );
  }

  if (sitemapUrlCount === 0) {
    add(
      {
        id: "sitemap-missing",
        label: "No sitemap found",
        severity: "high",
        category: "crawlability",
        why: "Without one a crawler discovers pages only by following links, so anything the navigation does not reach may never be read, and nothing says which URLs are the ones worth indexing.",
        fix: `Publish a sitemap at ${origin}${STANDARD_SITEMAP_PATH} and name it in robots.txt.`,
      },
      "robots.txt named none and the usual locations returned none",
    );
  } else if (!sitemapAtRoot) {
    add(
      {
        id: "sitemap-not-at-standard-url",
        label: `Sitemap is not served at ${STANDARD_SITEMAP_PATH}`,
        severity: "low",
        category: "crawlability",
        why: `No specification requires that path, and a crawler told about the file in robots.txt finds it anywhere. What the root path buys is the case where nothing tells the crawler anything — it is the first location guessed by search engines, AI crawlers and link checkers, and the address a person types.`,
        fix: `Serve the sitemap, or a sitemap index naming the real files, at ${origin}${STANDARD_SITEMAP_PATH} as well. A redirect from there is enough.`,
      },
      `read from ${sitemapsUsed.slice(0, 3).join(", ")}`,
    );
  }

  if (llmsStatus === 404 || llmsStatus === 410) {
    add(
      {
        id: "llms-missing",
        label: "No /llms.txt",
        severity: "low",
        category: "ai-crawlers",
        why: "A young convention rather than a standard, and no assistant is known to require it — so this is the last thing to do, not the first. What it buys is control of the summary a model assembles when it fetches your domain.",
        fix: "Publish a short markdown file at /llms.txt naming what the site is and linking the pages worth reading.",
      },
      `HTTP ${llmsStatus} at ${origin}/llms.txt`,
    );
  }

  const blockedSearch = aiCrawlers.filter((c) => c.job === "search" && !c.allowed);
  if (blockedSearch.length > 0) {
    add(
      {
        id: "ai-search-crawler-blocked",
        label: "AI search crawlers are blocked in robots.txt",
        severity: "high",
        category: "ai-crawlers",
        why: "These are the crawlers that build the index ChatGPT, Claude and Perplexity answer from. Blocked, the site cannot be cited in those answers at all — this is separate from training, and blocking one does not require blocking the other.",
        fix: "Allow the search agents if you want to appear in AI answers, and block only the training agents if that is the concern.",
      },
      blockedSearch.map((c) => `${c.agent} (${c.operator})`).join(", "),
    );
  }

  const blockedFetch = aiCrawlers.filter((c) => c.job === "fetch" && !c.allowed);
  if (blockedFetch.length > 0) {
    add(
      {
        id: "ai-user-fetch-blocked",
        label: "AI assistants cannot fetch pages on request",
        severity: "medium",
        category: "ai-crawlers",
        why: "These agents fetch a page only when a person pastes the link and asks about it. Blocking them means a reader who brings your URL to an assistant is told the page cannot be read.",
        fix: "Allow the user-triggered agents unless there is a reason a reader should not be able to hand your page to an assistant.",
      },
      blockedFetch.map((c) => `${c.agent} (${c.operator})`).join(", "),
    );
  }

  const blockedTraining = aiCrawlers.filter((c) => c.job === "training" && !c.allowed);
  if (blockedTraining.length > 0 && blockedSearch.length === 0) {
    add(
      {
        id: "ai-training-blocked",
        label: "AI training crawlers are blocked (for information)",
        severity: "low",
        category: "ai-crawlers",
        why: "This is a deliberate choice rather than a fault, and it is listed so the record is complete. Search and fetch agents are still allowed, so the site can still be cited.",
        fix: "Nothing to do if this was intended.",
      },
      blockedTraining.map((c) => `${c.agent} (${c.operator})`).join(", "),
    );
  }

  if (httpRedirects === false) {
    add(
      {
        id: "http-not-redirected",
        label: "The http:// address does not redirect to https://",
        severity: "high",
        category: "indexability",
        why: "Two addresses serve the same pages, so every page on the site exists twice as far as a crawler is concerned, and links split between them.",
        fix: "Redirect every http:// URL to its https:// equivalent with a 301.",
      },
      `${origin.replace("https://", "http://")} answers without redirecting`,
    );
  }

  if (hostVariantRedirects === false && hostVariantUrl) {
    add(
      {
        id: "host-variant-duplicate",
        label: "www and non-www both serve the site",
        severity: "high",
        category: "indexability",
        why: "A www address and a bare one are separate sites unless one redirects to the other. Serving both duplicates every page and splits the links between two hosts.",
        fix: `Pick one host and 301 the other to it.`,
      },
      `${hostVariantUrl} answers without redirecting to ${origin}`,
    );
  }

  return out;
}
