import { crawlSite, MAX_PAGES, type CrawlOptions } from "@/lib/seo-audit/crawl";
import { BROWSER_USER_AGENT, fetchUrl, pool } from "@/lib/seo-audit/net";
import { normalise, sameSite } from "@/lib/seo-audit/url";
import { isOk } from "@/lib/seo-audit/checks";
import type { AuditError, Page } from "@/lib/seo-audit/types";
import type {
  CheckedLink,
  LinkCheckResult,
  LinkSource,
  LinkState,
} from "./types";

export const MAX_LINKS = 750;
/** Longer than the SEO audit: this one crawls and then probes every link. */
const LINK_CHECK_BUDGET_MS = 110_000;
const PROBE_CONCURRENCY = 24;
const PROBE_TIMEOUT_MS = 12_000;
const SOURCES_PER_LINK = 8;

/** Answers that mean "we were refused", not "the page is gone". */
const REFUSAL = new Set([401, 403, 405, 406, 429, 999]);

/** Worth a second try with a browser user agent; 429 is not — it would just
 *  be refused again and cost the other server another request. */
const WORTH_RETRYING = new Set([401, 403, 405, 406, 501]);

const PER_HOST_CONCURRENCY = 3;

/**
 * Keeps one busy host from swallowing the whole batch, and keeps us from
 * looking like an attack to any single server. A freed slot is handed straight
 * to the next waiter rather than released and re-contested — re-contesting
 * loses the handover when the queue is momentarily empty, and the waiter then
 * sleeps forever.
 */
function hostGate(limit: number) {
  const active = new Map<string, number>();
  const waiting = new Map<string, Array<() => void>>();

  const acquire = (host: string): Promise<void> => {
    const running = active.get(host) ?? 0;
    if (running < limit) {
      active.set(host, running + 1);
      return Promise.resolve();
    }
    return new Promise<void>((resolve) => {
      const queue = waiting.get(host) ?? [];
      queue.push(resolve);
      waiting.set(host, queue);
    });
  };

  const release = (host: string) => {
    const next = waiting.get(host)?.shift();
    // The slot passes to the waiter, so the count does not change.
    if (next) {
      next();
      return;
    }
    active.set(host, Math.max(0, (active.get(host) ?? 1) - 1));
  };

  return async <T>(host: string, work: () => Promise<T>): Promise<T> => {
    await acquire(host);
    try {
      return await work();
    } finally {
      release(host);
    }
  };
}

