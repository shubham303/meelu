import type {
  LinkSuggestion,
  PillarSuggestion,
  SiteCrawlJob,
  SiteIssueGroup,
  SiteIssueKind,
  SiteIssueSeverity,
  SiteIssueState,
  SiteIssueSummary,
  SiteIssueType,
  SitePage,
  SitePageIssue,
  SiteRenderDevice,
  SiteRenderJobStatus,
  SuggestionState,
  SuggestionSummary,
} from "@demo/lib/types";
import * as siteData from "../data/site";
import { b, MockHttpError, newId, now, num, ok, paginate, type Route } from "../core";

interface SiteIssueRow {
  id: string;
  createdAt: string;
  updatedAt: string;
  siteId: string;
  runId: string;
  kind: SiteIssueKind;
  issue: string;
  severity: SiteIssueSeverity;
  state: SiteIssueState;
  issueType: SiteIssueType;
  rejectionReason: string | null;
}

type PageIssueRow = SitePageIssue & { runId: string; rejectionReason: string | null };

interface AuditRun {
  id: string;
  siteId: string;
  trigger: string;
  rulesRun: number;
  siteIssuesFound: number;
  pageIssuesFound: number;
  finishedAt: string | null;
  reviewedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

interface LiveCrawl {
  jobId: string;
  state: string;
  phase: "sitemap" | "links" | null;
  fetched: number;
  queued: number;
  discovered: number;
  startedAt: string;
}

interface LiveRender {
  jobId: string;
  state: string;
  scope: "sample" | "all";
  total: number;
  rendered: number;
  failed: number;
  startedAt: string;
}

interface RenderHistory {
  jobId: string;
  state: string;
  scope: "sample" | "all";
  total: number;
  rendered: number;
  failed: number;
  startedAt: string;
  finishedAt: string;
  stopReason: string | null;
}

const RUN_AT = siteData.LAST_CRAWLED_AT;
const RUN_ID = "sar_ledgerly_14";

function seedIssues() {
  const siteRows: SiteIssueRow[] = [];
  const pageRows: PageIssueRow[] = [];
  for (const seed of siteData.ISSUE_SEEDS) {
    const state = seed.state ?? "open";
    if (seed.scope === "site") {
      siteRows.push({
        id: `sis_${seed.kind}`,
        createdAt: RUN_AT,
        updatedAt: RUN_AT,
        siteId: siteData.SITE_ID,
        runId: RUN_ID,
        kind: seed.kind,
        issue: seed.issue,
        severity: seed.severity,
        state,
        issueType: seed.issueType,
        rejectionReason: state === "rejected" ? (seed.reason ?? null) : null,
      });
      continue;
    }
    const paths = seed.paths ?? [];
    for (const path of paths) {
      const page = siteData.PAGE_BY_PATH.get(path);
      if (!page) continue;
      const rejectedWhy = seed.rejected?.[path];
      const rowState: SiteIssueState = rejectedWhy ? "rejected" : state;
      pageRows.push({
        id: `spi_${seed.kind}_${page.id}`,
        createdAt: RUN_AT,
        updatedAt: RUN_AT,
        siteId: siteData.SITE_ID,
        runId: RUN_ID,
        kind: seed.kind,
        issue: seed.issue,
        severity: seed.severity,
        state: rowState,
        issueType: seed.issueType,
        pageId: page.id,
        matchedPages: paths.length,
        url: page.url,
        rejectionReason: rowState === "rejected" ? (rejectedWhy ?? seed.reason ?? null) : null,
      });
    }
  }
  return { siteRows, pageRows };
}

const seeded = seedIssues();

const state = {
  siteIssues: seeded.siteRows,
  pageIssues: seeded.pageRows,
  run: {
    id: RUN_ID,
    siteId: siteData.SITE_ID,
    trigger: "crawl",
    rulesRun: 214,
    siteIssuesFound: seeded.siteRows.length,
    pageIssuesFound: seeded.pageRows.length,
    finishedAt: RUN_AT,
    reviewedAt: null,
    createdAt: RUN_AT,
    updatedAt: RUN_AT,
  } as AuditRun,
  links: siteData.LINK_SUGGESTIONS.map((l) => ({ ...l })) as LinkSuggestion[],
  pillars: siteData.PILLAR_SUGGESTIONS.map((p) => ({ ...p, members: [...p.members] })) as PillarSuggestion[],
  lastCrawledAt: siteData.SITE.lastCrawledAt ?? null,
  crawlJobs: siteData.CRAWL_JOBS.map((j) => ({ ...j })) as SiteCrawlJob[],
  crawl: null as LiveCrawl | null,
  render: { desktop: null, mobile: null } as Record<SiteRenderDevice, LiveRender | null>,
  renderHistory: {
    desktop: renderSeed("desktop"),
    mobile: renderSeed("mobile"),
  } as Record<SiteRenderDevice, RenderHistory>,
  renderedPages: { desktop: siteData.RENDERED.desktop.pages, mobile: siteData.RENDERED.mobile.pages } as Record<SiteRenderDevice, number>,
  lastRenderedAt: { desktop: siteData.RENDERED.desktop.at, mobile: siteData.RENDERED.mobile.at } as Record<SiteRenderDevice, string>,
};

function renderSeed(device: SiteRenderDevice): RenderHistory {
  const r = siteData.RENDERED[device];
  return { jobId: `srj_${device}_7`, state: "completed", scope: "sample", total: r.total, rendered: r.total, failed: 0, startedAt: r.jobAt, finishedAt: r.at, stopReason: null };
}

export function markCrawled(): void {
  state.lastCrawledAt = now();
}

type BridgeEvent = { event: string; data: Record<string, unknown> };
type Subscribe = (cb: (m: BridgeEvent) => void) => () => void;

let listening = false;

function listenToBridge(): void {
  if (listening || typeof window === "undefined") return;
  const agent = (window as unknown as { meeluAgent?: { onCrawlEvent?: Subscribe; onRenderEvent?: Subscribe } }).meeluAgent;
  if (!agent?.onCrawlEvent || !agent.onRenderEvent) return;
  listening = true;
  agent.onCrawlEvent(onCrawlEvent);
  agent.onRenderEvent(onRenderEvent);
}

function onCrawlEvent({ event, data }: BridgeEvent): void {
  const jobId = String(data.jobId ?? "");
  if (event === "crawl:started") {
    state.crawl = { jobId, state: "running", phase: null, fetched: 0, queued: 0, discovered: 0, startedAt: now() };
  } else if (event === "crawl:progress" && state.crawl) {
    state.crawl.phase = (data.phase as LiveCrawl["phase"]) ?? state.crawl.phase;
    state.crawl.fetched = Number(data.fetched ?? state.crawl.fetched);
    state.crawl.queued = Number(data.queued ?? state.crawl.queued);
    state.crawl.discovered = Number(data.seen ?? state.crawl.discovered);
  } else if (event === "crawl:done" && state.crawl) {
    const stopped = data.stopped === true;
    const finishedAt = now();
    const fetched = Number(data.pagesStored ?? state.crawl.fetched);
    state.crawlJobs.unshift({
      id: state.crawl.jobId || newId("scj"),
      createdAt: state.crawl.startedAt,
      updatedAt: finishedAt,
      siteId: siteData.SITE_ID,
      status: stopped ? "cancelled" : "completed",
      trigger: "user",
      sitemapUrls: siteData.SITE.sitemapUrls,
      startedAt: state.crawl.startedAt,
      finishedAt,
      heartbeatAt: finishedAt,
      discovered: siteData.PAGES.length,
      fetched,
      queued: stopped ? siteData.PAGES.length - fetched : 0,
      newPages: 0,
      changed: stopped ? 0 : 2,
      unchanged: Math.max(0, fetched - 2),
      failed: 3,
      pagesStored: fetched,
      passagesStored: stopped ? Math.round(fetched * 11.6) : siteData.PAGE_STATS.chunks.total,
      complete: !stopped,
      stopReason: stopped ? "stopped by the user" : undefined,
      notes: [],
    });
    state.crawl = null;
    state.lastCrawledAt = finishedAt;
  }
}

function onRenderEvent({ event, data }: BridgeEvent): void {
  const device = data.device as SiteRenderDevice;
  if (device !== "desktop" && device !== "mobile") return;
  const jobId = String(data.jobId ?? "");
  const total = Number(data.total ?? 0);
  if (event === "render:started") {
    state.render[device] = { jobId, state: "running", scope: total >= siteData.RENDER_ELIGIBLE ? "all" : "sample", total, rendered: 0, failed: 0, startedAt: now() };
  } else if (event === "render:progress" && state.render[device]) {
    const r = state.render[device]!;
    r.total = total || r.total;
    r.rendered = Number(data.rendered ?? r.rendered);
    r.failed = Number(data.failed ?? r.failed);
  } else if (event === "render:done" && state.render[device]) {
    const r = state.render[device]!;
    const stopped = data.stopped === true;
    const rendered = Number(data.rendered ?? r.rendered);
    const finishedAt = now();
    state.renderHistory[device] = {
      jobId: r.jobId,
      state: stopped ? "cancelled" : "completed",
      scope: r.scope,
      total: r.total,
      rendered,
      failed: Number(data.failed ?? 0),
      startedAt: r.startedAt,
      finishedAt,
      stopReason: stopped ? "stopped by the user" : null,
    };
    state.renderedPages[device] = Math.min(siteData.RENDER_ELIGIBLE, state.renderedPages[device] + rendered);
    state.lastRenderedAt[device] = finishedAt;
    state.render[device] = null;
  }
}

function crawlStatus() {
  const latest = state.crawlJobs[0];
  const base = {
    siteId: siteData.SITE_ID,
    domain: siteData.SITE.domain,
    lastCrawledAt: state.lastCrawledAt,
    sitemapUrls: siteData.SITE.sitemapUrls,
    pages: siteData.PAGES.length,
    stopReason: null as string | null,
    error: null as string | null,
  };
  if (state.crawl) {
    return {
      ...base,
      jobId: state.crawl.jobId,
      state: state.crawl.state,
      active: true,
      trigger: "user",
      phase: state.crawl.phase,
      startedAt: state.crawl.startedAt,
      finishedAt: null,
      fetched: state.crawl.fetched,
      queued: state.crawl.queued,
      discovered: state.crawl.discovered,
      lastCrawlComplete: latest?.complete ?? false,
    };
  }
  return {
    ...base,
    jobId: latest?.id ?? null,
    state: latest?.status ?? "idle",
    active: false,
    trigger: latest?.trigger ?? null,
    phase: null,
    startedAt: latest?.startedAt ?? null,
    finishedAt: latest?.finishedAt ?? null,
    fetched: latest?.fetched ?? 0,
    queued: latest?.queued ?? 0,
    discovered: latest?.discovered ?? 0,
    stopReason: latest?.stopReason ?? null,
    lastCrawlComplete: latest?.complete ?? false,
  };
}

function renderStatus(device: SiteRenderDevice): SiteRenderJobStatus {
  const live = state.render[device];
  const last = state.renderHistory[device];
  const counts = {
    renderedPages: state.renderedPages[device],
    eligiblePages: siteData.RENDER_ELIGIBLE,
    pendingPages: siteData.RENDER_ELIGIBLE - state.renderedPages[device],
    lastRenderedAt: state.lastRenderedAt[device],
  };
  if (live) {
    return {
      siteId: siteData.SITE_ID,
      device,
      jobId: live.jobId,
      state: live.state,
      active: true,
      trigger: "user",
      scope: live.scope,
      userAgentProfile: "googlebot",
      startedAt: live.startedAt,
      finishedAt: null,
      total: live.total,
      rendered: live.rendered,
      failed: live.failed,
      error: null,
      stopReason: null,
      ...counts,
    };
  }
  return {
    siteId: siteData.SITE_ID,
    device,
    jobId: last.jobId,
    state: last.state,
    active: false,
    trigger: "user",
    scope: last.scope,
    userAgentProfile: "googlebot",
    startedAt: last.startedAt,
    finishedAt: last.finishedAt,
    total: last.total,
    rendered: last.rendered,
    failed: last.failed,
    error: null,
    stopReason: last.stopReason,
    ...counts,
  };
}

const openIssuePageIds = () => new Set(state.pageIssues.filter((r) => r.state === "open").map((r) => r.pageId));

const STATUS_CLASS: Record<string, (s: number) => boolean> = {
  ok: (s) => s === 200,
  error: (s) => s >= 400 || s === 0,
  gone: (s) => s === 404 || s === 410,
  blocked: (s) => s === 401 || s === 403 || s === 429,
  serverError: (s) => s >= 500,
  unreachable: (s) => s === 0,
  redirect: (s) => s >= 300 && s < 400,
};

const SORT_KEY: Record<string, [(p: SitePage) => number | string | undefined, "asc" | "desc"]> = {
  url: [(p) => p.url, "asc"],
  inlinks: [(p) => p.inlinks, "desc"],
  score: [(p) => p.linkScore, "desc"],
  depth: [(p) => p.depth ?? 0, "desc"],
  words: [(p) => p.wordCount ?? 0, "asc"],
  status: [(p) => p.status ?? 0, "desc"],
  crawled: [(p) => p.lastCrawledAt ?? "", "asc"],
  changed: [(p) => p.contentChangedAt, "asc"],
};

function compare(a: number | string | undefined, b: number | string | undefined): number {
  if (a === undefined && b === undefined) return 0;
  if (a === undefined) return 1;
  if (b === undefined) return -1;
  return a < b ? -1 : a > b ? 1 : 0;
}

function filterPages(q: URLSearchParams): SitePage[] {
  let list = [...siteData.PAGES];
  const types = [...q.getAll("pageType"), ...q.getAll("pageTypes").flatMap((v) => v.split(","))].filter(Boolean);
  if (types.length) list = list.filter((p) => !!p.pageType && types.includes(p.pageType));
  const status = q.get("status");
  if (status && STATUS_CLASS[status]) list = list.filter((p) => STATUS_CLASS[status](p.status ?? 0));
  const stage = q.get("stage");
  if (stage) list = list.filter((p) => p.stage === stage);
  const format = q.get("format");
  if (format) list = list.filter((p) => p.format === format);
  for (const missing of q.getAll("missing").flatMap((v) => v.split(","))) {
    list = list.filter((p) => {
      const v = (p as unknown as Record<string, unknown>)[missing];
      return v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);
    });
  }
  const lang = q.get("lang");
  if (lang) list = list.filter((p) => p.lang === lang);
  const contains = (key: string, field: (p: SitePage) => string | undefined) => {
    const v = q.get(key)?.toLowerCase();
    if (v) list = list.filter((p) => (field(p) ?? "").toLowerCase().includes(v));
  };
  contains("urlContains", (p) => p.url);
  contains("titleContains", (p) => p.title);
  contains("metaContains", (p) => p.metaDescription);
  contains("textContains", (p) => p.bodyText);
  const range = (minKey: string, maxKey: string, field: (p: SitePage) => number | undefined) => {
    const lo = num(q.get(minKey));
    const hi = num(q.get(maxKey));
    if (lo !== null) list = list.filter((p) => field(p) !== undefined && field(p)! >= lo);
    if (hi !== null) list = list.filter((p) => field(p) !== undefined && field(p)! <= hi);
  };
  range("minWords", "maxWords", (p) => p.wordCount);
  range("minInlinks", "maxInlinks", (p) => p.inlinks);
  range("minDepth", "maxDepth", (p) => p.depth);
  const dates = (afterKey: string, beforeKey: string, field: (p: SitePage) => string | undefined) => {
    const after = q.get(afterKey);
    const before = q.get(beforeKey);
    if (after) list = list.filter((p) => (field(p) ?? "") >= after);
    if (before) list = list.filter((p) => !!field(p) && field(p)! <= `${before}T23:59:59.999Z`);
  };
  dates("crawledAfter", "crawledBefore", (p) => p.lastCrawledAt);
  dates("changedAfter", "changedBefore", (p) => p.contentChangedAt);
  dates("publishedAfter", "publishedBefore", (p) => p.publishedAt);
  const flag = (key: string, test: (p: SitePage) => boolean) => {
    const v = q.get(key);
    if (v === "true") list = list.filter(test);
    if (v === "false") list = list.filter((p) => !test(p));
  };
  const auditable = openIssuePageIds();
  flag("inSitemap", (p) => p.inSitemap);
  flag("orphan", (p) => p.status === 200 && p.inlinks === 0 && p.depth !== 0);
  flag("noindex", (p) => !!p.robotsDirectives?.includes("noindex"));
  flag("shallow", (p) => p.shallow);
  flag("blockedByRobots", (p) => p.blockedByRobots);
  flag("canonicalElsewhere", (p) => !!p.canonical && p.canonical !== p.url);
  flag("redirects", (p) => !!p.redirectTo);
  flag("needsAudit", (p) => auditable.has(p.id));

