import type {
  ContentPiece,
  ContentPieceSlim,
  LinkSuggestion,
  Note,
  NoteHit,
  PillarSuggestion,
  SiteIssueGroup,
  SitePage,
  SitePageIssue,
  SiteProfile,
  SocialListeningPost,
  SocialListeningQuery,
  SocialListeningTarget,
  AnalyticsSession,
  AnalyticsSource,
  AnalyticsReport,
  ApiKey,
} from "@demo/lib/types";
import type { PieceIssue } from "@/app/demo/dashboard/content/types";
import { ago, DAY, HOUR, NOW } from "./rand";
import * as siteData from "./data/site";
import * as search from "./data/search";
import * as traffic from "./data/traffic";
import * as content from "./data/content";
import * as social from "./data/social";
import * as analytics from "./data/analytics";
import * as misc from "./data/misc";

export class MockHttpError extends Error {
  constructor(
    public status: number,
    message: string,
    public extra: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

const state = {
  site: { ...siteData.SITE } as SiteProfile,
  sites: [{ ...siteData.SITE }] as SiteProfile[],
  profile: { ...misc.PROFILE },
  notes: [...misc.NOTES] as Note[],
  keys: [...misc.KEYS] as ApiKey[],
  groups: siteData.ISSUE_GROUPS.map((g) => ({ ...g })) as SiteIssueGroup[],
  pageIssues: siteData.PAGE_ISSUES.map((p) => ({ ...p })) as SitePageIssue[],
  links: siteData.LINK_SUGGESTIONS.map((l) => ({ ...l })) as LinkSuggestion[],
  pillars: siteData.PILLAR_SUGGESTIONS.map((p) => ({ ...p })) as PillarSuggestion[],
  channels: content.CHANNELS.map((c) => ({ ...c })),
  pieces: content.PIECES.map((p) => ({ ...p })) as ContentPiece[],
  issues: content.ISSUES.map((i) => ({ ...i })) as PieceIssue[],
  socialConfig: { ...social.CONFIG },
  queries: social.QUERIES.map((q) => ({ ...q })) as SocialListeningQuery[],
  targets: social.TARGETS.map((t) => ({ ...t })) as SocialListeningTarget[],
  posts: social.POSTS.map((p) => ({ ...p })) as SocialListeningPost[],
  sessions: analytics.SESSIONS.map((s) => ({ ...s })) as AnalyticsSession[],
  sources: analytics.SOURCES.map((s) => ({ ...s })) as AnalyticsSource[],
  reports: analytics.REPORTS.map((r) => ({ ...r })) as AnalyticsReport[],
  csv: { ...analytics.CSV } as Record<string, string>,
  lastCrawledAt: siteData.SITE.lastCrawledAt ?? null,
};

export function mockState() {
  return state;
}

let counter = 100;
function newId(prefix: string): string {
  counter += 1;
  return `${prefix}_${counter.toString(36)}`;
}

function now(): string {
  return new Date().toISOString();
}

function paginate<T>(list: T[], q: URLSearchParams, extra: Record<string, unknown> = {}) {
  const page = Math.max(1, Number(q.get("page") ?? 1));
  const size = Math.max(1, Number(q.get("page_size") ?? q.get("pageSize") ?? 50));
  const total = list.length;
  const totalPages = Math.max(1, Math.ceil(total / size));
  return {
    ...extra,
    data: list.slice((page - 1) * size, page * size),
    pagination: { page, page_size: size, total, total_pages: totalPages, has_next: page < totalPages, has_prev: page > 1 },
  };
}

function ok(data: unknown) {
  return { data };
}

function num(v: string | null): number | null {
  if (v === null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function slim(p: ContentPiece): ContentPieceSlim {
  const { id, createdAt, updatedAt, siteId, title, channelKey, status, wordCount, checks, mediaSource, mediaUrl, parentPieceId } = p;
  return { id, createdAt, updatedAt, siteId, title, channelKey, status, wordCount, checks, mediaSource, mediaUrl, parentPieceId };
}

function recheckPiece(p: ContentPiece): ContentPiece {
  const channel = state.channels.find((c) => c.channelKey === p.channelKey);
  const checks = [...p.checks.filter((c) => c.code !== "media_required" && c.code !== "too_long")];
  if (channel?.requiresMedia && p.mediaSource === "none") {
    checks.push({ code: "media_required", level: "block", message: `${channel.label} needs a picture. Add one and this piece unblocks.` });
  }
  if (channel && p.bodyMarkdown.length > channel.characterLimit) {
    checks.push({ code: "too_long", level: "block", message: `${p.bodyMarkdown.length.toLocaleString()} characters; ${channel.label} allows ${channel.characterLimit.toLocaleString()}.` });
  }
  return {
    ...p,
    checks,
    status: checks.some((c) => c.level === "block") ? "blocked" : "draft",
    wordCount: p.bodyMarkdown.split(/\s+/).filter(Boolean).length,
  };
}

function filterPages(q: URLSearchParams): SitePage[] {
  let list = [...siteData.PAGES];
  const kind = q.get("kind");
  if (kind) list = list.filter((p) => p.kind === kind);
  const status = q.get("status");
  if (status) {
    list = list.filter((p) => {
      const s = p.status ?? 0;
      switch (status) {
        case "ok": return s === 200;
        case "redirect": return s >= 300 && s < 400;
        case "gone": return s === 404 || s === 410;
        case "blocked": return s === 401 || s === 403 || s === 429;
        case "serverError": return s >= 500;
        case "unreachable": return s === 0;
        case "error": return s !== 200;
        default: return true;
      }
    });
  }
  const stage = q.get("stage");
  if (stage) list = list.filter((p) => p.stage === stage);
  const format = q.get("format");
  if (format) list = list.filter((p) => p.format === format);
  for (const missing of q.getAll("missing")) {
    list = list.filter((p) => {
      const v = (p as unknown as Record<string, unknown>)[missing];
      return v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);
    });
  }
  const lang = q.get("lang");
  if (lang) list = list.filter((p) => p.lang === lang);
  const contains = (key: string, pickField: (p: SitePage) => string | undefined) => {
    const v = q.get(key)?.toLowerCase();
    if (v) list = list.filter((p) => (pickField(p) ?? "").toLowerCase().includes(v));
  };
  contains("urlContains", (p) => p.url);
  contains("titleContains", (p) => p.title);
  contains("metaContains", (p) => p.metaDescription);
  contains("textContains", (p) => p.bodyText);
  const range = (minKey: string, maxKey: string, field: (p: SitePage) => number | undefined) => {
    const lo = num(q.get(minKey));
    const hi = num(q.get(maxKey));
    if (lo !== null) list = list.filter((p) => (field(p) ?? -1) >= lo);
    if (hi !== null) list = list.filter((p) => (field(p) ?? Infinity) <= hi);
  };
  range("minWords", "maxWords", (p) => p.wordCount);
  range("minInlinks", "maxInlinks", (p) => p.inlinks);
  range("minDepth", "maxDepth", (p) => p.depth);
  const dates = (afterKey: string, beforeKey: string, field: (p: SitePage) => string | undefined) => {
    const after = q.get(afterKey);
    const before = q.get(beforeKey);
    if (after) list = list.filter((p) => (field(p) ?? "") >= after);
    if (before) list = list.filter((p) => (field(p) ?? "9") <= `${before}T23:59:59`);
  };
  dates("crawledAfter", "crawledBefore", (p) => p.lastCrawledAt);
  dates("changedAfter", "changedBefore", (p) => p.contentChangedAt);
  dates("publishedAfter", "publishedBefore", (p) => p.publishedAt);
  const bool = (key: string, test: (p: SitePage) => boolean) => {
    const v = q.get(key);
    if (v === "true") list = list.filter(test);
    if (v === "false") list = list.filter((p) => !test(p));
  };
  bool("inSitemap", (p) => p.inSitemap);
  bool("orphan", (p) => p.inlinks === 0 && p.status === 200);
  bool("noindex", (p) => !!p.robotsDirectives?.includes("noindex"));
  bool("shallow", (p) => p.shallow);
  bool("blockedByRobots", (p) => p.blockedByRobots);
  bool("canonicalElsewhere", (p) => !!p.canonical && p.canonical !== p.url);
  bool("redirects", (p) => !!p.redirectTo);
  bool("needsAudit", (p) => (p.status ?? 0) !== 200 || !p.metaDescription);

  const searchText = q.get("searchText")?.toLowerCase().trim();
  if (searchText) {
    const terms = searchText.split(/\s+/).filter((t) => t.length > 2);
    const scored = siteData.SEARCH_CORPUS.filter((c) => list.includes(c.page)).map((c) => {
      const hits = terms.filter((t) => c.text.includes(t)).length;
      const score = terms.length ? hits / terms.length : 0;
      return { page: c.page, score };
    }).filter((s) => s.score > 0).sort((a, b) => b.score - a.score);
    return scored.map((s) => ({
      ...s.page,
      similarity: Math.round((0.55 + s.score * 0.4) * 100) / 100,
      match: { text: s.page.bodyText ?? s.page.metaDescription ?? s.page.title ?? "", headingPath: s.page.h1[0] },
    }));
  }

  const [field, dir] = (q.get("sort") ?? "url:asc").split(":");
  const sign = dir === "desc" ? -1 : 1;
  const key = (p: SitePage): number | string => {
    switch (field) {
      case "status": return p.status ?? 0;
      case "score": return p.linkScore ?? 0;
      case "words": return p.wordCount ?? 0;
      case "inlinks": return p.inlinks;
      case "changed": return p.contentChangedAt ?? "";
      default: return p.url;
    }
  };
  list.sort((a, b) => {
    const ka = key(a);
    const kb = key(b);
    return (ka < kb ? -1 : ka > kb ? 1 : 0) * sign;
  });
  return list;
}

function pageRowsSorted(days: number, q: URLSearchParams) {
  let rows = search.pageRows(days);
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
  rows.sort((a, b) => {
    const ka = key(a);
    const kb = key(b);
    return (ka < kb ? -1 : ka > kb ? 1 : 0) * dir;
  });
  return rows;
}

function slice<T>(rows: T[], q: URLSearchParams): T[] {
  const limit = num(q.get("limit")) ?? 20;
  const offset = num(q.get("offset")) ?? 0;
  return rows.slice(offset, offset + limit);
}

function socialSummary() {
  const posts = state.posts;
  const count = (f: (p: SocialListeningPost) => boolean) => posts.filter(f).length;
  const brand = posts.filter((p) => p.kind === "brand");
  return {
    unprocessed: 0,
    needsReply: count((p) => p.kind === "topic" && p.status === "needs_reply"),
    drafted: count((p) => p.status === "drafted"),
    replied: count((p) => p.status === "replied"),
    skipped: count((p) => p.status === "skipped"),
    brandMentions: brand.length,
    competitorMentions: count((p) => p.kind === "competitor"),
    lastRun: social.LAST_RUN,
    keptByQuery: state.queries.map((q) => ({ id: q.id, text: q.text, kept: count((p) => p.queryId === q.id) })),
    mentionClasses: {
      praise: brand.filter((p) => p.classes.includes("praise")).length,
      complaint: brand.filter((p) => p.classes.includes("complaint")).length,
      featureRequest: brand.filter((p) => p.classes.includes("feature_request")).length,
      question: brand.filter((p) => p.classes.includes("question")).length,
      switchOpportunity: brand.filter((p) => p.classes.includes("switch_opportunity")).length,
    },
    sentiment: {
      positive: brand.filter((p) => p.sentiment === "positive").length,
      neutral: brand.filter((p) => p.sentiment === "neutral").length,
      negative: brand.filter((p) => p.sentiment === "negative").length,
    },
  };
}

function sortPosts(list: SocialListeningPost[], sort: string | null) {
  const copy = [...list];
  if (sort === "newest") copy.sort((a, b) => (b.postedAt ?? "").localeCompare(a.postedAt ?? ""));
  else if (sort === "engaged") copy.sort((a, b) => (b.engagement.score ?? 0) - (a.engagement.score ?? 0));
  else copy.sort((a, b) => (b.compositeScore ?? 0) - (a.compositeScore ?? 0));
  return copy;
}

function csvEscape(v: unknown): string {
  const s = String(v ?? "");
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function issuesCsv(q: URLSearchParams): string {
  const st = q.get("state") ?? "open";
  const type = q.get("type") ?? "static";
  const kinds = q.get("kind")?.split(",").filter(Boolean);
  const rows: string[][] = [["kind", "scope", "severity", "state", "url", "issue"]];
  for (const g of state.groups) {
    if (g.state !== st || g.issueType !== type) continue;
    if (kinds && !kinds.includes(g.kind)) continue;
    if (g.scope === "site") rows.push([g.kind, "site", g.severity, g.state, siteData.ORIGIN, g.issue]);
    else for (const pi of state.pageIssues.filter((p) => p.kind === g.kind && p.state === st)) rows.push([g.kind, "pages", g.severity, g.state, pi.url ?? "", g.issue]);
  }
  return rows.map((r) => r.map(csvEscape).join(",")).join("\n");
}

type Handler = (m: RegExpMatchArray, q: URLSearchParams, body: Record<string, unknown>) => unknown;
type Route = [string, RegExp, Handler];

const b = (body: Record<string, unknown>, key: string) => body[key];

const ROUTES: Route[] = [
  ["GET", /^\/api\/auth\/me$/, () => ok(misc.USER)],
  ["POST", /^\/api\/auth\/logout$/, () => ok({ ok: true })],

  ["GET", /^\/api\/v1\/stats$/, () => ok({
    site: { pages: siteData.PAGES.length, needsReading: 0 },
    pages: { open: state.groups.filter((g) => g.state === "open").length, verified: 3, rejected: state.groups.filter((g) => g.state === "rejected").length },
    analytics: { sources: state.sources.length, reports: state.reports.length },
    content: { drafts: state.pieces.filter((p) => p.status === "draft").length, blocked: state.pieces.filter((p) => p.status === "blocked").length },
  })],

  ["GET", /^\/api\/v1\/site$/, () => ok(state.site)],
  ["PUT", /^\/api\/v1\/site$/, (_m, _q, body) => {
    Object.assign(state.site, body, { updatedAt: now() });
    state.sites = state.sites.map((s) => (s.id === state.site.id ? state.site : s));
    return ok(state.site);
  }],
  ["GET", /^\/api\/v1\/sites$/, (_m, q) => paginate(state.sites, q)],
  ["POST", /^\/api\/v1\/sites$/, (_m, _q, body) => {
    const site: SiteProfile = {
      ...siteData.SITE,
      id: newId("site"),
      createdAt: now(),
      updatedAt: now(),
      domain: String(b(body, "domain") ?? "example.com"),
      name: String(b(body, "name") ?? b(body, "domain") ?? "New website"),
      summary: undefined,
      socialLinks: [],
      sitemapUrls: [],
      sitemapUrlCount: undefined,
      lastCrawledAt: null,
      robotsStatus: null,
      llmsStatus: null,
      crawlerAccess: null,
      hostVariants: null,
      gscProperty: null,
      gaProperty: null,
    };
    state.sites.push(site);
    return ok(site);
  }],
  ["DELETE", /^\/api\/v1\/sites\/([^/]+)$/, (m) => {
    if (m[1] === siteData.SITE_ID) throw new MockHttpError(400, "The demo website cannot be deleted — but you can add another one.");
    state.sites = state.sites.filter((s) => s.id !== m[1]);
    return ok({ ok: true });
  }],

  ["GET", /^\/api\/v1\/profile$/, () => ok(state.profile)],
  ["PUT", /^\/api\/v1\/profile$/, (_m, _q, body) => { Object.assign(state.profile, body, { updatedAt: now() }); return ok(state.profile); }],

  ["GET", /^\/api\/v1\/keys$/, (_m, q) => paginate(state.keys, q)],
  ["POST", /^\/api\/v1\/keys$/, () => {
    const key = { id: newId("key"), createdAt: now(), updatedAt: now(), name: "New key", preview: "mlu_…d21a", lastUsedAt: null, key: "mlu_live_9c1f4e2ab7d84f3a1e6b0c5d21a" };
    state.keys.push(key);
    return ok(key);
  }],
  ["DELETE", /^\/api\/v1\/keys\/([^/]+)$/, (m) => { state.keys = state.keys.filter((k) => k.id !== m[1]); return ok({ ok: true }); }],

  ["GET", /^\/api\/v1\/notes$/, (_m, q) => {
    const needle = q.get("q")?.toLowerCase().trim();
    if (needle) {
      const terms = needle.split(/\s+/);
      const hits: NoteHit[] = state.notes
        .map((n) => ({ ...n, score: terms.filter((t) => n.note.toLowerCase().includes(t)).length / terms.length, similarity: null }))
        .filter((n) => n.score > 0)
        .sort((a, c) => c.score - a.score);
      return ok({ hits, mode: "keyword", note: hits.length ? undefined : "Nothing matched those words." });
    }
    return paginate([...state.notes].sort((a, c) => c.createdAt.localeCompare(a.createdAt)), q);
  }],
  ["POST", /^\/api\/v1\/notes$/, (_m, _q, body) => {
    const note: Note = { id: newId("nt"), createdAt: now(), updatedAt: now(), siteId: siteData.SITE_ID, note: String(b(body, "note") ?? ""), kind: (b(body, "kind") as Note["kind"]) ?? "note" };
    state.notes.unshift(note);
    return ok(note);
  }],
  ["PUT", /^\/api\/v1\/notes\/([^/]+)$/, (m, _q, body) => {
    const note = state.notes.find((n) => n.id === m[1]);
    if (!note) throw new MockHttpError(404, "No such note.");
    Object.assign(note, body, { updatedAt: now() });
    return ok(note);
  }],
  ["DELETE", /^\/api\/v1\/notes\/([^/]+)$/, (m) => { state.notes = state.notes.filter((n) => n.id !== m[1]); return ok({ ok: true }); }],

  ["GET", /^\/api\/v1\/agent\/scope$/, (_m, q) => ok(misc.scopeFor(q.get("action") ?? ""))],
  ["GET", /^(\/api\/v1)?\/credits$/, () => ok(misc.CREDITS.balance)],
  ["GET", /^(\/api\/v1)?\/credits\/ledger$/, (_m, q) => paginate(misc.CREDITS.ledger, q)],

  ["GET", /^\/api\/v1\/site\/pages\/stats$/, () => ok({ ...siteData.PAGE_STATS, lastCrawledAt: state.lastCrawledAt })],
  ["GET", /^\/api\/v1\/site\/pages\/discovery$/, () => ok(siteData.DISCOVERY)],
  ["GET", /^\/api\/v1\/site\/pages$/, (_m, q) => {
    const rows = filterPages(q);
    return paginate(rows, q, q.get("searchText") ? { note: rows.length ? null : "Nothing in the corpus is close to that." } : {});
  }],
  ["GET", /^\/api\/v1\/site\/pages\/([^/]+)$/, (m) => {
    const page = siteData.PAGE_BY_ID.get(m[1]);
    if (!page) throw new MockHttpError(404, "That page is not in the crawl.");
    return ok(page);
  }],
  ["GET", /^\/api\/v1\/site\/page-llm-extractions\/by-page\/([^/]+)$/, (m) => {
    const ex = siteData.EXTRACTIONS.get(m[1]);
    if (!ex) throw new MockHttpError(404, "Not classified yet.");
    return ok(ex);
  }],

  ["GET", /^\/api\/v1\/site\/crawl-jobs$/, (_m, q) => paginate([], q, { status: { ...siteData.crawlView(), lastCrawledAt: state.lastCrawledAt } })],
  ["PATCH", /^\/api\/v1\/site\/crawl-jobs\/([^/]+)$/, () => ok({ ok: true })],
  ["GET", /^\/api\/v1\/site\/render-jobs$/, (_m, q) => ok({ status: siteData.renderStatus((q.get("device") as "desktop" | "mobile") ?? "desktop") })],
  ["PATCH", /^\/api\/v1\/site\/render-jobs\/([^/]+)$/, () => ok({ ok: true })],

  ["GET", /^\/api\/v1\/site\/technical-seo\/summary$/, () => ok(siteData.issueSummary(state.groups))],
  ["GET", /^\/api\/v1\/site\/technical-seo\/groups$/, (_m, q) => ok(state.groups.filter((g) => g.state === (q.get("state") ?? "open")))],
  ["GET", /^\/api\/v1\/site\/technical-seo\/page-issues$/, (_m, q) => {
    const rows = state.pageIssues.filter((p) => p.kind === q.get("kind") && p.state === (q.get("state") ?? "open"));
    return paginate(rows, q);
  }],
  ["PATCH", /^\/api\/v1\/site\/technical-seo\/(issues|page-issues)$/, (_m, _q, body) => {
    const kind = b(body, "kind");
    const to = b(body, "state") as SiteIssueGroup["state"];
    for (const g of state.groups) if (g.kind === kind) { g.state = to; g.reason = (b(body, "rejectionReason") as string | undefined) ?? null; }
    for (const p of state.pageIssues) if (p.kind === kind) p.state = to;
    return ok({ ok: true });
  }],
  ["PATCH", /^\/api\/v1\/site\/technical-seo\/page-issues\/([^/]+)$/, (m, _q, body) => {
    const row = state.pageIssues.find((p) => p.id === m[1]);
    if (row) {
      row.state = b(body, "state") as SitePageIssue["state"];
      const group = state.groups.find((g) => g.kind === row.kind && g.scope === "pages");
      if (group) {
        const open = state.pageIssues.filter((p) => p.kind === row.kind && p.state === "open");
        group.pages = open.length;
        group.matched = open.length;
        group.examples = open.slice(0, 3).map((p) => p.url ?? "");
        if (open.length === 0) group.state = "rejected";
      }
    }
    return ok({ ok: true });
  }],
  ["POST", /^\/api\/v1\/site\/technical-seo\/run-audit$/, () => ok({ ok: true, checked: siteData.PAGES.length })],

  ["GET", /^\/api\/v1\/site\/structure\/link-suggestions\/summary$/, () => {
    const s = { draft: 0, ready: 0, llm_rejected: 0, user_rejected: 0, done: 0, stale: 0 };
    for (const l of state.links) s[l.state] += 1;
    return ok(s);
  }],
  ["GET", /^\/api\/v1\/site\/structure\/link-suggestions$/, (_m, q) => {
    let rows = state.links.filter((l) => l.state === (q.get("state") ?? "ready"));
    const action = q.get("action");
    if (action) rows = rows.filter((l) => l.action === action);
    const url = q.get("url")?.toLowerCase();
    if (url) rows = rows.filter((l) => (l.fromUrl ?? "").toLowerCase().includes(url) || (l.toUrl ?? "").toLowerCase().includes(url));
    return paginate(rows, q);
  }],
  ["PATCH", /^\/api\/v1\/site\/structure\/link-suggestions\/([^/]+)$/, (m, _q, body) => {
    const row = state.links.find((l) => l.id === m[1]);
    if (row) Object.assign(row, body, { updatedAt: now() });
    return ok(row);
  }],
  ["DELETE", /^\/api\/v1\/site\/structure\/link-suggestions\/([^/]+)$/, (m) => { state.links = state.links.filter((l) => l.id !== m[1]); return ok({ ok: true }); }],
  ["GET", /^\/api\/v1\/site\/structure\/pillar-suggestions\/summary$/, () => {
    const s = { draft: 0, ready: 0, llm_rejected: 0, user_rejected: 0, done: 0, stale: 0 };
    for (const p of state.pillars) s[p.state] += 1;
    return ok(s);
  }],
  ["GET", /^\/api\/v1\/site\/structure\/pillar-suggestions$/, (_m, q) => paginate(state.pillars.filter((p) => p.state === (q.get("state") ?? "ready")), q)],
  ["PATCH", /^\/api\/v1\/site\/structure\/pillar-suggestions\/([^/]+)$/, (m, _q, body) => {
    const row = state.pillars.find((p) => p.id === m[1]);
    if (row) Object.assign(row, body, { updatedAt: now() });
    return ok(row);
  }],
  ["DELETE", /^\/api\/v1\/site\/structure\/pillar-suggestions\/([^/]+)$/, (m) => { state.pillars = state.pillars.filter((p) => p.id !== m[1]); return ok({ ok: true }); }],

  ["GET", /^\/api\/v1\/site\/search-data$/, () => ok({
    connected: true,
    property: state.site.gscProperty,
    hasData: true,
    operatingBlind: false,
    firstDay: search.FIRST_DAY,
    lastDay: search.LAST_DAY,
    indexation: search.indexationCounts(),
    neverChecked: 0,
    googlePrefers: [{ url: `${siteData.ORIGIN}/pricing/`, googleCanonical: `${siteData.ORIGIN}/pricing`, coverageState: "Duplicate, Google chose different canonical than user" }],
    contentQualityVerdict: null,
    active: null,
  })],
  ["GET", /^\/api\/v1\/site\/search-data\/series$/, (_m, q) => {
    const days = num(q.get("days")) ?? 90;
    const pages = q.get("pages")?.split(",").filter(Boolean) ?? [];
    return ok({
      hasData: true,
      lastDay: search.LAST_DAY,
      days,
      series: pages.length ? pages.map((p) => ({ page: p, points: search.pointsFor(p, days) })) : [{ page: null, points: search.pointsFor(null, days) }],
      current: search.totalsFor(null, days),
      previous: search.totalsFor(null, days, days),
    });
  }],
  ["GET", /^\/api\/v1\/site\/search-data\/pages$/, (_m, q) => {
    const rows = pageRowsSorted(num(q.get("days")) ?? 90, q);
    return ok({ rows: slice(rows, q), total: rows.length });
  }],
  ["GET", /^\/api\/v1\/site\/search-data\/queries$/, (_m, q) => {
    if (q.get("view") === "striking") {
      const rows = search.strikingRows();
      return ok({ rows: slice(rows, q), total: rows.length });
    }
    const rows = search.queryRows(num(q.get("days")) ?? 90, q.get("pages")?.split(",").filter(Boolean) ?? null);
    return ok({ rows: slice(rows, q), total: rows.length });
  }],
  ["POST", /^\/api\/v1\/site\/search-data\/property$/, (_m, _q, body) => { state.site.gscProperty = String(b(body, "property") ?? b(body, "siteUrl") ?? ""); return ok(state.site); }],

  ["GET", /^\/api\/v1\/site\/traffic$/, (_m, q) => {
    const days = num(q.get("days")) ?? 90;
    const cur = traffic.channelTotals(days)["Organic Search"];
    const prev = traffic.channelTotals(days, days)["Organic Search"];
    return ok({
      connected: true,
      property: state.site.gaProperty,
      hasData: true,
      days,
      firstDay: traffic.TRAFFIC_FIRST_DAY,
      lastDay: traffic.TRAFFIC_LAST_DAY,
      totals: { current: traffic.totals(days), previous: traffic.totals(days, days) },
      organic: { current: cur, previous: prev },
      channels: traffic.channelRows(days),
      active: null,
    });
  }],
  ["GET", /^\/api\/v1\/site\/traffic\/series$/, (_m, q) => ok({ points: traffic.seriesPoints(num(q.get("days")) ?? 90) })],
  ["GET", /^\/api\/v1\/site\/traffic\/pages$/, (_m, q) => {
    let rows = traffic.landingRows(num(q.get("days")) ?? 90);
    const needle = q.get("search")?.toLowerCase();
    if (needle) rows = rows.filter((r) => r.landingPage.includes(needle));
    const channel = q.get("channel");
    if (channel) rows = rows.map((r) => ({ ...r, sessions: Math.round(r.sessions * 0.46), prevSessions: Math.round(r.prevSessions * 0.46), engagedSessions: Math.round(r.engagedSessions * 0.46), keyEvents: Math.round(r.keyEvents * 0.46) }));
    const sort = q.get("sort") ?? "sessions";
    rows.sort((a, c) => sort === "delta" ? (c.sessions - c.prevSessions) - (a.sessions - a.prevSessions) : sort === "keyEvents" ? c.keyEvents - a.keyEvents : sort === "revenue" ? c.revenue - a.revenue : c.sessions - a.sessions);
    return ok({ pages: slice(rows, q), total: rows.length });
  }],
  ["GET", /^\/api\/v1\/site\/traffic\/content$/, (_m, q) => {
    let rows = traffic.contentRows(num(q.get("days")) ?? 90);
    const needle = q.get("search")?.toLowerCase();
    if (needle) rows = rows.filter((r) => r.pagePath.includes(needle));
    const sort = q.get("sort") ?? "views";
    rows.sort((a, c) => sort === "delta" ? (c.views - c.prevViews) - (a.views - a.prevViews) : sort === "users" ? c.users - a.users : sort === "keyEvents" ? c.keyEvents - a.keyEvents : c.views - a.views);
    return ok({ pages: slice(rows, q), total: rows.length });
  }],
  ["GET", /^\/api\/v1\/site\/traffic\/breakdown$/, (_m, q) => {
    const rows = traffic.breakdownRows(q.get("by") ?? "source", num(q.get("days")) ?? 90);
    return ok({ rows: slice(rows, q), total: rows.length });
  }],
  ["PUT", /^\/api\/v1\/site\/traffic\/property$/, (_m, _q, body) => { state.site.gaProperty = String(b(body, "property") ?? ""); return ok(state.site); }],

  ["GET", /^\/api\/v1\/content\/channels$/, () => ok(state.channels)],
  ["PUT", /^\/api\/v1\/content\/channels\/([^/]+)$/, (m, _q, body) => {
    const ch = state.channels.find((c) => c.channelKey === m[1]);
    if (!ch) throw new MockHttpError(404, "No such channel.");
    Object.assign(ch, body, { updatedAt: now() });
    return ok(ch);
  }],
  ["POST", /^\/api\/v1\/content\/channels\/([^/]+)\/reset$/, (m) => {
    const ch = state.channels.find((c) => c.channelKey === m[1]);
    const seed = content.CHANNELS.find((c) => c.channelKey === m[1]);
    if (ch && seed) ch.rules = [...seed.rules];
    return ok(ch);
  }],

  ["GET", /^\/api\/v1\/content\/pieces$/, (_m, q) => {
    if (q.get("counts") === "true") {
      return ok({ byStatus: { draft: state.pieces.filter((p) => p.status === "draft").length, blocked: state.pieces.filter((p) => p.status === "blocked").length } });
    }
    let rows = [...state.pieces].sort((a, c) => c.updatedAt.localeCompare(a.updatedAt));
    const status = q.get("status");
    if (status) rows = rows.filter((p) => p.status === status);
    const channel = q.get("channel");
    if (channel) rows = rows.filter((p) => p.channelKey === channel);
    const needle = q.get("search")?.toLowerCase();
    if (needle) rows = rows.filter((p) => p.title.toLowerCase().includes(needle) || p.bodyMarkdown.toLowerCase().includes(needle));
    return paginate(rows.map(slim), q);
  }],
  ["POST", /^\/api\/v1\/content\/pieces$/, (_m, _q, body) => {
    const cloneFrom = b(body, "cloneFromPieceId") as string | undefined;
    const source = cloneFrom ? state.pieces.find((p) => p.id === cloneFrom) : undefined;
    const piece = recheckPiece({
      ...(source ?? content.PIECES[0]),
      ...(source ? {} : { bodyMarkdown: "", mediaSource: "none", mediaUrl: null, mediaAlt: null, sourcePageId: null }),
      id: newId("pc"),
      createdAt: now(),
      updatedAt: now(),
      title: String(b(body, "title") ?? source?.title ?? "Untitled piece"),
      channelKey: String(b(body, "channelKey") ?? "website"),
      parentPieceId: source?.id ?? null,
      createdBy: "user",
      checks: [],
    });
    state.pieces.unshift(piece);
    return ok(piece);
  }],
  ["GET", /^\/api\/v1\/content\/pieces\/([^/]+)$/, (m) => {
    const piece = state.pieces.find((p) => p.id === m[1]);
    if (!piece) throw new MockHttpError(404, "No such piece.");
    return ok(piece);
  }],
  ["PATCH", /^\/api\/v1\/content\/pieces\/([^/]+)$/, (m, _q, body) => {
    const idx = state.pieces.findIndex((p) => p.id === m[1]);
    if (idx < 0) throw new MockHttpError(404, "No such piece.");
    state.pieces[idx] = recheckPiece({ ...state.pieces[idx], ...body, updatedAt: now() } as ContentPiece);
    return ok(state.pieces[idx]);
  }],
  ["DELETE", /^\/api\/v1\/content\/pieces\/([^/]+)$/, (m) => { state.pieces = state.pieces.filter((p) => p.id !== m[1]); return ok({ ok: true }); }],
  ["GET", /^\/api\/v1\/content\/pieces\/([^/]+)\/markdown$/, (m) => {
    const piece = state.pieces.find((p) => p.id === m[1]);
    return `# ${piece?.title ?? ""}\n\n${piece?.bodyMarkdown ?? ""}`;
  }],
  ["GET", /^\/api\/v1\/content\/pieces\/([^/]+)\/issues$/, (m) => ok(state.issues.filter((i) => i.pieceId === m[1]))],
  ["POST", /^\/api\/v1\/content\/pieces\/([^/]+)\/issues$/, (m, _q, body) => {
    const tool = String(b(body, "tool") ?? "seo");
    const rows = (b(body, "issues") as Array<Record<string, unknown>> | undefined) ?? [];
    state.issues = state.issues.filter((i) => !(i.pieceId === m[1] && i.tool === tool && i.state === "open"));
    const runId = newId("run");
    for (const r of rows) {
      state.issues.push({
        id: content.nextIssueId(),
        pieceId: m[1],
        tool,
        code: String(r.code ?? "check"),
        title: String(r.title ?? ""),
        detail: (r.detail as string | null) ?? null,
        anchorText: (r.anchorText as string | null) ?? null,
        suggestion: (r.suggestion as string | null) ?? null,
        state: "open",
        runId,
        createdAt: now(),
        updatedAt: now(),
      });
    }
    return ok({ ok: true });
  }],
  ["PATCH", /^\/api\/v1\/content\/pieces\/([^/]+)\/issues\/([^/]+)$/, (m, _q, body) => {
    const issue = state.issues.find((i) => i.id === m[2]);
    if (issue) Object.assign(issue, body, { updatedAt: now() });
    return ok(issue);
  }],

  ["GET", /^\/api\/v1\/social-listening\/config$/, () => ok(state.socialConfig)],
  ["PUT", /^\/api\/v1\/social-listening\/config$/, (_m, _q, body) => { Object.assign(state.socialConfig, body, { updatedAt: now() }); return ok(state.socialConfig); }],
  ["GET", /^\/api\/v1\/social-listening\/queries$/, () => ok(state.queries)],
  ["POST", /^\/api\/v1\/social-listening\/queries$/, (_m, _q, body) => {
    const rows = (Array.isArray(body) ? body : [body]) as Array<Record<string, unknown>>;
    for (const r of rows) {
      state.queries.push({ id: newId("q"), createdAt: now(), updatedAt: now(), siteId: siteData.SITE_ID, text: String(r.text ?? ""), enabled: r.enabled !== false, source: (r.source as "user" | "suggested") ?? "user", keywords: [], negativeKeywords: [], embedded: false });
    }
    return ok(state.queries);
  }],
  ["PATCH", /^\/api\/v1\/social-listening\/queries\/([^/]+)$/, (m, _q, body) => { const q = state.queries.find((x) => x.id === m[1]); if (q) Object.assign(q, body); return ok(q); }],
  ["DELETE", /^\/api\/v1\/social-listening\/queries\/([^/]+)$/, (m) => { state.queries = state.queries.filter((q) => q.id !== m[1]); return ok({ ok: true }); }],
  ["GET", /^\/api\/v1\/social-listening\/targets$/, () => ok(state.targets)],
  ["POST", /^\/api\/v1\/social-listening\/targets$/, (_m, _q, body) => {
    const rows = (Array.isArray(body) ? body : [body]) as Array<Record<string, unknown>>;
    for (const r of rows) {
      state.targets.push({ id: newId("t"), createdAt: now(), updatedAt: now(), siteId: siteData.SITE_ID, kind: (r.kind as "brand" | "competitor") ?? "competitor", name: String(r.name ?? ""), enabled: r.enabled !== false, source: (r.source as SocialListeningTarget["source"]) ?? "user" });
    }
    return ok(state.targets);
  }],
  ["PATCH", /^\/api\/v1\/social-listening\/targets\/([^/]+)$/, (m, _q, body) => { const t = state.targets.find((x) => x.id === m[1]); if (t) Object.assign(t, body); return ok(t); }],
  ["DELETE", /^\/api\/v1\/social-listening\/targets\/([^/]+)$/, (m) => { state.targets = state.targets.filter((t) => t.id !== m[1]); return ok({ ok: true }); }],
  ["GET", /^\/api\/v1\/social-listening\/summary$/, () => ok(socialSummary())],
  ["GET", /^\/api\/v1\/social-listening\/posts$/, (_m, q) => {
    let rows = [...state.posts];
    const kind = q.get("kind");
    if (kind) rows = rows.filter((p) => p.kind === kind);
    const status = q.get("status");
    if (status) rows = rows.filter((p) => p.status === status);
    const platform = q.get("platform");
    if (platform) rows = rows.filter((p) => p.platform === platform);
    const intent = q.get("intent");
    if (intent) rows = rows.filter((p) => p.intent === intent);
    const queryId = q.get("queryId");
    if (queryId) rows = rows.filter((p) => p.queryId === queryId);
    const cls = q.get("cls");
    if (cls) rows = rows.filter((p) => p.classes.includes(cls as SocialListeningPost["classes"][number]));
    const target = q.get("target");
    if (target) rows = rows.filter((p) => p.matchedTargets.includes(target));
    return paginate(sortPosts(rows, q.get("sort")), q);
  }],
  ["PATCH", /^\/api\/v1\/social-listening\/posts\/([^/]+)$/, (m, _q, body) => {
    const post = state.posts.find((p) => p.id === m[1]);
    if (post) Object.assign(post, body, { updatedAt: now(), ...(b(body, "status") === "replied" ? { repliedAt: now() } : {}) });
    return ok(post);
  }],

  ["GET", /^\/api\/v1\/analytics\/workspace$/, () => ok({
    sessions: state.sessions,
    sources: state.sources,
    reports: state.reports.map(({ html, ...r }) => ({ ...r, htmlBytes: html.length })),
  })],
  ["POST", /^\/api\/v1\/analytics\/sessions$/, (_m, _q, body) => {
    const s: AnalyticsSession = { id: newId("as"), createdAt: now(), updatedAt: now(), siteId: siteData.SITE_ID, title: String(b(body, "title") ?? "New session"), about: String(b(body, "about") ?? ""), sessionKey: null };
    state.sessions.unshift(s);
    return ok(s);
  }],
  ["GET", /^\/api\/v1\/analytics\/sessions\/([^/]+)$/, (m) => {
    const s = state.sessions.find((x) => x.id === m[1]);
    if (!s) throw new MockHttpError(404, "No such session.");
    return ok(s);
  }],
  ["PUT", /^\/api\/v1\/analytics\/sessions\/([^/]+)$/, (m, _q, body) => { const s = state.sessions.find((x) => x.id === m[1]); if (s) Object.assign(s, body, { updatedAt: now() }); return ok(s); }],
  ["DELETE", /^\/api\/v1\/analytics\/sessions\/([^/]+)$/, (m) => {
    state.sessions = state.sessions.filter((s) => s.id !== m[1]);
    state.sources = state.sources.filter((s) => s.sessionId !== m[1]);
    state.reports = state.reports.filter((r) => r.sessionId !== m[1]);
    return ok({ ok: true });
  }],
  ["GET", /^\/api\/v1\/analytics\/sessions\/([^/]+)\/sources$/, (m) => ok(state.sources.filter((s) => s.sessionId === m[1]))],
  ["POST", /^\/api\/v1\/analytics\/sessions\/([^/]+)\/sources$/, (m, _q, body) => {
    const name = String(b(body, "name") ?? "source.csv");
    const s: AnalyticsSource = { id: newId("src"), createdAt: now(), updatedAt: now(), siteId: siteData.SITE_ID, sessionId: m[1], name, filePath: (b(body, "filePath") as string | undefined) ?? `analytics/${m[1]}/${name}` };
    state.sources.push(s);
    return ok(s);
  }],
  ["DELETE", /^\/api\/v1\/analytics\/sources\/([^/]+)$/, (m) => { state.sources = state.sources.filter((s) => s.id !== m[1]); return ok({ ok: true }); }],
  ["GET", /^\/api\/v1\/analytics\/reports$/, (_m, q) => {
    const sessionId = q.get("sessionId");
    const rows = state.reports.filter((r) => !sessionId || r.sessionId === sessionId).map(({ html, ...r }) => ({ ...r, htmlBytes: html.length }));
    return paginate(rows, q);
  }],
  ["GET", /^\/api\/v1\/analytics\/reports\/([^/]+)$/, (m) => {
    const r = state.reports.find((x) => x.id === m[1]);
    if (!r) throw new MockHttpError(404, "No such report.");
    return ok(r);
  }],
  ["DELETE", /^\/api\/v1\/analytics\/reports\/([^/]+)$/, (m) => { state.reports = state.reports.filter((r) => r.id !== m[1]); return ok({ ok: true }); }],
];

export interface MockResponse {
  status: number;
  payload: unknown;
}

export function route(method: string, path: string, body?: unknown): MockResponse {
  const url = new URL(path, "http://demo.local");
  const pathname = url.pathname.replace(/\/$/, "") || "/";
  for (const [m, re, handler] of ROUTES) {
    if (m !== method.toUpperCase()) continue;
    const match = pathname.match(re);
    if (!match) continue;
    try {
      const payload = handler(match, url.searchParams, (body ?? {}) as Record<string, unknown>);
      return { status: 200, payload };
    } catch (e) {
      if (e instanceof MockHttpError) return { status: e.status, payload: { error: { message: e.message, ...e.extra } } };
      throw e;
    }
  }
  return { status: 404, payload: { error: { message: `The demo has no data for ${method} ${pathname}.` } } };
}

export async function mockFetch(method: string, path: string, body?: unknown): Promise<MockResponse> {
  const wait = 90 + Math.random() * 160;
  await new Promise((r) => setTimeout(r, wait));
  return route(method, path, body);
}

export function markCrawled(): void {
  state.lastCrawledAt = now();
  state.site.lastCrawledAt = state.lastCrawledAt;
}

export function addReport(sessionId: string, title: string, html: string): AnalyticsReport {
  const r: AnalyticsReport = { id: newId("rp"), createdAt: now(), updatedAt: now(), siteId: siteData.SITE_ID, sessionId, title, html, createdBy: "agent" };
  state.reports.unshift(r);
  return r;
}

export const demoTimes = { ago, DAY, HOUR, NOW };
