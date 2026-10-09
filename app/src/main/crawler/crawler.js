import { XMLParser } from "fast-xml-parser";
import { fetchPage, loadLlms, loadRobots, pool, sleep, USER_AGENT } from "./fetch.js";
import { crawlFetch, withOutboundSlot } from "../net.js";
import { articleFormat, extract, shallowReason } from "./extract.js";
import { IMAGE_PROBE_BUDGET, weighImages } from "./images.js";
import { probeHostVariants } from "./host-variants.js";
import { probeCrawlerAccess } from "./probe.js";
import { normalise, otherHostForm, sameHost } from "./url.js";

const MAX_PAGES = 10_000;

const GOOGLEBOT = "Googlebot";
const OUR_AGENT = "MeeluSEO";

const STANDARD_SITEMAP_PATH = "/sitemap.xml";

const SITEMAP_PROBES = [
  STANDARD_SITEMAP_PATH,
  "/sitemap_index.xml",
  "/sitemap-index.xml",
  "/sitemap/sitemap.xml",
  "/sitemaps/sitemap.xml",
  "/wp-sitemap.xml",
  "/sitemap/index.xml",
];

const BINARY = /\.(pdf|jpe?g|png|gif|webp|svg|ico|zip|gz|mp4|mp3|wav|css|js|xml|json|woff2?)$/i;

function repeatsSegments(url) {
  try {
    const counts = new Map();
    for (const seg of new URL(url).pathname.split("/").filter(Boolean)) {
      const n = (counts.get(seg) ?? 0) + 1;
      if (n >= 3) return true;
      counts.set(seg, n);
    }
    return false;
  } catch {
    return false;
  }
}

function unchangedRow(url, inSitemap) {
  return {
    url,
    status: 200,
    inSitemap,
    blockedByRobots: false,
    lastCrawledAt: new Date().toISOString(),
    state: "unchanged",
  };
}

function blockedRow(url, inSitemap) {
  return {
    url,
    status: null,
    inSitemap,
    blockedByRobots: true,
    shallow: false,
    fetchError: null,
    redirectTo: null,
    redirectFinal: null,
    redirectHops: null,
    state: "blocked",
  };
}

function failedRow(url, inSitemap, status, reason, fetchError = null) {
  return {
    url,
    links: [],
    externalLinks: [],
    status,
    inSitemap,
    blockedByRobots: false,
    shallow: true,
    shallowReason: reason,
    fetchError,
    redirectTo: null,
    redirectFinal: null,
    redirectHops: null,
    ...(reason === "unreachable" ? {} : { lastCrawledAt: new Date().toISOString() }),
    state: "error",
  };
}

function redirectRow(hop, inSitemap, final, hopsLeft) {
  return {
    url: hop.url,
    links: [],
    externalLinks: [],
    status: hop.status,
    inSitemap,
    blockedByRobots: false,
    lastCrawledAt: new Date().toISOString(),
    redirectTo: hop.to,
    redirectFinal: final,
    redirectHops: hopsLeft,
    shallow: true,
    shallowReason: "redirect",
    fetchError: null,
    state: "redirect",
  };
}

function halted(origin, startedAt, note, extra = {}) {
  return {
    origin,
    startedAt,
    pages: [],
    counts: { new: 0, changed: 0, unchanged: 0, error: 0 },
    complete: false,
    queued: 0,
    seen: [],
    skipped: 0,
    stopped: true,
    sitemapsUsed: [],
    sitemapUrlCount: 0,
    notes: [note],
    ...extra,
  };
}

async function readSitemaps(urls, depth = 0) {
  if (depth > 2) return { urls: [], used: [] };
  const parser = new XMLParser({ ignoreAttributes: false });
  const out = [];
  const used = [];

  for (const url of urls.slice(0, 50)) {
    try {
      const xml = await withOutboundSlot(async () => {
        const res = await crawlFetch(url, {
          headers: { "user-agent": USER_AGENT },
          signal: AbortSignal.timeout(15_000),
        });
        if (!res.ok) {
          await res.body?.cancel().catch(() => undefined);
          return null;
        }
        return res.text();
      });
      if (xml === null) continue;
      const parsed = parser.parse(xml);

      const index = parsed?.sitemapindex?.sitemap;
      if (index) {
        const nested = (Array.isArray(index) ? index : [index])
          .map((entry) => entry.loc)
          .filter((loc) => typeof loc === "string");
        const inner = await readSitemaps(nested, depth + 1);
        if (inner.urls.length) {
          out.push(...inner.urls);
          used.push(url, ...inner.used);
        }
        continue;
      }

      const entries = parsed?.urlset?.url;
      if (entries) {
        const locs = (Array.isArray(entries) ? entries : [entries])
          .map((entry) => entry.loc)
          .filter((loc) => typeof loc === "string");
        if (locs.length) {
          out.push(...locs);
          used.push(url);
        }
      }
    } catch {
    }
  }
  return { urls: [...new Set(out)], used: [...new Set(used)] };
}