  const sorts = (q.get("sort") ?? "url").split(",").filter(Boolean);
  list.sort((a, bb) => {
    for (const spec of sorts) {
      const [field, dir] = spec.split(":");
      const def = SORT_KEY[field];
      if (!def) continue;
      const sign = (dir ?? def[1]) === "desc" ? -1 : 1;
      const ka = def[0](a);
      const kb = def[0](bb);
      if (ka === undefined || kb === undefined) {
        const c = compare(ka, kb);
        if (c) return c;
        continue;
      }
      const c = compare(ka, kb) * sign;
      if (c) return c;
    }
    return a.url.localeCompare(bb.url);
  });
  return list;
}

function stem(word: string): string {
  return word.replace(/(ing|es|s)$/, "");
}

const STOP = new Set(["the", "and", "for", "with", "how", "what", "does", "this", "that", "are", "you", "your", "our", "any", "anywhere", "covered", "there", "about", "into", "from"]);

function semanticSearch(rows: SitePage[], text: string): SitePage[] {
  const terms = text.toLowerCase().split(/[^a-z0-9-]+/).filter((t) => t.length > 2 && !STOP.has(t)).map(stem);
  if (!terms.length) return [];
  const hits: Array<{ page: SitePage; score: number; match: { text: string; headingPath?: string } }> = [];
  for (const page of rows) {
    if (page.status !== 200 || page.shallow) continue;
    const passages = siteData.searchPassages(page);
    let best: { text: string; headingPath?: string } | null = null;
    let bestHits = 0;
    for (const passage of passages) {
      const lower = passage.text.toLowerCase();
      const n = terms.filter((t) => lower.includes(t)).length;
      if (n > bestHits) {
        bestHits = n;
        best = passage;
      }
    }
    const whole = `${page.title ?? ""} ${page.metaDescription ?? ""} ${page.bodyText ?? ""} ${page.url}`.toLowerCase();
    const overall = terms.filter((t) => whole.includes(t)).length;
    if (!overall) continue;
    const titleHits = terms.filter((t) => (page.title ?? "").toLowerCase().includes(t)).length;
    const score = (overall + bestHits + titleHits) / (3 * terms.length);
    hits.push({ page, score, match: best ?? { text: page.metaDescription ?? page.title ?? "", headingPath: page.h1[0] } });
  }
  hits.sort((x, y) => y.score - x.score || (y.page.linkScore ?? 0) - (x.page.linkScore ?? 0));
  return hits.slice(0, 24).map((h, i) => ({
    ...h.page,
    similarity: Math.round(Math.max(0.41, Math.min(0.93, 0.5 + h.score * 0.42 - i * 0.008)) * 100) / 100,
    match: h.match,
  }));
}

