import type { SiteIssueSummary, SuggestionSummary } from "@demo/lib/types";
import { activeSiteId } from "@demo/lib/current-site";
import * as search from "../data/search";
import * as siteData from "../data/site";
import { route } from "../api";
import { num, ok, type Route } from "../core";

function get<T>(path: string): T | null {
  const res = route("GET", path);
  if (res.status >= 400) return null;
  return ((res.payload as { data?: T } | null)?.data ?? null) as T | null;
}

function total(path: string): number {
  const res = route("GET", path);
  return (res.payload as { pagination?: { total?: number } } | null)?.pagination?.total ?? 0;
}

function stats() {
  const ledgerly = (activeSiteId() ?? siteData.SITE_ID) === siteData.SITE_ID;
  if (!ledgerly) {
    return {
      pages: 0,
      lastCrawlAt: null,
      contentPieces: 0,
      reports: 0,
      waiting: { structureSuggestions: 0, conversationsToReply: 0, leadsToMessage: 0, issuesOpen: 0 },
    };
  }
  const links = get<SuggestionSummary>("/api/v1/site/structure/link-suggestions/summary");
  const pillars = get<SuggestionSummary>("/api/v1/site/structure/pillar-suggestions/summary");
  const issues = get<SiteIssueSummary>("/api/v1/site/technical-seo/summary");
  const social = get<{ toReply: number }>("/api/v1/social-listening/summary");
  const leads = get<{ new: number }>("/api/v1/find-leads/summary");
  const pageStats = get<{ lastCrawledAt?: string | null }>("/api/v1/site/pages/stats");
  return {
    pages: siteData.PAGES.length,
    lastCrawlAt: pageStats?.lastCrawledAt ?? siteData.LAST_CRAWLED_AT,
    contentPieces: total("/api/v1/content/pieces?page=1&page_size=1"),
    reports: total("/api/v1/reports?page=1&page_size=1"),
    waiting: {
      structureSuggestions: (links?.reviewApproved ?? 0) + (pillars?.reviewApproved ?? 0),
      conversationsToReply: social?.toReply ?? 0,
      leadsToMessage: leads?.new ?? 0,
      issuesOpen: (issues?.site.open ?? 0) + (issues?.pages.open ?? 0),
    },
  };
}

const SLIPPING: Record<string, number> = {
  "/blog/quickbooks-alternatives": 1.34,
  "/templates/receipt": 1.22,
  "/blog/1099-nec-guide": 1.18,
};

function changes(days: number) {
  const movers = [...search.PAGE_SERIES.keys()].map((url) => {
    const clicks = search.totalsFor(url, days).clicks;
    const path = siteData.pathOf(url);
    const prevClicks = SLIPPING[path] ? Math.round(clicks * SLIPPING[path]) : search.totalsFor(url, days, days).clicks;
    return { kind: "page", key: url, clicks, prevClicks };
  });
  const delta = (m: (typeof movers)[number]) => m.clicks - m.prevClicks;
  return {
    hasData: true,
    lastDay: search.LAST_DAY,
    days,
    up: movers.filter((m) => delta(m) > 0).sort((a, c) => delta(c) - delta(a)).slice(0, 10),
    down: movers.filter((m) => delta(m) < 0).sort((a, c) => delta(a) - delta(c)).slice(0, 10),
  };
}

export const ROUTES: Route[] = [
  ["GET", /^\/api\/v1\/stats$/, () => ok(stats())],
  ["GET", /^\/api\/v1\/site\/search-data\/changes$/, (_m, q) => ok(changes(num(q.get("days")) ?? 28))],
];