function hostOf(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

export type LinkCheckOptions = CrawlOptions & {
  /** Check <img src> as well as <a href>. */
  includeImages?: boolean;
  maxLinks?: number;
};

export type LinkCheckOutcome =
  | { ok: true; result: LinkCheckResult }
  | { ok: false; error: AuditError };

type Target = {
  url: string;
  side: "internal" | "external";
  asset: "link" | "image";
  sources: LinkSource[];
  sourceCount: number;
};

function collect(
  pages: Page[],
  origin: string,
  includeImages: boolean,
): Map<string, Target> {
  const targets = new Map<string, Target>();

  const add = (
    raw: string,
    asset: "link" | "image",
    source: LinkSource,
  ) => {
    let url: string;
    try {
      url = normalise(raw);
      const parsed = new URL(url);
      if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return;
    } catch {
      return;
    }
    const key = `${asset}:${url}`;
    const existing = targets.get(key);
    if (existing) {
      existing.sourceCount += 1;
      if (existing.sources.length < SOURCES_PER_LINK) existing.sources.push(source);
      return;
    }
    targets.set(key, {
      url,
      side: sameSite(url, origin) ? "internal" : "external",
      asset,
      sources: [source],
      sourceCount: 1,
    });
  };

  for (const page of pages) {
    if (!isOk(page)) continue;
    for (const link of [...page.outLinks, ...page.externalLinks]) {
      add(link.url, "link", {
        page: page.url,
        anchor: link.anchor || "(no anchor text)",
        rel: link.rel,
      });
    }
    if (includeImages) {
      for (const image of page.images) {
        add(image.src, "image", {
          page: page.url,
          anchor: image.alt ? `alt: ${image.alt}` : "(no alt text)",
          rel: null,
        });
      }
    }
  }

  return targets;
}

/** Spreads same-host targets apart so no one server takes the whole batch. */
function interleaveByHost(targets: Target[]): Target[] {
  const byHost = new Map<string, Target[]>();
  for (const target of targets) {
    let host: string;
    try {
      host = new URL(target.url).hostname;
    } catch {
      host = "";
    }
    const list = byHost.get(host) ?? [];
    list.push(target);
    byHost.set(host, list);
  }
  const queues = [...byHost.values()];
  const out: Target[] = [];
  let drained = false;
  while (!drained) {
    drained = true;
    for (const queue of queues) {
      const next = queue.shift();
      if (next) {
        out.push(next);
        drained = false;
      }
    }
  }
  return out;
}

function describeError(message: string): { state: LinkState; reason: string } {
  const lower = message.toLowerCase();
  if (lower.includes("timeout") || lower.includes("timed out") || lower.includes("abort")) {
    return { state: "no-answer", reason: "No answer within 12 seconds" };
  }
  if (
    lower.includes("enotfound") ||
    lower.includes("getaddrinfo") ||
    lower.includes("dns")
  ) {
    return { state: "broken", reason: "The domain does not resolve — it is gone or misspelled" };
  }
  if (lower.includes("econnrefused") || lower.includes("connection refused")) {
    return { state: "broken", reason: "The server refused the connection" };
  }
  if (lower.includes("certificate") || lower.includes("ssl") || lower.includes("tls")) {
    return { state: "broken", reason: "The HTTPS certificate could not be verified" };
  }
  return { state: "no-answer", reason: `The request failed: ${message.slice(0, 120)}` };
}

function statusReason(status: number): string {
  if (status === 404) return "HTTP 404 — page not found";
  if (status === 410) return "HTTP 410 — page permanently removed";
  if (status === 400) return "HTTP 400 — the server rejected the URL as malformed";
  if (status >= 500) return `HTTP ${status} — server error`;
  return `HTTP ${status}`;
}

async function probe(target: Target, signal?: AbortSignal): Promise<CheckedLink> {
  const base: Omit<CheckedLink, "state" | "reason"> = {
    url: target.url,
    status: null,
    side: target.side,
    asset: target.asset,
    redirectTo: null,
    redirectHops: 0,
    responseMs: null,
    sources: target.sources,
    sourceCount: target.sourceCount,
  };

  // HEAD first: it is the polite request, and most servers answer it honestly.
  let res = await fetchUrl(target.url, {
    method: "HEAD",
    timeoutMs: PROBE_TIMEOUT_MS,
    htmlOnly: false,
    accept: "*/*",
    signal,
  });

  const headRefused =
    res.error !== undefined ||
    res.status === undefined ||
    WORTH_RETRYING.has(res.status);

  // A refusal is not proof of a dead link, so ask again the way a reader would.
  if (headRefused && !res.blockedReason) {
    res = await fetchUrl(target.url, {
      method: "GET",
      timeoutMs: PROBE_TIMEOUT_MS,
      htmlOnly: false,
      accept: "text/html,application/xhtml+xml,*/*;q=0.8",
      userAgent: BROWSER_USER_AGENT,
      signal,
    });
  }

  const hops = res.chain.length;
  const redirectTo = hops > 0 ? res.chain[hops - 1].to : null;
  const common = {
    ...base,
    redirectHops: hops,
    redirectTo,
    responseMs: res.responseMs,
  };

  if (res.blockedReason) {
    return { ...common, state: "blocked", reason: res.blockedReason };
  }
  if (res.loop) {
    return { ...common, state: "broken", reason: "The URL redirects in a loop" };
  }
  if (res.tooManyHops) {
    return {
      ...common,
      state: "broken",
      reason: "The URL redirects more than five times without landing",
    };
  }
  if (res.error !== undefined) {
    return { ...common, ...describeError(res.error) };
  }

  const status = res.status ?? null;
  if (status === null) {
    return { ...common, state: "no-answer", reason: "The server sent no status" };
  }

  if (status >= 400) {
    if (REFUSAL.has(status)) {
      return {
        ...common,
        status,
        state: "blocked",
        reason: `HTTP ${status} — the server refused an automated request. Often bot protection rather than a dead page; open it in a browser to be sure.`,
      };
    }
    return { ...common, status, state: "broken", reason: statusReason(status) };
  }

  if (hops > 0) {
    return {
      ...common,
      status,
      state: "redirect",
      reason: `${hops} redirect${hops === 1 ? "" : "s"} to ${redirectTo}`,
    };
  }

  return { ...common, status, state: "ok", reason: `HTTP ${status}` };
}

export async function runLinkCheck(
  rawInput: string,
  options: LinkCheckOptions = {},
): Promise<LinkCheckOutcome> {
  const { includeImages = true, maxLinks = MAX_LINKS } = options;

  const outcome = await crawlSite(rawInput, { budgetMs: LINK_CHECK_BUDGET_MS, ...options });
  if (!outcome.ok) return outcome;

  const {
    origin,
    scope,
    startedAt,
    startTime,
    outOfTime,
    emit,
    signal,
    pages,
    byUrl,
    hitCap,
    notes,
  } = outcome.crawl;

  const targets = collect(pages, origin, includeImages);
  const linksFound = targets.size;

  // Pages we already fetched need no second request — their status is known.
  const known: CheckedLink[] = [];
  const toProbe: Target[] = [];
  for (const target of targets.values()) {
    const crawled = target.asset === "link" ? byUrl.get(target.url) : undefined;
    if (crawled && crawled.status !== null && crawled.state !== "blocked") {
      const status = crawled.status;
      const hops = crawled.redirectHops;
      const state: LinkState =
        status >= 400
          ? REFUSAL.has(status)
            ? "blocked"
            : "broken"
          : hops > 0
            ? "redirect"
            : "ok";
      known.push({
        url: target.url,
        state,
        status,
        reason:
          state === "broken"
            ? statusReason(status)
            : state === "blocked"
              ? `HTTP ${status} — the server refused an automated request`
              : hops > 0
                ? `${hops} redirect${hops === 1 ? "" : "s"} to ${crawled.redirectTo}`
                : `HTTP ${status}`,
        side: target.side,
        asset: target.asset,
        redirectTo: crawled.redirectTo,
        redirectHops: hops,
        responseMs: crawled.responseMs,
        sources: target.sources,
        sourceCount: target.sourceCount,
      });
      continue;
    }
    toProbe.push(target);
  }

  const ordered = interleaveByHost(toProbe);
  const budget = ordered.slice(0, Math.max(0, maxLinks));
  const skipped = ordered.length - budget.length;

  emit({
    type: "phase",
    message: `Checking ${budget.length + known.length} link${
      budget.length + known.length === 1 ? "" : "s"
    }`,
  });

  const checked: CheckedLink[] = [];
  const gate = hostGate(PER_HOST_CONCURRENCY);
  // A belt-and-braces deadline: even a wedged socket cannot outlive the run.
  const remaining = Math.max(1_000, LINK_CHECK_BUDGET_MS - (Date.now() - startTime));
  const deadline = AbortSignal.timeout(remaining);
  const probeSignal = signal ? AbortSignal.any([signal, deadline]) : deadline;
  let done = 0;
  let ranOut = false;

  await pool(budget, PROBE_CONCURRENCY, async (target) => {
    if (signal?.aborted || deadline.aborted || outOfTime()) {
      ranOut = true;
      return;
    }
    const link = await gate(hostOf(target.url), () => probe(target, probeSignal));
    checked.push(link);
    done += 1;
    if (done % 5 === 0 || done === budget.length) {
      emit({ type: "progress", fetched: done, total: budget.length, queued: 0 });
    }
  });

  const links = [...known, ...checked];
  const uncheckedCount = skipped + (ranOut ? budget.length - checked.length : 0);

  if (skipped > 0) {
    notes.push(
      `${skipped} link(s) were found but not checked — the tool stops at ${maxLinks} destinations that need a request. Links to pages already read during the crawl cost nothing and are always checked.`,
    );
  }
  if (ranOut) {
    notes.push(
      "The run reached its time limit before every link was checked. Everything already checked is in the table.",
    );
  }
  if (includeImages) {
    notes.push("Image sources were checked alongside links.");
  }

  const rank: Record<LinkState, number> = {
    broken: 0,
    blocked: 1,
    "no-answer": 2,
    redirect: 3,
    ok: 4,
    unchecked: 5,
  };
  links.sort(
    (a, b) =>
      rank[a.state] - rank[b.state] ||
      b.sourceCount - a.sourceCount ||
      a.url.localeCompare(b.url),
  );

  const count = (state: LinkState) => links.filter((l) => l.state === state).length;
  const broken = links.filter((l) => l.state === "broken");

  const brokenByPage = new Map<string, number>();
  for (const link of broken) {
    for (const source of link.sources) {
      brokenByPage.set(source.page, (brokenByPage.get(source.page) ?? 0) + 1);
    }
  }

  const result: LinkCheckResult = {
    input: rawInput.trim(),
    origin,
    scope,
    startedAt,
    summary: {
      pagesCrawled: pages.filter(isOk).length,
      linksFound,
      linksChecked: links.length,
      uncheckedCount,
      broken: broken.length,
      redirects: count("redirect"),
      blocked: count("blocked"),
      noAnswer: count("no-answer"),
      ok: count("ok"),
      brokenInternal: broken.filter((l) => l.side === "internal").length,
      brokenExternal: broken.filter((l) => l.side === "external").length,
      brokenImages: broken.filter((l) => l.asset === "image").length,
      durationMs: Date.now() - startTime,
      limitReached: hitCap,
    },
    links,
    pages: pages
      .filter(isOk)
      .map((page) => ({
        url: page.url,
        status: page.status,
        linksOut:
          page.outLinks.length +
          page.externalLinks.length +
          (includeImages ? page.images.length : 0),
        broken: brokenByPage.get(page.url) ?? 0,
      }))
      .sort((a, b) => b.broken - a.broken),
    notes,
  };

  return { ok: true, result };
}

export { MAX_PAGES };