async function servesSitemapAtRoot(origin, used) {
  const standard = new URL(STANDARD_SITEMAP_PATH, origin).toString();
  if (used.includes(standard)) return true;
  const found = await readSitemaps([standard]);
  return found.urls.length > 0;
}

async function findSitemapUrls(origin, declared, fromRobots) {
  const attempts = [
    declared,
    fromRobots,
    SITEMAP_PROBES.map((path) => new URL(path, origin).toString()),
  ];
  const tried = [];
  for (const candidates of attempts) {
    if (!candidates?.length) continue;
    tried.push(...candidates);
    const found = await readSitemaps(candidates);
    if (found.urls.length) {
      return {
        ...found,
        tried: [...new Set(tried)],
        atRoot: await servesSitemapAtRoot(origin, found.used),
      };
    }
  }
  return { urls: [], used: [], tried: [...new Set(tried)], atRoot: false };
}

async function resolveOrigin(start, crawlToken) {
  const res = await fetchPage(start, {}, crawlToken).catch(() => null);
  if (!res || res.error) return { origin: start, reached: false, why: res?.error ?? "no answer" };
  if (!res.finalUrl) return { origin: start, reached: true };
  try {
    return { origin: new URL(res.finalUrl).origin, reached: true };
  } catch {
    return { origin: start, reached: true };
  }
}