function examplesFor(rows: PageIssueRow[]): string[] {
  return rows.map((r) => r.url ?? "").filter(Boolean).sort().slice(0, 3);
}

export function groups(want: SiteIssueState): SiteIssueGroup[] {
  const out: SiteIssueGroup[] = state.siteIssues
    .filter((r) => r.state === want)
    .map((r) => ({ scope: "site", kind: r.kind, issue: r.issue, severity: r.severity, pages: 0, matched: 0, examples: [], state: want, reason: r.rejectionReason, issueType: r.issueType }));
  const byKind = new Map<SiteIssueKind, PageIssueRow[]>();
  for (const r of state.pageIssues) if (r.state === want) byKind.set(r.kind, [...(byKind.get(r.kind) ?? []), r]);
  for (const [kind, rows] of byKind) {
    const first = rows[0];
    out.push({
      scope: "pages",
      kind,
      issue: first.issue,
      severity: first.severity,
      pages: rows.length,
      matched: Math.max(rows.length, first.matchedPages),
      examples: examplesFor(rows),
      state: want,
      reason: rows.find((r) => r.rejectionReason)?.rejectionReason ?? null,
      issueType: first.issueType,
    });
  }
  return out.sort((x, y) => x.severity.localeCompare(y.severity) || y.pages - x.pages || x.kind.localeCompare(y.kind));
}

