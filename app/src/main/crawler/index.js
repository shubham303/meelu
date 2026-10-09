import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";
import { runRender } from "../render/index.js";
import { crawlSite } from "./crawler.js";
import { crawlToken } from "./token.js";

const running = new Map();

const OUTLINK_BATCH = 100;

function api(path, { method = "GET", body, siteId, cookieHeader } = {}) {
  const headers = {
    ...meeluAuthHeaders(cookieHeader),
    ...(body ? { "content-type": "application/json" } : {}),
    ...(siteId ? { "x-meelu-site": siteId } : {}),
  };
  return apiFetch(`${ENV_DEFAULTS.meeluBaseUrl}/api/v1${path}`, {
    method,
    headers,
    ...(body ? { body: JSON.stringify(body) } : {}),
  }).then(async (res) => {
    const json = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(json?.error?.message ?? `${method} ${path} failed (${res.status})`);
    }
    return json?.data ?? json;
  });
}

export function requestCrawlStop(jobId) {
  const live = running.get(jobId);
  if (!live) return false;
  live.stop = true;
  return true;
}

export async function runCrawl(params, emit, options = {}) {
  if (params?.render === "desktop" || params?.render === "mobile") {
    const { render, ...rest } = params;
    return runRender({ ...rest, device: render }, options.emitRender ?? emit, options);
  }
  const { siteId, freshDays, sitemapUrls, trigger = "user" } = params ?? {};
  const cookieHeader = options.cookieHeader ?? "";
  if (!siteId) throw new Error("A crawl needs a website — no siteId was passed.");

  const opened = await api("/site/crawl-jobs", {
    method: "POST",
    siteId,
    cookieHeader,
    body: {
      trigger,
      ...(Number.isFinite(Number(freshDays)) ? { freshDays: Number(freshDays) } : {}),
      ...(Array.isArray(sitemapUrls) ? { sitemapUrls } : {}),
    },
  });

  if (!opened.started) {
    emit("crawl:done", {
      ok: false,
      jobId: opened.job?.id ?? null,
      siteId,
      error: opened.reason ?? "A crawl of this website is already running.",
    });
    return { jobId: opened.job?.id ?? null, started: false, reason: opened.reason };
  }

  const jobId = opened.job.id;
  running.set(jobId, { stop: false });
  void drive(jobId, siteId, cookieHeader, emit).finally(() => running.delete(jobId));
  return { jobId, siteId, started: true };
}

async function saveOutlinks(pages, siteId, cookieHeader) {
  const withLinks = pages
    .filter((p) => Array.isArray(p.links))
    .map((p) => ({ url: p.url, links: p.links }));
  const unresolved = new Set();
  for (let i = 0; i < withLinks.length; i += OUTLINK_BATCH) {
    const res = await api("/site/pages/links", {
      method: "POST",
      siteId,
      cookieHeader,
      body: { pages: withLinks.slice(i, i + OUTLINK_BATCH) },
    });
    for (const url of res.unresolved ?? []) unresolved.add(url);
  }
  return [...unresolved];
}