export async function crawlSite(domain, known, opts = {}) {
  const startedAt = new Date().toISOString();
  const declaredOrigin = domain.startsWith("http") ? new URL(domain).origin : `https://${domain}`;
  const concurrency = Math.max(1, opts.concurrency ?? 8);
  let delayMs = opts.delayMs ?? 200;

  const notes = [];

  const home = await resolveOrigin(declaredOrigin, opts.crawlToken ?? null);
  if (!home.reached) {
    return halted(
      declaredOrigin,
      startedAt,
      `${declaredOrigin} did not answer (${home.why}). That is the exact host on the website ` +
        `record, and the crawl reads that host and no other — a www address and a bare one are ` +
        `separate websites unless one redirects to the other. Check the host on the Website ` +
        `profile screen: if the site serves on the other form, put that form on the record.`,
      { unreachableHost: true },
    );
  }

  const origin = home.origin;
  if (origin !== declaredOrigin) {
    notes.push(
      `${declaredOrigin} redirects to ${origin}, so that is the address the crawl read. The two ` +
        `host forms are separate websites unless one redirects to the other, and this one does.`,
    );
  }

  const [
    { robots, sitemaps, found, status: robotsStatus, body: robotsTxt, fetchedAt: robotsFetchedAt },
    { status: llmsStatus, body: llmsTxt, fetchedAt: llmsFetchedAt },
  ] = await Promise.all([loadRobots(origin), loadLlms(origin)]);

  const wellKnown = { robotsTxt, robotsStatus, robotsFetchedAt, llmsTxt, llmsStatus, llmsFetchedAt };

  const blockedForGooglebot = (url) => !!robots && robots.isAllowed(url, GOOGLEBOT) === false;
  const mayFetch = (url) =>
    !robots || (robots.isAllowed(url, OUR_AGENT) !== false && robots.isAllowed(url, GOOGLEBOT) !== false);

  if (!found) {
    notes.push("No robots.txt — not a problem in itself, but worth knowing.");
  }

  const declared = opts.sitemapUrls?.length ? opts.sitemapUrls : [];
  const sitemap = await findSitemapUrls(origin, declared, sitemaps);

  if (sitemap.urls.length === 0) {
    return halted(
      origin,
      startedAt,
      `No sitemap could be found for ${origin}. ` +
        (sitemap.tried.length
          ? `Tried ${sitemap.tried.slice(0, 6).join(", ")}. `
          : "") +
        `The crawl reads the pages a sitemap lists and nothing else, so it needs one — add the ` +
        `sitemap URL on the Website profile screen and run the crawl again.`,
      { needsSitemap: true, sitemapsTried: sitemap.tried, ...wellKnown },
    );
  }

  const worklist = [...new Set(sitemap.urls.filter((url) => sameHost(url, origin)).map(normalise))];
  const variantListed = sitemap.urls.filter((url) => otherHostForm(url, origin)).length;
  const offSite = sitemap.urls.length - worklist.length - variantListed;
  if (offSite > 0) {
    notes.push(`${offSite} sitemap URL(s) point outside ${origin} and were left alone.`);
  }
  if (variantListed > 0) {
    notes.push(
      `${variantListed} sitemap URL(s) use the other host form and were left alone — ${origin} is ` +
        `the address this site answers on, and a host that does not redirect to it is a separate ` +
        `website rather than another way of spelling this one.`,
    );
  }
  if (worklist.length === 0) {
    return halted(
      origin,
      startedAt,
      `The sitemap for ${origin} lists no URLs on that host, so there was nothing to read. ` +
        `Check the sitemap URL on the Website profile screen.`,
      { needsSitemap: true, sitemapsTried: sitemap.tried, ...wellKnown },
    );
  }

  const blockedSeen = new Set();
  const priorByUrl = new Map(known.map((k) => [normalise(k.url), k]));
  const inSitemap = new Set(worklist);
  const sitemapQueue = [...worklist];
  const linkQueue = [];
  const seen = new Set(worklist);
  const pages = [];
  const counts = { new: 0, changed: 0, unchanged: 0, error: 0 };
  let stopped = false;
  let skipped = 0;
  let requested = 0;
  let linkRequested = 0;

  const linkBudget = Math.min(worklist.length * 2, MAX_PAGES - worklist.length);

  const freshBefore = opts.freshBefore ? new Date(opts.freshBefore) : null;

  const freshEnough = (url) => {
    if (!freshBefore) return false;
    const prior = priorByUrl.get(url);
    if (!prior?.lastCrawledAt || prior.crawlComplete !== true) return false;
    return new Date(prior.lastCrawledAt).getTime() >= freshBefore.getTime();
  };

  const recordBlocked = (url) => {
    if (!blockedForGooglebot(url) || blockedSeen.has(url)) return;
    blockedSeen.add(url);
    pages.push(blockedRow(url, inSitemap.has(url)));
  };

  const enqueueLink = (raw) => {
    const url = normalise(raw);
    if (seen.has(url) || !sameHost(url, origin)) return;
    if (BINARY.test(url) || repeatsSegments(url)) return;
    if (!mayFetch(url)) {
      seen.add(url);
      recordBlocked(url);
      return;
    }
    seen.add(url);
    linkQueue.push(url);
  };

  const skippedFresh = [];
  const takeBatch = (queue, n, budgetLeft) => {
    const batch = [];
    while (queue.length > 0 && batch.length < n && batch.length < budgetLeft) {
      const url = queue.shift();
      if (!mayFetch(url)) {
        recordBlocked(url);
        continue;
      }
      if (freshEnough(url)) {
        skipped++;
        skippedFresh.push(url);
        continue;
      }
      batch.push(url);
    }
    return batch;
  };

  const imageWeights = new Map();
  const imageCandidates = [];
  let imageBudgetLeft = Math.max(0, opts.imageBudget ?? IMAGE_PROBE_BUDGET);
  let imagesWeighed = 0;

  const runImageProbes = async () => {
    const rows = imageCandidates.splice(0, imageCandidates.length);
    if (rows.length === 0 || imageBudgetLeft <= 0) return;
    const used = await weighImages(
      rows,
      imageWeights,
      imageBudgetLeft,
      opts.crawlToken ?? null,
      concurrency,
    );
    imageBudgetLeft -= used;
    imagesWeighed += used;
  };

  let consecutiveFailedBatches = 0;
  let persistedUpTo = 0;
  let bailed = false;
  const batchSize = Math.max(concurrency, opts.batchSize ?? 25);

  const flush = async () => {
    if (opts.onVisited && skippedFresh.length > 0) {
      const urls = skippedFresh.splice(0, skippedFresh.length);
      try {
        await opts.onVisited(urls);
      } catch {
      }
    }
    if (!opts.onBatch || pages.length === persistedUpTo) return;
    const batch = pages.slice(persistedUpTo);
    persistedUpTo = pages.length;
    try {
      await opts.onBatch(batch);
    } catch {
    }
  };

  let lastStopCheck = Date.now();
  const stopAsked = async () => {
    if (!opts.shouldStop) return false;
    if (Date.now() - lastStopCheck < 2000) return false;
    lastStopCheck = Date.now();
    try {
      return await opts.shouldStop();
    } catch {
      return false;
    }
  };

  const record = (res, phase) => {
    const listed = inSitemap.has(res.url);

    if (res.notModified) {
      counts.unchanged++;
      pages.push(unchangedRow(res.url, listed));
      return;
    }

    if (res.chain?.length) {
      const final = res.chain[res.chain.length - 1].to;
      res.chain.forEach((hop, i) => {
        pages.push(redirectRow(hop, inSitemap.has(hop.url), final, res.chain.length - i));
      });
      enqueueLink(final);
      if (res.loop || res.tooManyHops) {
        counts.error++;
        notes.push(`${res.url} redirects in a loop or past ${5} hops.`);
        return;
      }
    }

    if (res.error) {
      counts.error++;
      pages.push(failedRow(res.url, listed, 0, "unreachable", res.error.slice(0, 500)));
      return;
    }
    if (res.loop || res.tooManyHops) return;

    if (res.status >= 400) {
      counts.error++;
      const reason =
        res.status === 404 || res.status === 410
          ? "gone"
          : res.status >= 500
            ? "server-error"
            : "blocked";
      pages.push(failedRow(res.url, listed, res.status, reason));
      return;
    }

    if (!res.html) {
      pages.push({
        ...failedRow(res.url, listed, res.status, "not-html"),
        contentType: res.contentType,
        state: "unchanged",
      });
      return;
    }

    const prior = priorByUrl.get(res.url);
    const f = extract(res.html, res.url, res.status);
    const changed = !prior?.contentHash || prior.contentHash !== f.contentHash;
    if (changed) counts[prior ? "changed" : "new"]++;
    else counts.unchanged++;

    const format = articleFormat(f);
    const reason = shallowReason(f);
    const row = {
      url: f.url,
      status: f.status,
      contentHash: f.contentHash,
      etag: res.etag,
      lastModified: res.lastModified,
      xRobotsTag: res.xRobotsTag ?? null,
      blockedByRobots: false,
      lastCrawledAt: new Date().toISOString(),
      inSitemap: listed,
      contentType: res.contentType,
      redirectTo: null,
      redirectFinal: null,
      redirectHops: null,
      fetchError: null,
      title: f.title,
      titlePixels: f.titlePixels,
      metaDescription: f.metaDescription,
      h1: f.h1,
      headings: f.headings,
      bodyText: f.bodyText,
      links: f.outLinks,
      externalLinks: f.externalLinks,
      canonical: f.canonical,
      robotsDirectives: f.robotsDirectives,
      viewportMeta: f.viewportMeta,
      nosnippetCount: f.nosnippetCount,
      socialMetaCount: f.socialMetaCount,
      socialMeta: f.socialMeta,
      hasGoogleAnalytics: f.hasGoogleAnalytics,
      author: f.author,
      schemaTypes: f.schemaTypes,
      schemaNodes: f.schemaNodes,
      lang: f.lang,
      hreflang: f.hreflang,
      images: f.images,
      publishedAt: f.publishedAt,
      modifiedAt: f.modifiedAt,
      wordCount: f.wordCount,
      mixedContent: f.mixedContent,
      format,
      shallow: Boolean(reason),
      shallowReason: reason,
      state: changed ? (prior ? "changed" : "new") : "unchanged",
    };
    pages.push(row);

    if (imageBudgetLeft > 0 && row.images.length > 0) imageCandidates.push(row);

    for (const link of f.outLinks) if (link.rel !== "nofollow") enqueueLink(link.url);
  };

  const runPhase = async (queue, phase, budget) => {
    let used = 0;
    while (queue.length > 0 && used < budget) {
      const batch = takeBatch(queue, concurrency, budget - used);
      if (batch.length === 0) continue;
      used += batch.length;
      requested += batch.length;
      if (phase === "links") linkRequested += batch.length;

      const fetched = await pool(batch, concurrency, async (url) =>
        fetchPage(url, priorByUrl.get(url) ?? {}, opts.crawlToken ?? null),
      );
      await sleep(delayMs);

      if (pages.length - persistedUpTo >= batchSize || skippedFresh.length >= batchSize) {
        await flush();
      }

      const failed = fetched.filter((f) => f.error).length;
      if (failed === fetched.length && fetched.length > 0) {
        consecutiveFailedBatches += 1;
        delayMs = Math.min(delayMs * 2, 5000);
        if (consecutiveFailedBatches >= 5) {
          bailed = true;
          notes.push(
            `The site stopped responding after ${pages.length} page(s) — five batches in a row ` +
              `failed, so the crawl stopped rather than keep hammering it. Nothing already known ` +
              `was lost; run it again later to continue.`,
          );
          return;
        }
      } else if (failed === 0) {
        consecutiveFailedBatches = 0;
        delayMs = Math.max(delayMs / 2, opts.delayMs ?? 200);
      }

      for (const res of fetched) record(res, phase);
      opts.onProgress?.({
        phase,
        fetched: pages.length - blockedSeen.size,
        queued: sitemapQueue.length + linkQueue.length,
        skipped,
        seen: seen.size,
      });
      await runImageProbes();

      if (await stopAsked()) {
        stopped = true;
        notes.push(
          `Stopped on request after ${pages.length} page(s). Everything fetched so far was saved.`,
        );
        return;
      }
    }
  };

  const accessProbe = probeCrawlerAccess(origin).catch(() => null);
  const variantProbe = probeHostVariants(origin, worklist, opts.crawlToken ?? null).catch(
    () => null,
  );

  await runPhase(sitemapQueue, "sitemap", MAX_PAGES);
  const sitemapComplete = sitemapQueue.length === 0 && !stopped && !bailed;

  for (const url of opts.linkFrontier ?? []) enqueueLink(url);

  if (sitemapComplete && linkBudget > 0) {
    await runPhase(linkQueue, "links", linkBudget);
  }

  const complete = sitemapComplete && linkQueue.length === 0;

  if (!sitemapComplete && !stopped && !bailed) {
    notes.push(
      `The ${MAX_PAGES.toLocaleString("en-US")}-page limit was reached with ` +
        `${sitemapQueue.length} of the sitemap's URLs still unread, so no link-following ran — ` +
        `pages the sitemap does not list were not looked for.`,
    );
  }
  if (linkQueue.length > 0) {
    notes.push(
      `${linkRequested} linked page(s) outside the sitemap were read and ${linkQueue.length} more ` +
        `were found but left — link-following is capped at ${linkBudget} pages so it cannot crowd ` +
        `out the sitemap.`,
    );
  }
  notes.push(`${worklist.length} URL(s) came from ${sitemap.used.join(", ")}.`);
  if (skipped > 0) {
    notes.push(
      `${skipped} page(s) were skipped without a request: downloaded since ` +
        `${freshBefore?.toISOString()} with nothing left for the crawl to do.`,
    );
  }

  if (blockedSeen.size > 0) {
    notes.push(
      `${blockedSeen.size} URL(s) are disallowed to Googlebot by robots.txt and were recorded ` +
        `without being read. Google will not crawl them either.`,
    );
  }

  if (imagesWeighed > 0 && imageBudgetLeft === 0) {
    notes.push(
      `File sizes were measured for the first ${imagesWeighed} image(s) found, which is the ` +
        `cap for one crawl. Images past it carry no weight on record, so findings about ` +
        `oversized or uncompressed images cover only the part of the site that was measured.`,
    );
  }

  await flush();

  const crawlerAccess = await accessProbe;
  const hostVariants = await variantProbe;

  return {
    origin,
    startedAt,
    pages,
    counts,
    ...wellKnown,
    crawlerAccess,
    hostVariants,
    blockedByRobots: blockedSeen.size,
    complete,
    sitemapComplete,
    queued: sitemapQueue.length + linkQueue.length,
    seen: [...seen],
    sitemapUrls: worklist,
    linkDiscovered: linkRequested,
    skipped,
    stopped,
    sitemapsUsed: sitemap.used,
    sitemapAtRoot: sitemap.atRoot,
    sitemapUrlCount: worklist.length,
    notes,
  };
}
