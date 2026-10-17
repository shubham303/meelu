import type {
  BacklinkOpportunity,
  Competitor,
  CompetitorsChange,
  KeywordCluster,
  TrackedKeyword,
  TrackedOverview,
} from "@/app/(demo)/demo/dashboard/seo/types";
import * as search from "../data/search";
import * as seo from "../data/seo";
import * as siteData from "../data/site";
import * as traffic from "../data/traffic";
import { ago, DAY } from "../rand";
import { b, MockHttpError, newId, now, num, ok, paginate, slice, type Route } from "../core";

const MAX_COMPETITORS = 50;
const MAX_ITEMS_PER_CALL = 100;

const state = {
  gscProperty: siteData.SITE.gscProperty ?? null,
  gaProperty: siteData.SITE.gaProperty ?? null,
  clusters: seo.CLUSTERS.map((c) => ({ ...c })) as KeywordCluster[],
  competitors: seo.COMPETITOR_SEEDS.map((c, i): Competitor => ({
    id: `cmp_${i + 1}`,
    domain: c.domain,
    domainRank: seo.domainRankOf(c.domain),
    backlinksFetchedAt: c.fetchedDaysAgo === undefined ? undefined : ago(c.fetchedDaysAgo * DAY),
    createdAt: ago(c.addedDaysAgo * DAY),
    backlinks: c.backlinks,
  })),
  dismissed: new Set<string>(),
  tracked: new Map<string, TrackedKeyword[]>(),
  sync: {
    search: { active: null as SyncRecord | null, last: null as SyncRecord | null },
    traffic: { active: null as SyncRecord | null, last: null as SyncRecord | null },
  },
  inspected: new Map<string, string>(),
  indexCheckedAt: null as string | null,
};

interface SyncRecord {
  id: string;
  status: "running" | "completed" | "stopped";
  property: string | null;
  daysDone: number;
  daysTotal: number;
  rowsStored: number;
  startedAt: string;
  finishedAt: string | null;
}

export function syncEvent(event: string, data: Record<string, unknown>): void {
  const [kind, phase] = event.split(":");
  if (kind === "index") {
    if (phase === "done") state.indexCheckedAt = now();
    return;
  }
  if (kind !== "search" && kind !== "traffic") return;
  const slot = state.sync[kind];
  const id = String(data.syncId ?? "");
  if (phase === "started") {
    const property = typeof data.property === "string" ? data.property : null;
    if (property) {
      if (kind === "search") state.gscProperty = property;
      else state.gaProperty = property;
    }
    slot.active = { id, status: "running", property, daysDone: 0, daysTotal: Number(data.daysTotal) || 0, rowsStored: 0, startedAt: now(), finishedAt: null };
    return;
  }
  if (!slot.active || slot.active.id !== id) return;
  slot.active.daysDone = Number(data.daysDone) || slot.active.daysDone;
  slot.active.rowsStored = Number(data.rowsStored) || slot.active.rowsStored;
  if (phase === "done") {
    slot.last = { ...slot.active, status: data.stopped ? "stopped" : "completed", finishedAt: now() };
    slot.active = null;
  }
}

function bareUrl(url: string): string {
  return url.replace(/\/+$/, "");
}

export function inspectedUrl(url: string): void {
  state.inspected.set(bareUrl(url), now());
}

export function addKeywordClusters(source: string, topic: string | null): number {
  const added = seo.discoverClusters(source, topic, new Set(state.clusters.map((c) => c.mainKeyword)));
  const stamp = now();
  state.clusters.push(...added.map((c) => ({ ...c, createdAt: stamp, updatedAt: stamp })));
  return added.length;
}

export function trackKeywords(keywords: string[]): void {
  trackVolumes({ keywords });
}

export function competitorDomains(): string[] {
  return state.competitors.map((c) => c.domain);
}

export function opportunityDomains(): string[] {
  return opportunities().map((o) => o.domain);
}

function belongsTo(domain: string, owner: string): boolean {
  return domain === owner || domain.endsWith(`.${owner}`);
}

function withCompetitors(cluster: KeywordCluster): KeywordCluster {
  const serp = cluster.climb.map((r) => r.domain);
  return {
    ...cluster,
    competitors: competitorDomains().filter((c) => serp.some((d) => belongsTo(d, c))),
  };
}

function findCluster(id: string): KeywordCluster {
  const cluster = state.clusters.find((c) => c.id === id);
  if (!cluster) throw new MockHttpError(404, "No such keyword cluster on this website.");
  return cluster;
}

function bool(v: string | null): boolean | null {
  return v === "true" ? true : v === "false" ? false : null;
}