function summary(): SiteIssueSummary & { run: AuditRun } {
  const count = (rows: Array<{ state: SiteIssueState }>) => ({
    open: rows.filter((r) => r.state === "open").length,
    rejected: rows.filter((r) => r.state === "rejected").length,
  });
  const open = groups("open");
  return {
    run: state.run,
    site: count(state.siteIssues),
    pages: count(state.pageIssues),
    openSiteIssues: open.filter((g) => g.scope === "site").map((g) => ({ kind: g.kind, issue: g.issue, severity: g.severity, issueType: g.issueType })),
    openPageIssues: open.filter((g) => g.scope === "pages"),
  };
}

function csvEscape(v: unknown): string {
  const s = String(v ?? "");
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function issuesCsv(q: URLSearchParams): string {
  const want = (q.get("state") ?? "open") as SiteIssueState;
  const type = q.get("type");
  const kinds = q.get("kind")?.split(",").filter(Boolean);
  const keep = (r: { state: SiteIssueState; issueType: SiteIssueType; kind: SiteIssueKind }) =>
    r.state === want && (!type || r.issueType === type) && (!kinds || kinds.includes(r.kind));
  const rows: unknown[][] = [["kind", "severity", "scope", "type", "state", "url", "issue"]];
  for (const r of state.siteIssues.filter(keep)) rows.push([r.kind, r.severity, "site", r.issueType, want, "", r.issue]);
  for (const r of state.pageIssues.filter(keep)) rows.push([r.kind, r.severity, "pages", r.issueType, want, r.url ?? "", r.issue]);
  return `${rows.map((r) => r.map(csvEscape).join(",")).join("\n")}\n`;
}

function issueState(body: Record<string, unknown>): SiteIssueState {
  const to = b(body, "state");
  if (to !== "open" && to !== "rejected") throw new MockHttpError(400, "state must be open or rejected.");
  return to;
}

function reasonFor(to: SiteIssueState, body: Record<string, unknown>): string | null {
  if (to !== "rejected") return null;
  const why = b(body, "rejectionReason");
  return typeof why === "string" && why.trim() ? why.trim() : null;
}

function suggestionSummary(rows: Array<{ state: SuggestionState }>): SuggestionSummary {
  const s: SuggestionSummary = { draft: 0, screeningRejected: 0, screeningApproved: 0, reviewApproved: 0, reviewRejected: 0, userRejected: 0 };
  const key: Record<SuggestionState, keyof SuggestionSummary> = {
    draft: "draft",
    screening_rejected: "screeningRejected",
    screening_approved: "screeningApproved",
    review_approved: "reviewApproved",
    review_rejected: "reviewRejected",
    user_rejected: "userRejected",
  };
  for (const r of rows) s[key[r.state]] += 1;
  return s;
}

const VISIBLE: SuggestionState[] = ["review_approved", "user_rejected"];

function statesFrom(q: URLSearchParams): SuggestionState[] {
  const asked = q.getAll("state").flatMap((v) => v.split(",")).filter(Boolean) as SuggestionState[];
  return asked.length ? asked : VISIBLE;
}

function byScore<T extends { score?: number | null }>(rows: T[], q: URLSearchParams): T[] {
  const sign = q.get("sortOrder") === "asc" ? 1 : -1;
  return [...rows].sort((x, y) => ((x.score ?? -1) - (y.score ?? -1)) * sign);
}

function suggestionPatch(body: Record<string, unknown>): SuggestionState {
  const to = b(body, "state") as SuggestionState;
  if (to !== "review_approved" && to !== "user_rejected") throw new MockHttpError(400, "A suggestion can only be approved or turned down here.");
  return to;
}

function stamped<T extends { id: string; createdAt: string; updatedAt: string; siteId: string }>(row: T, prefix: string): T {
  const at = now();
  return { ...row, id: row.id || newId(prefix), createdAt: row.createdAt || at, updatedAt: row.updatedAt || at, siteId: row.siteId || siteData.SITE_ID };
}

function insertAll<T extends { id: string }>(list: T[], rows: T[]): T[] {
  const incoming = new Set(rows.map((r) => r.id));
  return [...rows, ...list.filter((r) => !incoming.has(r.id))];
}

export function addLinkSuggestions(rows: LinkSuggestion[]): void {
  state.links = insertAll(state.links, rows.map((r) => stamped(r, "sls")));
}

export function addPillarSuggestions(rows: PillarSuggestion[]): void {
  state.pillars = insertAll(state.pillars, rows.map((r) => stamped({ ...r, members: [...(r.members ?? [])] }, "spp")));
}

export const ROUTES: Route[] = [
  ["GET", /^\/api\/v1\/site\/pages\/stats$/, () => ok({ ...siteData.PAGE_STATS, lastCrawledAt: state.lastCrawledAt })],
  ["GET", /^\/api\/v1\/site\/pages\/discovery$/, () => ok(siteData.DISCOVERY)],
  ["GET", /^\/api\/v1\/site\/pages\/by-url$/, (_m, q) => {
    const url = q.get("url") ?? "";
    const page = siteData.PAGES.find((p) => p.url === url || p.url === url.replace(/\/$/, ""));
    if (!page) throw new MockHttpError(404, "That URL is not in the crawl.");
    return ok(page);
  }],
  ["GET", /^\/api\/v1\/site\/pages$/, (_m, q) => {
    const rows = filterPages(q);
    const text = q.get("searchText")?.trim();
    if (!text) return paginate(rows, q, { note: null });
    const hits = semanticSearch(rows, text);
    return paginate(hits, q, { note: hits.length ? null : "No page covers that." });
  }],
  ["GET", /^\/api\/v1\/site\/pages\/([^/]+)\/links$/, (m) => {
    const links = siteData.pageLinks(m[1]);
    if (!links) throw new MockHttpError(404, "That page is not in the crawl.");
    return ok(links);
  }],
  ["GET", /^\/api\/v1\/site\/pages\/([^/]+)$/, (m) => {
    const page = siteData.PAGE_BY_ID.get(m[1]);
    if (!page) throw new MockHttpError(404, "That page is not in the crawl.");
    return ok(page);
  }],
  ["GET", /^\/api\/v1\/site\/page-llm-extractions\/by-page\/([^/]+)$/, (m) => {
    const ex = siteData.EXTRACTIONS.get(m[1]);
    if (!ex) throw new MockHttpError(404, "This page has not been classified yet.");
    return ok(ex);
  }],

  ["GET", /^\/api\/v1\/site\/crawl-jobs$/, (_m, q) => {
    listenToBridge();
    return paginate(state.crawlJobs, q, { status: crawlStatus() });
  }],
  ["GET", /^\/api\/v1\/site\/crawl-jobs\/([^/]+)$/, (m) => {
    const job = state.crawlJobs.find((j) => j.id === m[1]);
    if (!job) throw new MockHttpError(404, "No crawl with that id.");
    return ok(job);
  }],
  ["PATCH", /^\/api\/v1\/site\/crawl-jobs\/([^/]+)$/, (m, _q, body) => {
    if (b(body, "status") === "cancelling" && state.crawl?.jobId === m[1]) state.crawl.state = "cancelling";
    return ok({ ...crawlStatus(), id: m[1], status: state.crawl?.state ?? "cancelled" });
  }],
  ["GET", /^\/api\/v1\/site\/render-jobs$/, (_m, q) => {
    listenToBridge();
    const device = (q.get("device") ?? "desktop") as SiteRenderDevice;
    if (device !== "desktop" && device !== "mobile") throw new MockHttpError(400, "device must be one of desktop, mobile.");
    return ok({ status: renderStatus(device) });
  }],
  ["PATCH", /^\/api\/v1\/site\/render-jobs\/([^/]+)$/, (m, _q, body) => {
    for (const device of ["desktop", "mobile"] as const) {
      const live = state.render[device];
      if (live?.jobId === m[1] && b(body, "status") === "cancelling") live.state = "cancelling";
    }
    return ok({ id: m[1], status: "cancelling" });
  }],

  ["GET", /^\/api\/v1\/site\/technical-seo\/summary$/, () => ok(summary())],
  ["GET", /^\/api\/v1\/site\/technical-seo\/groups$/, (_m, q) => ok(groups((q.get("state") ?? "open") as SiteIssueState))],
  ["GET", /^\/api\/v1\/site\/technical-seo\/issues$/, (_m, q) => {
    const want = q.get("state");
    return paginate(state.siteIssues.filter((r) => !want || r.state === want), q);
  }],
  ["PATCH", /^\/api\/v1\/site\/technical-seo\/issues$/, (_m, _q, body) => {
    const to = issueState(body);
    const kind = b(body, "kind");
    const rows = state.siteIssues.filter((r) => r.kind === kind);
    if (!rows.length) throw new MockHttpError(404, "No site issue in this run matched.");
    for (const r of rows) Object.assign(r, { state: to, rejectionReason: reasonFor(to, body), updatedAt: now() });
    return ok({ runId: state.run.id, updated: rows.length });
  }],
  ["GET", /^\/api\/v1\/site\/technical-seo\/page-issues$/, (_m, q) => {
    const want = q.get("state");
    const kind = q.get("kind");
    const type = q.get("issueType");
    const rows = state.pageIssues
      .filter((r) => (!want || r.state === want) && (!kind || r.kind === kind) && (!type || r.issueType === type))
      .sort((x, y) => (x.url ?? "").localeCompare(y.url ?? ""));
    return paginate(rows, q);
  }],
  ["PATCH", /^\/api\/v1\/site\/technical-seo\/page-issues$/, (_m, _q, body) => {
    const to = issueState(body);
    const kind = b(body, "kind");
    const pageIdWanted = b(body, "pageId");
    const rows = state.pageIssues.filter((r) => (!kind || r.kind === kind) && (!pageIdWanted || r.pageId === pageIdWanted));
    if (!rows.length) throw new MockHttpError(404, "No page issue in this run matched.");
    for (const r of rows) Object.assign(r, { state: to, rejectionReason: reasonFor(to, body), updatedAt: now() });
    return ok({ runId: state.run.id, updated: rows.length });
  }],
  ["GET", /^\/api\/v1\/site\/technical-seo\/page-issues\/([^/]+)$/, (m) => {
    const row = state.pageIssues.find((r) => r.id === m[1]);
    if (!row) throw new MockHttpError(404, "No page issue with that id.");
    return ok(row);
  }],
  ["PATCH", /^\/api\/v1\/site\/technical-seo\/page-issues\/([^/]+)$/, (m, _q, body) => {
    const row = state.pageIssues.find((r) => r.id === m[1]);
    if (!row) throw new MockHttpError(404, "No page issue with that id.");
    const to = issueState(body);
    Object.assign(row, { state: to, rejectionReason: reasonFor(to, body), updatedAt: now() });
    return ok(row);
  }],
  ["POST", /^\/api\/v1\/site\/technical-seo\/run-audit$/, () => {
    const at = now();
    state.run = { ...state.run, id: newId("sar"), trigger: "user", finishedAt: at, createdAt: at, updatedAt: at };
    for (const r of state.siteIssues) r.runId = state.run.id;
    for (const r of state.pageIssues) r.runId = state.run.id;
    return ok({ ...summary(), checks: state.run.rulesRun });
  }],
  ["GET", /^\/api\/v1\/site\/technical-seo\/download$/, (_m, q) => ok({ filename: `ledgerly-app-${q.get("state") ?? "open"}-issues.csv`, body: issuesCsv(q) })],

  ["GET", /^\/api\/v1\/site\/structure\/link-suggestions\/summary$/, () => ok(suggestionSummary(state.links))],
  ["POST", /^\/api\/v1\/site\/structure\/link-suggestions\/reconcile$/, () => {
    const before = state.links.length;
    state.links = state.links.filter((l) => !siteData.RESOLVED_LINKS.has(l.id));
    return ok({ removed: before - state.links.length });
  }],
  ["GET", /^\/api\/v1\/site\/structure\/link-suggestions$/, (_m, q) => {
    const states = statesFrom(q);
    let rows = state.links.filter((l) => states.includes(l.state));
    const action = q.get("action");
    if (action) rows = rows.filter((l) => l.action === action);
    const has = (key: string, field: (l: LinkSuggestion) => string | null | undefined) => {
      const v = q.get(key)?.toLowerCase();
      if (v) rows = rows.filter((l) => (field(l) ?? "").toLowerCase().includes(v));
    };
    has("fromUrl", (l) => l.fromUrl);
    has("toUrl", (l) => l.toUrl);
    const either = q.get("url")?.toLowerCase();
    if (either) rows = rows.filter((l) => (l.fromUrl ?? "").toLowerCase().includes(either) || (l.toUrl ?? "").toLowerCase().includes(either));
    for (const key of ["fromPageId", "toPageId", "jobId"] as const) {
      const v = q.get(key);
      if (v) rows = rows.filter((l) => l[key] === v);
    }
    const pid = q.get("pageId");
    if (pid) rows = rows.filter((l) => l.fromPageId === pid || l.toPageId === pid);
    return paginate(byScore(rows, q), q);
  }],
  ["GET", /^\/api\/v1\/site\/structure\/link-suggestions\/([^/]+)$/, (m) => {
    const row = state.links.find((l) => l.id === m[1]);
    if (!row) throw new MockHttpError(404, "No link suggestion with that id.");
    return ok(row);
  }],
  ["PATCH", /^\/api\/v1\/site\/structure\/link-suggestions\/([^/]+)$/, (m, _q, body) => {
    const row = state.links.find((l) => l.id === m[1]);
    if (!row) throw new MockHttpError(404, "No link suggestion with that id.");
    Object.assign(row, { state: suggestionPatch(body), updatedAt: now() });
    return ok(row);
  }],
  ["DELETE", /^\/api\/v1\/site\/structure\/link-suggestions\/([^/]+)$/, (m) => {
    state.links = state.links.filter((l) => l.id !== m[1]);
    return ok({ id: m[1], deleted: true });
  }],

  ["GET", /^\/api\/v1\/site\/structure\/pillar-suggestions\/summary$/, () => ok(suggestionSummary(state.pillars))],
  ["POST", /^\/api\/v1\/site\/structure\/pillar-suggestions\/reconcile$/, () => {
    const before = state.pillars.length;
    state.pillars = state.pillars.filter((p) => !siteData.RESOLVED_PILLARS.has(p.id));
    return ok({ removed: before - state.pillars.length });
  }],
  ["GET", /^\/api\/v1\/site\/structure\/pillar-suggestions$/, (_m, q) => {
    const states = statesFrom(q);
    let rows = state.pillars.filter((p) => states.includes(p.state));
    const action = q.get("action");
    if (action) rows = rows.filter((p) => p.action === action);
    return paginate(byScore(rows, q), q);
  }],
  ["GET", /^\/api\/v1\/site\/structure\/pillar-suggestions\/([^/]+)$/, (m) => {
    const row = state.pillars.find((p) => p.id === m[1]);
    if (!row) throw new MockHttpError(404, "No pillar suggestion with that id.");
    return ok(row);
  }],
  ["PATCH", /^\/api\/v1\/site\/structure\/pillar-suggestions\/([^/]+)$/, (m, _q, body) => {
    const row = state.pillars.find((p) => p.id === m[1]);
    if (!row) throw new MockHttpError(404, "No pillar suggestion with that id.");
    Object.assign(row, { state: suggestionPatch(body), updatedAt: now() });
    return ok(row);
  }],
  ["DELETE", /^\/api\/v1\/site\/structure\/pillar-suggestions\/([^/]+)$/, (m) => {
    state.pillars = state.pillars.filter((p) => p.id !== m[1]);
    return ok({ id: m[1], deleted: true });
  }],
];
