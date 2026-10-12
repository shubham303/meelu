import { classify, extract } from "./extract";
import { fetchUrl, looksLikeBotChallenge, pool, sleep } from "./net";
import { robotsAllows, sitemapsIn } from "./robots";
import { discoverSitemaps, readSitemaps } from "./sitemap";
import {
  BINARY_PATH,
  looksLikeSitemap,
  normalise,
  parseInput,
  repeatsSegments,
  sameHost,
} from "./url";
import type { AuditError, Page, Robots, StreamEvent } from "./types";

export const MAX_PAGES = 100;
const CONCURRENCY = 5;
const DELAY_MS = 120;
export const TOTAL_BUDGET_MS = 100_000;
const CRAWL_SHARE = 0.55;
const GOOGLEBOT = "Googlebot";
const OUR_AGENT = "MeeluSEOAudit";

const REFUSAL = new Set([401, 402, 403, 405, 418, 429, 451]);

const blankPage = (url: string, inSitemap: boolean): Page => ({
  url,
  status: null,
  state: "error",
  fetchError: null,
  contentType: null,
  responseMs: null,
  bytes: null,
  redirectHops: 0,
  redirectTo: null,
  redirectChain: [],
  inSitemap,
  blockedByRobots: false,
  depth: null,
  inlinks: 0,
  kind: "other",
  format: null,
  title: null,
  titlePixels: null,
  metaDescription: null,
  h1: [],
  headings: [],
  bodyText: "",
  wordCount: 0,
  outLinks: [],
  externalLinks: [],
  canonical: null,
  robotsDirectives: null,
  xRobotsTag: null,
  hasViewport: false,
  lang: null,
  hreflang: {},
  schemaTypes: [],
  schemaNodes: [],
  images: [],
  mixedContent: false,
  openGraph: false,
  twitterCard: false,
  favicon: false,
  ampHtml: null,
  noindexHeaderOnly: false,
});

export type CrawlOptions = {
  scope?: "auto" | "page";
  maxPages?: number;
  /** Wall clock for the whole run, crawl and whatever follows it. */
  budgetMs?: number;
  onEvent?: (event: StreamEvent) => void;
  signal?: AbortSignal;
};

/** Everything both tools need from one pass over a site. */
export type Crawl = {
  input: string;
  origin: string;
  scope: "site" | "sitemap" | "page";
  startedAt: string;
  startTime: number;
  outOfTime: () => boolean;
  emit: (event: StreamEvent) => void;
  maxPages: number;
  signal?: AbortSignal;
  pages: Page[];
  byUrl: Map<string, Page>;
  seen: Set<string>;
  blockedSeen: Set<string>;
  hitCap: boolean;
  robots: Robots;
  robotsBody: string | null;
  llmsStatus: number | null;
  sitemapsUsed: string[];
  sitemapUrlCount: number;
  sitemapAtRoot: boolean;
  notes: string[];
};

export type CrawlOutcome =
  | { ok: true; crawl: Crawl }
  | { ok: false; error: AuditError };

/**
 * One pass over a site: resolve the host, read robots.txt, find the sitemap and
 * fetch up to `maxPages` URLs. Both the SEO audit and the link checker run on
 * top of this — they differ only in what they do with the pages afterwards.
 */