function listClusters(q: URLSearchParams) {
  let rows = [...state.clusters];
  const needle = q.get("search")?.trim().toLowerCase();
  if (needle) rows = rows.filter((c) => c.mainKeyword.includes(needle) || c.keywords.join(" ").includes(needle));
  const minVolume = num(q.get("minVolume"));
  if (minVolume !== null) rows = rows.filter((c) => c.volume >= minVolume);
  const scored = bool(q.get("scored"));
  if (scored !== null) rows = rows.filter((c) => (c.metricsAt !== undefined) === scored);
  const ranked = bool(q.get("ranked"));
  if (ranked !== null) rows = rows.filter((c) => c.isRanked === ranked);
  rows.sort(
    (a, c) =>
      (c.winnability ?? -1) - (a.winnability ?? -1) ||
      c.volume - a.volume ||
      a.mainKeyword.localeCompare(c.mainKeyword),
  );
  return paginate(rows.map(withCompetitors), q);
}

function rescore(id: string): KeywordCluster {
  const cluster = findCluster(id);
  const seed = seo.CLUSTER_SEEDS.get(id);
  if (!seed) throw new MockHttpError(404, "No such keyword cluster on this website.");
  const stamp = now();
  if (seed.verdict === "poisoned") {
    const cleared = { ...cluster, metricsAt: stamp, updatedAt: stamp };
    state.clusters = state.clusters.map((c) => (c.id === id ? cleared : c));
    return withCompetitors(cleared);
  }
  const scored = { ...cluster, ...seo.scoreCluster(seed), serpVerdict: seo.verdictOf({ ...seed, scoredDaysAgo: 0 }), metricsAt: stamp, updatedAt: stamp };
  if (scored.ourPosition !== undefined) scored.isRanked = true;
  state.clusters = state.clusters.map((c) => (c.id === id ? scored : c));
  return withCompetitors(scored);
}

function siteMarkets(): Array<{ locationCode: number; languageCode: string; country: string }> {
  const site = siteData.SITE as { markets?: string[]; language?: string | null };
  const language = site.language ?? "en";
  const countries = site.markets?.length ? site.markets : ["US", "GB"];
  return countries
    .filter((c) => seo.LOCATION_CODES[c] !== undefined)
    .map((country) => ({ locationCode: seo.LOCATION_CODES[country], languageCode: language, country }));
}

function trackedRows(country: string): TrackedKeyword[] {
  let rows = state.tracked.get(country);
  if (!rows) {
    rows = seo.trackedFor(country);
    state.tracked.set(country, rows);
  }
  return rows;
}

function trackedOverview(q: URLSearchParams): TrackedOverview {
  const markets = siteMarkets();
  const asked = num(q.get("locationCode"));
  const market = markets.find((m) => m.locationCode === asked) ?? markets[0];
  const keywords = [...trackedRows(market.country)].sort(
    (a, c) =>
      Number(a.position === undefined) - Number(c.position === undefined) ||
      (a.position ?? 0) - (c.position ?? 0) ||
      (c.volume ?? 0) - (a.volume ?? 0) ||
      a.keyword.localeCompare(c.keyword),
  );
  return {
    locationCode: market.locationCode,
    languageCode: market.languageCode,
    markets,
    months: seo.MONTHS,
    stats: {
      tracked: keywords.length,
      topTen: keywords.filter((k) => k.position !== undefined && k.position <= 10).length,
      moved: keywords.filter((k) => k.change).length,
      notRanking: keywords.filter((k) => k.position === undefined).length,
    },
    keywords,
  };
}

function normalizeKeyword(raw: unknown): string {
  return String(raw ?? "").toLowerCase().split(/\s+/).filter(Boolean).join(" ");
}

function trackVolumes(body: Record<string, unknown>) {
  const keywords = [...new Set((Array.isArray(b(body, "keywords")) ? (b(body, "keywords") as unknown[]) : []).map(normalizeKeyword))].filter(Boolean);
  if (!keywords.length) throw new MockHttpError(422, "Pass at least one keyword.");
  const markets = siteMarkets();
  const withoutData: string[] = [];
  let found = 0;
  for (const market of markets) {
    const rows = trackedRows(market.country);
    for (const keyword of keywords) {
      const cluster = state.clusters.find((c) => c.mainKeyword === keyword && c.country === market.country);
      const existing = rows.find((r) => r.keyword === keyword);
      if (!existing) rows.push(seo.newTrackedRow(keyword, cluster));
      if (market === markets[0]) {
        if (cluster || existing) found += 1;
        else if (keyword.split(" ").length > 6) withoutData.push(keyword);
        else found += 1;
      }
    }
  }
  return {
    keywords: keywords.length,
    months: seo.MONTHS.length,
    rows: found * markets.length * seo.MONTHS.length,
    withoutData,
  };
}