async function drive(jobId, siteId, cookieHeader, broadcast) {
  const emit = (event, data) => broadcast(event, { jobId, siteId, ...data });
  let plan;
  try {
    plan = await api(`/site/crawl-jobs/${jobId}/claim`, {
      method: "POST",
      siteId,
      cookieHeader,
    });
  } catch (e) {
    emit("crawl:done", { ok: false, error: readable(e) });
    return;
  }

  const target = plan.target;
  emit("crawl:started", { domain: target.domain, known: plan.known.length });

  let stored = 0;
  let progress = { fetched: 0, queued: 0, skipped: 0, seen: 0 };
  let sweepReliable = true;

  const savePages = async (batch) => {
    const rows = batch.map(({ state, links, ...rest }) => {
      void state;
      void links;
      return rest;
    });
    try {
      const res = await api("/site/pages", {
        method: "POST",
        siteId,
        cookieHeader,
        body: { pages: rows },
      });
      stored += res.pages ?? 0;
    } catch (e) {
      sweepReliable = false;
      throw e;
    }
  };

  const markVisited = async (urls) => {
    try {
      for (let i = 0; i < urls.length; i += 500) {
        await api("/site/pages/visited", {
          method: "POST",
          siteId,
          cookieHeader,
          body: { urls: urls.slice(i, i + 500) },
        });
      }
    } catch (e) {
      sweepReliable = false;
      throw e;
    }
  };

  const sweepStarted = await api("/site/pages/visited", {
    method: "POST",
    siteId,
    cookieHeader,
    body: { reset: true },
  })
    .then(() => true)
    .catch(() => false);

  try {
    const result = await crawlSite(target.domain, plan.known, {
      concurrency: plan.concurrency,
      batchSize: plan.batchSize,
      sitemapUrls: plan.sitemapUrls,
      linkFrontier: plan.linkFrontier ?? [],
      crawlToken: crawlToken(target.domain),
      freshBefore: plan.freshBefore ?? undefined,
      shouldStop: async () => {
        if (running.get(jobId)?.stop) return true;
        const beat = await api(`/site/crawl-jobs/${jobId}`, {
          method: "PATCH",
          siteId,
          cookieHeader,
          body: { heartbeat: true, ...progress },
        }).catch(() => null);
        return beat?.stop === true;
      },
      onBatch: savePages,
      onVisited: markVisited,
      onProgress: (p) => {
        progress = { fetched: p.fetched, queued: p.queued, skipped: p.skipped, discovered: p.seen };
        emit("crawl:progress", p);
      },
    });

    if (result.unreachableHost) {
      const message = result.notes[0];
      await api(`/site/crawl-jobs/${jobId}`, {
        method: "PATCH",
        siteId,
        cookieHeader,
        body: { status: "failed", error: message, pagesStored: 0 },
      }).catch(() => undefined);
      emit("crawl:done", { ok: false, unreachableHost: true, error: message });
      return;
    }

    if (result.needsSitemap) {
      const message = result.notes[0];
      await api(`/site/crawl-jobs/${jobId}`, {
        method: "PATCH",
        siteId,
        cookieHeader,
        body: {
          status: "failed",
          error: message,
          pagesStored: 0,
          sitemapUrlCount: 0,
          robotsTxt: result.robotsTxt,
          robotsStatus: result.robotsStatus,
          robotsFetchedAt: result.robotsFetchedAt,
          llmsTxt: result.llmsTxt,
          llmsStatus: result.llmsStatus,
          llmsFetchedAt: result.llmsFetchedAt,
        },
      }).catch(() => undefined);
      emit("crawl:done", { ok: false, needsSitemap: true, error: message });
      return;
    }

    if (!sweepReliable) {
      result.notes.push(
        "Some pages could not be saved or marked as seen, so pages that have gone were left " +
          "on record rather than risk removing live ones. The next complete crawl will prune them.",
      );
    }
    if (result.complete && !result.stopped && sweepStarted && sweepReliable) {
      const pruned = await api("/site/pages/prune", {
        method: "POST",
        siteId,
        cookieHeader,
      }).catch((e) => {
        result.notes.push(`Pages that have gone could not be removed (${readable(e)}).`);
        return null;
      });
      if (pruned?.deleted > 0) {
        result.notes.push(
          `${pruned.deleted} page(s) on record were not reachable from the sitemap or any link ` +
            `on the site, so their entries were removed.`,
        );
      }
    }

    const frontier = await saveOutlinks(result.pages, siteId, cookieHeader).catch((e) => {
      result.notes.push(`The links between pages could not be saved (${readable(e)}).`);
      return [];
    });

    await api("/site/pages/graph", {
      method: "POST",
      siteId,
      cookieHeader,
      body: {},
    }).catch((e) => result.notes.push(`The link graph could not be rebuilt (${readable(e)}).`));

    const settled = await api(`/site/crawl-jobs/${jobId}`, {
      method: "PATCH",
      siteId,
      cookieHeader,
      body: {
        status: result.stopped ? "cancelled" : "completed",
        discovered: result.seen.length,
        skipped: result.skipped,
        fetched: result.pages.length - (result.blockedByRobots ?? 0),
        queued: result.queued,
        newPages: result.counts.new,
        changed: result.counts.changed,
        unchanged: result.counts.unchanged,
        failed: result.counts.error,
        pagesStored: stored,
        complete: result.complete,
        sitemapComplete: result.sitemapComplete,
        linkDiscovered: result.linkDiscovered,
        frontier,
        notes: result.notes,
        sitemapUrls: result.sitemapUrls,
        sitemapsUsed: result.sitemapsUsed,
        sitemapAtRoot: result.sitemapAtRoot,
        sitemapUrlCount: result.sitemapUrlCount,
        robotsTxt: result.robotsTxt,
        robotsStatus: result.robotsStatus,
        robotsFetchedAt: result.robotsFetchedAt,
        llmsTxt: result.llmsTxt,
        llmsStatus: result.llmsStatus,
        llmsFetchedAt: result.llmsFetchedAt,
        crawlerAccess: result.crawlerAccess,
        hostVariants: result.hostVariants,
      },
    });

    emit("crawl:done", {
      ok: true,
      domain: target.domain,
      stopped: result.stopped,
      complete: result.complete,
      counts: result.counts,
      pagesStored: stored,
      skipped: result.skipped,
      notes: result.notes,
      job: settled,
    });
  } catch (e) {
    const message = readable(e);
    await api(`/site/crawl-jobs/${jobId}`, {
      method: "PATCH",
      siteId,
      cookieHeader,
      body: { status: "failed", error: message, pagesStored: stored },
    }).catch(() => undefined);
    emit("crawl:done", { ok: false, error: message });
  }
}

function readable(e) {
  return e instanceof Error ? e.message : String(e);
}