export async function crawlSite(
  rawInput: string,
  options: CrawlOptions = {},
): Promise<CrawlOutcome> {
  const {
    scope: requested = "auto",
    maxPages = MAX_PAGES,
    budgetMs = TOTAL_BUDGET_MS,
    onEvent,
    signal,
  } = options;
  const startedAt = new Date().toISOString();
  const startTime = Date.now();
  const outOfTime = () => Date.now() - startTime > budgetMs;
  // The crawl gives up early so the step after it is not left with nothing.
  const crawlOutOfTime = () => Date.now() - startTime > budgetMs * CRAWL_SHARE;
  const emit = (event: StreamEvent) => onEvent?.(event);
  const notes: string[] = [];

  const parsed = parseInput(rawInput);
  if (!parsed) {
    return {
      ok: false,
      error: {
        code: "invalid-url",
        message: "That does not look like a website address.",
        hint: "Try something like example.com, https://example.com/pricing or https://example.com/sitemap.xml.",
      },
    };
  }

  const startUrl = normalise(parsed.toString());
  const scope: "site" | "sitemap" | "page" =
    requested === "page" ? "page" : looksLikeSitemap(parsed) ? "sitemap" : "site";

  emit({ type: "phase", message: `Fetching ${parsed.hostname}` });

  // The first request settles three things at once: whether the site answers,
  // which host form it settles on, and whether anything is standing in the way.
  const probeUrl =
    scope === "sitemap" ? `${parsed.protocol}//${parsed.host}/` : startUrl;
  const probe = await fetchUrl(probeUrl, { timeoutMs: 20_000, signal });

  if (probe.blockedReason) {
    return { ok: false, error: { code: "private-address", message: probe.blockedReason } };
  }
  if (probe.error) {
    return {
      ok: false,
      error: {
        code: "unreachable",
        message: `${parsed.hostname} did not answer.`,
        hint: `The request failed with: ${probe.error}. Check the address, and whether the site serves on www or without it — those are separate hosts unless one redirects to the other.`,
      },
    };
  }
  if (probe.loop || probe.tooManyHops) {
    return {
      ok: false,
      error: {
        code: "unreachable",
        message: probe.loop
          ? "That URL redirects in a loop."
          : "That URL redirects more than five times before landing anywhere.",
      },
    };
  }
  if (probe.status !== undefined && REFUSAL.has(probe.status)) {
    return {
      ok: false,
      error: {
        code: "http-refused",
        message: `Crawling blocked — the site answered HTTP ${probe.status}.`,
        hint:
          probe.status === 403 || probe.status === 401
            ? "The server refused an ordinary crawler. A firewall, WAF or login wall is usually the cause. Googlebot may be allowed where this tool is not — check your server or CDN's bot rules."
            : "The server is rate-limiting or refusing automated requests. Try again later, or allow the MeeluSEOAudit user agent.",
      },
    };
  }
  if (looksLikeBotChallenge(probe.html)) {
    return {
      ok: false,
      error: {
        code: "bot-protection",
        message: "Crawling blocked — the site served a bot-protection challenge.",
        hint: "Cloudflare or a similar service is showing an interstitial instead of the page. Allow the MeeluSEOAudit user agent, or run the audit from inside your own network.",
      },
    };
  }

  const finalStart = probe.finalUrl ?? probeUrl;
  const origin = new URL(finalStart).origin;
  if (probe.chain.length > 0 && scope !== "sitemap") {
    notes.push(
      `${probeUrl} redirects to ${finalStart}, so that is the address the audit read.`,
    );
  }

  emit({ type: "phase", message: "Reading robots.txt" });
  const [robotsRes, llmsRes] = await Promise.all([
    fetchUrl(new URL("/robots.txt", origin).toString(), {
      timeoutMs: 10_000,
      accept: "text/plain,*/*",
      htmlOnly: false,
      signal,
    }),
    fetchUrl(new URL("/llms.txt", origin).toString(), {
      timeoutMs: 10_000,
      accept: "text/plain,text/markdown,*/*",
      htmlOnly: false,
      signal,
    }),
  ]);

  const robotsBody = robotsRes.status === 200 ? (robotsRes.text ?? "") : null;
  const robots: Robots = {
    fetched: robotsRes.status !== undefined,
    status: robotsRes.status ?? null,
    body: robotsBody,
    error: robotsRes.error ?? robotsRes.blockedReason ?? null,
    sitemaps: robotsBody ? sitemapsIn(robotsBody) : [],
  };

  const mayFetch = (url: string): boolean => {
    if (!robotsBody) return true;
    const path = new URL(url).pathname + new URL(url).search;
    return (
      robotsAllows(robotsBody, OUR_AGENT, path) &&
      robotsAllows(robotsBody, GOOGLEBOT, path)
    );
  };
  const blockedForGooglebot = (url: string): boolean => {
    if (!robotsBody) return false;
    const path = new URL(url).pathname + new URL(url).search;
    return !robotsAllows(robotsBody, GOOGLEBOT, path);
  };

  if (robotsBody && !robotsAllows(robotsBody, GOOGLEBOT, "/") && scope !== "page") {
    return {
      ok: false,
      error: {
        code: "robots-disallow",
        message: "Crawling blocked — robots.txt disallows the whole site.",
        hint: `${origin}/robots.txt contains a rule that stops Googlebot at "/". Nothing under it can be crawled or indexed until that rule changes.`,
      },
    };
  }
  if (robotsBody && !mayFetch(finalStart)) {
    return {
      ok: false,
      error: {
        code: "robots-disallow",
        message: "Crawling blocked — robots.txt disallows that URL.",
        hint: `${origin}/robots.txt has a Disallow rule covering ${new URL(finalStart).pathname}. Search engines will not fetch it either.`,
      },
    };
  }

  // Build the list of URLs to read.
  let worklist: string[] = [];
  let sitemapUrls: string[] = [];
  let sitemapsUsed: string[] = [];
  let sitemapAtRoot = false;
  let sitemapUrlCount = 0;

  if (scope === "page") {
    worklist = [finalStart];
  } else if (scope === "sitemap") {
    emit({ type: "phase", message: "Reading the sitemap" });
    const read = await readSitemaps([startUrl], maxPages * 4, 0, signal);
    if (read.urls.length === 0) {
      return {
        ok: false,
        error: {
          code: "no-urls",
          message: "That sitemap could not be read, or lists no URLs.",
          hint: "Check the address opens in a browser and returns XML with <loc> entries. Gzipped sitemaps (.xml.gz) are not supported here — point at the uncompressed file or the sitemap index.",
        },
      };
    }
    sitemapsUsed = read.used;
    sitemapUrls = read.urls;
    sitemapUrlCount = read.urls.length;
    sitemapAtRoot = read.used.includes(new URL("/sitemap.xml", origin).toString());
    worklist = [...new Set(read.urls.map(normalise))];
  } else {
    emit({ type: "phase", message: "Looking for a sitemap" });
    const found = await discoverSitemaps(origin, robots.sitemaps, maxPages * 4, signal);
    sitemapsUsed = found.used;
    sitemapAtRoot = found.atRoot;
    sitemapUrls = found.urls;
    const onHost = [...new Set(found.urls.filter((u) => sameHost(u, origin)).map(normalise))];
    sitemapUrlCount = onHost.length;
    const offHost = found.urls.length - onHost.length;
    if (offHost > 0) {
      notes.push(`${offHost} sitemap URL(s) point at another host and were left alone.`);
    }
    worklist = onHost.length > 0 ? [finalStart, ...onHost] : [finalStart];
    if (onHost.length === 0) {
      notes.push(
        "No sitemap was found, so the audit followed links from the start URL instead.",
      );
    }
  }

  worklist = [...new Set(worklist)];
  const inSitemap = new Set(scope === "page" ? [] : worklist.filter((u) => sitemapUrls.map(normalise).includes(u)));

  const pages: Page[] = [];
  const byUrl = new Map<string, Page>();
  const seen = new Set(worklist);
  const depths = new Map<string, number>([[finalStart, 0]]);
  const queue = [...worklist];
  const linkQueue: string[] = [];
  const blockedSeen = new Set<string>();
  let fetched = 0;
  let hitCap = false;

  const enqueueLink = (raw: string, from: string) => {
    if (scope === "page") return;
    const url = normalise(raw);
    if (seen.has(url) || !sameHost(url, origin)) return;
    if (BINARY_PATH.test(new URL(url).pathname) || repeatsSegments(url)) return;
    seen.add(url);
    depths.set(url, (depths.get(from) ?? 0) + 1);
    if (blockedForGooglebot(url)) {
      if (!blockedSeen.has(url)) {
        blockedSeen.add(url);
        const page = blankPage(url, inSitemap.has(url));
        page.state = "blocked";
        page.blockedByRobots = true;
        page.depth = depths.get(url) ?? null;
        pages.push(page);
        byUrl.set(url, page);
      }
      return;
    }
    linkQueue.push(url);
  };

  const record = (res: Awaited<ReturnType<typeof fetchUrl>>, url: string) => {
    const page = blankPage(url, inSitemap.has(url));
    page.depth = depths.get(url) ?? null;
    page.redirectChain = res.chain;
    page.redirectHops = res.chain.length;
    page.responseMs = res.responseMs;
    page.bytes = res.bytes;
    page.contentType = res.contentType;
    page.xRobotsTag = res.xRobotsTag;

    if (res.chain.length > 0) {
      page.redirectTo = res.chain[res.chain.length - 1].to;
      page.status = res.chain[0].status;
      page.state = "redirect";
      enqueueLink(page.redirectTo, url);
      if (res.loop || res.tooManyHops) {
        page.fetchError = res.loop ? "redirect loop" : "more than five redirects";
        pages.push(page);
        byUrl.set(url, page);
        return;
      }
    }

    if (res.blockedReason || res.error) {
      page.state = "error";
      page.fetchError = (res.blockedReason ?? res.error ?? "").slice(0, 200);
      pages.push(page);
      byUrl.set(url, page);
      return;
    }

    if (res.status !== undefined && res.chain.length === 0) page.status = res.status;

    if (res.status !== undefined && res.status >= 400) {
      page.state = "error";
      page.status = res.status;
      pages.push(page);
      byUrl.set(url, page);
      return;
    }

    if (!res.html) {
      page.state = "not-html";
      pages.push(page);
      byUrl.set(url, page);
      return;
    }

    // A URL that redirects is recorded at the address that was asked for, and
    // the page itself is read at the address it landed on.
    const landed = res.finalUrl ?? url;
    const facts = extract(res.html, landed);
    Object.assign(page, facts);
    page.state = res.chain.length > 0 ? "redirect" : "ok";
    if (res.chain.length === 0) {
      page.status = res.status ?? 200;
      page.kind = classify(landed, origin, facts.schemaTypes);
      page.noindexHeaderOnly =
        /noindex/i.test(res.xRobotsTag ?? "") && !/noindex/i.test(facts.robotsDirectives ?? "");
      for (const link of facts.outLinks) {
        if (link.rel && /nofollow/i.test(link.rel)) continue;
        enqueueLink(link.url, url);
      }
    }
    pages.push(page);
    byUrl.set(url, page);
  };

  const drain = async (source: string[], phase: string) => {
    while (source.length > 0 && fetched < maxPages) {
      if (signal?.aborted) return;
      if (crawlOutOfTime()) {
        hitCap = true;
        notes.push(
          `The crawl stopped after ${fetched} page(s) — it reached its time limit rather than keep the site busy.`,
        );
        return;
      }
      const batch: string[] = [];
      while (source.length > 0 && batch.length < CONCURRENCY && fetched + batch.length < maxPages) {
        const url = source.shift()!;
        if (blockedForGooglebot(url)) {
          if (!blockedSeen.has(url)) {
            blockedSeen.add(url);
            const page = blankPage(url, inSitemap.has(url));
            page.state = "blocked";
            page.blockedByRobots = true;
            pages.push(page);
            byUrl.set(url, page);
          }
          continue;
        }
        batch.push(url);
      }
      if (batch.length === 0) continue;

      const results = await pool(batch, CONCURRENCY, (url) =>
        fetchUrl(url, { timeoutMs: 15_000, signal }),
      );
      batch.forEach((url, i) => record(results[i], url));
      fetched += batch.length;
      emit({
        type: "progress",
        fetched,
        total: maxPages,
        queued: source.length + (phase === "sitemap" ? linkQueue.length : 0),
      });
      await sleep(DELAY_MS);
    }
    if (source.length > 0) hitCap = true;
  };

  emit({ type: "phase", message: `Reading ${Math.min(worklist.length, maxPages)} page(s)` });
  await drain(queue, "sitemap");
  if (fetched < maxPages && !hitCap && scope !== "page") {
    await drain(linkQueue, "links");
  }
  if (linkQueue.length > 0 && fetched >= maxPages) hitCap = true;

  if (pages.length === 0) {
    return {
      ok: false,
      error: {
        code: "no-urls",
        message: "Nothing could be read at that address.",
      },
    };
  }
  return {
    ok: true,
    crawl: {
      input: rawInput.trim(),
      origin,
      scope,
      startedAt,
      startTime,
      outOfTime,
      emit,
      maxPages,
      signal,
      pages,
      byUrl,
      seen,
      blockedSeen,
      hitCap,
      robots,
      robotsBody,
      llmsStatus: llmsRes.status ?? null,
      sitemapsUsed,
      sitemapUrlCount,
      sitemapAtRoot,
      notes,
    },
  };
}