function cleanDomains(raw: unknown): string[] {
  const values = Array.isArray(raw) ? raw : [];
  if (!values.length) throw new MockHttpError(422, "Pass at least one domain.");
  if (values.length > MAX_ITEMS_PER_CALL) throw new MockHttpError(422, `At most ${MAX_ITEMS_PER_CALL} items per call.`);
  const cleaned = [
    ...new Set(
      values.map((v) =>
        String(v ?? "")
          .trim()
          .toLowerCase()
          .replace(/^[a-z]+:\/\//, "")
          .replace(/^www\./, "")
          .split(/[/?#]/)[0]
          .replace(/:\d+$/, ""),
      ),
    ),
  ].filter((d) => d.includes("."));
  if (!cleaned.length) throw new MockHttpError(422, "Pass at least one domain.");
  return cleaned;
}

function findCompetitor(id: string): Competitor {
  const competitor = state.competitors.find((c) => c.id === id);
  if (!competitor) throw new MockHttpError(404, "No such competitor on this website.");
  return competitor;
}

export function addCompetitors(domains: string[]): CompetitorsChange {
  const current = competitorDomains();
  const added = domains.filter((d) => !current.includes(d) && d !== siteData.SITE.domain);
  if (current.length + added.length > MAX_COMPETITORS) {
    throw new MockHttpError(409, `A website keeps at most ${MAX_COMPETITORS} competitors.`);
  }
  const stamp = now();
  state.competitors.push(
    ...added.map((domain): Competitor => ({ id: newId("cmp"), domain, domainRank: seo.domainRankOf(domain) ?? 300, createdAt: stamp, backlinks: 0 })),
  );
  return { added, removed: [], unchanged: domains.filter((d) => !added.includes(d)), competitors: competitorDomains() };
}

export function removeCompetitors(domains: string[]): CompetitorsChange {
  const current = competitorDomains();
  const removed = domains.filter((d) => current.includes(d));
  state.competitors = state.competitors.filter((c) => !removed.includes(c.domain));
  return { added: [], removed, unchanged: domains.filter((d) => !removed.includes(d)), competitors: competitorDomains() };
}

export function fetchBacklinks(domains: string[]) {
  const stamp = now();
  const fetched: Array<{ domain: string; backlinks: number }> = [];
  const notSaved: string[] = [];
  for (const domain of domains) {
    const competitor = state.competitors.find((c) => c.domain === domain);
    if (!competitor) {
      notSaved.push(domain);
      continue;
    }
    competitor.backlinks = competitor.backlinks || seo.backlinkCountFor(domain);
    competitor.backlinksFetchedAt = stamp;
    fetched.push({ domain, backlinks: competitor.backlinks });
  }
  return { fetched, notSaved };
}

function opportunities(): BacklinkOpportunity[] {
  const fetched = new Set(state.competitors.filter((c) => c.backlinksFetchedAt).map((c) => c.domain));
  return seo.opportunitiesFor(fetched, state.dismissed);
}

export function dismissOpportunities(domains: string[]) {
  const known = new Set(opportunities().map((o) => o.domain));
  const dismissed = domains.filter((d) => known.has(d));
  for (const d of dismissed) state.dismissed.add(d);
  return { dismissed, notFound: domains.filter((d) => !known.has(d)) };
}

function pageRowsSorted(days: number, q: URLSearchParams) {
  let rows = search.pageRows(days).map((r) => ({
    ...r,
    indexCheckedAt: state.inspected.get(bareUrl(r.page)) ?? state.indexCheckedAt ?? r.indexCheckedAt,
  }));
  const needle = q.get("search")?.toLowerCase();
  if (needle) rows = rows.filter((r) => r.page.toLowerCase().includes(needle));
  const sort = q.get("sort") ?? "clicks";
  const dir = q.get("dir") === "asc" ? 1 : -1;
  const key = (r: (typeof rows)[number]): number | string => {
    switch (sort) {
      case "page": return r.page;
      case "impressions": return r.impressions;
      case "ctr": return r.impressions ? r.clicks / r.impressions : 0;
      case "position": return r.position ?? 99;
      case "index": return r.indexState ?? "";
      case "crawled": return r.lastCrawlTime ?? "";
      case "inspected": return r.indexCheckedAt ?? "";
      default: return r.clicks;
    }
  };
  rows.sort((a, c) => {
    const ka = key(a);
    const kc = key(c);
    return (ka < kc ? -1 : ka > kc ? 1 : 0) * dir;
  });
  return rows;
}

function searchOverview() {
  return {
    connected: true,
    property: state.gscProperty,
    hasData: true,
    operatingBlind: false,
    firstDay: search.FIRST_DAY,
    lastDay: search.LAST_DAY,
    daysStored: search.DAYS_STORED,
    current: search.totalsFor(null, 28),
    previous: search.totalsFor(null, 28, 28),
    weeklyClicks: search.weeklyClicks(12),
    indexation: search.indexationCounts(),
    neverChecked: state.indexCheckedAt ? 0 : search.neverChecked(),
    googlePrefers: [
      {
        url: `${siteData.ORIGIN}/pricing/`,
        googleCanonical: `${siteData.ORIGIN}/pricing`,
        coverageState: "Duplicate, Google chose different canonical than user",
      },
      {
        url: `${siteData.ORIGIN}/old-pricing`,
        googleCanonical: `${siteData.ORIGIN}/pricing`,
        coverageState: "Duplicate, Google chose different canonical than user",
      },
    ],
    contentQualityVerdict: null,
    sync: state.sync.search.last,
    active: state.sync.search.active,
  };
}

function trafficOverview(q: URLSearchParams) {
  const days = num(q.get("days")) ?? 28;
  const organic = (shift: number) => {
    const c = traffic.channelTotals(days, shift)["Organic Search"];
    return { sessions: c.sessions, engagedSessions: c.engagedSessions, keyEvents: c.keyEvents, revenue: c.revenue };
  };
  return {
    connected: true,
    property: state.gaProperty,
    hasData: true,
    days,
    firstDay: traffic.TRAFFIC_FIRST_DAY,
    lastDay: traffic.TRAFFIC_LAST_DAY,
    daysStored: traffic.DAYS_STORED,
    totals: { current: traffic.totals(days), previous: traffic.totals(days, days) },
    organic: { current: organic(0), previous: organic(days) },
    channels: traffic.channelRows(days),
    sync: state.sync.traffic.last,
    active: state.sync.traffic.active,
  };
}

export const ROUTES: Route[] = [
  ["GET", /^\/api\/v1\/site\/seo\/competitors$/, () =>
    ok([...state.competitors].sort((a, c) => (c.domainRank ?? 0) - (a.domainRank ?? 0)))],
  ["POST", /^\/api\/v1\/site\/seo\/competitors$/, (_m, _q, body) => ok(addCompetitors(cleanDomains(b(body, "domains"))))],
  ["DELETE", /^\/api\/v1\/site\/seo\/competitors\/([^/]+)$/, (m) => {
    const competitor = findCompetitor(m[1]);
    state.competitors = state.competitors.filter((c) => c.id !== competitor.id);
    return ok(null);
  }],
  ["POST", /^\/api\/v1\/site\/seo\/backlinks\/fetch$/, (_m, _q, body) => ok(fetchBacklinks(cleanDomains(b(body, "domains"))))],
  ["GET", /^\/api\/v1\/site\/seo\/backlink-opportunities$/, (_m, q) => paginate(opportunities(), q)],
  ["POST", /^\/api\/v1\/site\/seo\/backlink-opportunities\/dismiss$/, (_m, _q, body) =>
    ok(dismissOpportunities(cleanDomains(b(body, "domains"))))],

  ["GET", /^\/api\/v1\/site\/seo\/clusters$/, (_m, q) => listClusters(q)],
  ["GET", /^\/api\/v1\/site\/seo\/clusters\/([^/]+)$/, (m) => ok(withCompetitors(findCluster(m[1])))],
  ["POST", /^\/api\/v1\/site\/seo\/clusters\/([^/]+)\/metrics$/, (m) => ok(rescore(m[1]))],
  ["DELETE", /^\/api\/v1\/site\/seo\/clusters\/([^/]+)$/, (m) => {
    findCluster(m[1]);
    state.clusters = state.clusters.filter((c) => c.id !== m[1]);
    return ok(null);
  }],

  ["GET", /^\/api\/v1\/site\/seo\/tracked$/, (_m, q) => ok(trackedOverview(q))],
  ["POST", /^\/api\/v1\/site\/seo\/tracked\/volumes$/, (_m, _q, body) => ok(trackVolumes(body))],

  ["GET", /^\/api\/v1\/site\/search-data$/, () => ok(searchOverview())],
  ["GET", /^\/api\/v1\/site\/search-data\/series$/, (_m, q) => {
    const days = num(q.get("days")) ?? 90;
    const pages = q.get("pages")?.split(",").filter(Boolean) ?? [];
    return ok({
      hasData: true,
      lastDay: search.LAST_DAY,
      days,
      series: pages.length
        ? pages.map((p) => ({ page: p, points: search.pointsFor(search.matchPage(p), days) }))
        : [{ page: null, points: search.pointsFor(null, days) }],
      current: search.totalsFor(pages.length ? pages.map(search.matchPage) : null, days),
      previous: search.totalsFor(pages.length ? pages.map(search.matchPage) : null, days, days),
    });
  }],
  ["GET", /^\/api\/v1\/site\/search-data\/pages$/, (_m, q) => {
    const rows = pageRowsSorted(num(q.get("days")) ?? 90, q);
    return ok({ rows: slice(rows, q), total: rows.length });
  }],
  ["GET", /^\/api\/v1\/site\/search-data\/queries$/, (_m, q) => {
    if (q.get("view") === "striking") {
      const rows = search.strikingRows(num(q.get("days")) ?? 28);
      return ok({ rows: slice(rows, q), total: rows.length });
    }
    const rows = search.queryRows(num(q.get("days")) ?? 90, q.get("pages")?.split(",").filter(Boolean) ?? null);
    return ok({ rows: slice(rows, q), total: rows.length });
  }],
  ["POST", /^\/api\/v1\/site\/search-data\/property$/, (_m, _q, body) => {
    const property = String(b(body, "property") ?? "").trim();
    if (!property) throw new MockHttpError(422, "property is required — the Search Console property this website reports on.");
    state.gscProperty = property;
    return ok({ property });
  }],

  ["GET", /^\/api\/v1\/site\/traffic$/, (_m, q) => ok(trafficOverview(q))],
  ["GET", /^\/api\/v1\/site\/traffic\/series$/, (_m, q) => ok({ points: traffic.seriesPoints(num(q.get("days")) ?? 28) })],
  ["GET", /^\/api\/v1\/site\/traffic\/pages$/, (_m, q) => {
    let rows = traffic.landingRows(num(q.get("days")) ?? 28);
    const needle = q.get("search")?.toLowerCase();
    if (needle) rows = rows.filter((r) => r.landingPage.includes(needle) || (r.title ?? "").toLowerCase().includes(needle));
    const channel = q.get("channel");
    if (channel) {
      const share = traffic.channelShare(channel);
      rows = rows.map((r) => ({
        ...r,
        sessions: Math.round(r.sessions * share),
        prevSessions: Math.round(r.prevSessions * share),
        engagedSessions: Math.round(r.engagedSessions * share),
        keyEvents: Math.round(r.keyEvents * share),
        revenue: Math.round(r.revenue * share * 100) / 100,
      }));
    }
    const sort = q.get("sort") ?? "sessions";
    rows.sort((a, c) =>
      sort === "delta" ? (c.sessions - c.prevSessions) - (a.sessions - a.prevSessions)
        : sort === "keyEvents" ? c.keyEvents - a.keyEvents
          : sort === "revenue" ? c.revenue - a.revenue
            : c.sessions - a.sessions);
    return ok({ pages: slice(rows, q), total: rows.length });
  }],
  ["GET", /^\/api\/v1\/site\/traffic\/content$/, (_m, q) => {
    let rows = traffic.contentRows(num(q.get("days")) ?? 28);
    const needle = q.get("search")?.toLowerCase();
    if (needle) rows = rows.filter((r) => r.pagePath.includes(needle));
    const sort = q.get("sort") ?? "views";
    rows.sort((a, c) =>
      sort === "delta" ? (c.views - c.prevViews) - (a.views - a.prevViews)
        : sort === "users" ? c.users - a.users
          : sort === "keyEvents" ? c.keyEvents - a.keyEvents
            : c.views - a.views);
    return ok({ pages: slice(rows, q), total: rows.length });
  }],
  ["GET", /^\/api\/v1\/site\/traffic\/breakdown$/, (_m, q) => {
    const rows = traffic.breakdownRows(q.get("by") ?? "source", num(q.get("days")) ?? 28);
    return ok({ rows: slice(rows, q), total: rows.length });
  }],
  ["GET", /^\/api\/v1\/site\/traffic\/property$/, () => ok({ property: state.gaProperty, domain: siteData.SITE.domain })],
  ["PUT", /^\/api\/v1\/site\/traffic\/property$/, (_m, _q, body) => {
    const property = String(b(body, "property") ?? "").trim();
    if (!property) throw new MockHttpError(422, "property is required — the Analytics property this website reports on.");
    state.gaProperty = property;
    return ok({ property });
  }],
];
