import robotsParserModule from "robots-parser";
import { crawlFetch, withOutboundSlot } from "../net.js";
import { normalise } from "./url.js";

const robotsParser = robotsParserModule.default ?? robotsParserModule;

export const USER_AGENT = "MeeluSEO/1.0 (+https://meelu.app/crawler)";

const REDIRECTS = new Set([301, 302, 303, 307, 308]);
const MAX_HOPS = 5;

export function fetchPage(url, prev = {}, crawlToken = null) {
  return withOutboundSlot(async () => {
    const chain = [];
    let current = url;

    for (let hop = 0; hop <= MAX_HOPS; hop++) {
      const headers = { "user-agent": USER_AGENT, accept: "text/html" };
      if (crawlToken) headers["x-meelu-crawl"] = crawlToken;
      if (hop === 0 && prev.etag) headers["if-none-match"] = prev.etag;
      if (hop === 0 && prev.lastModified) headers["if-modified-since"] = prev.lastModified;

      let res;
      try {
        res = await crawlFetch(current, {
          headers,
          redirect: "manual",
          signal: AbortSignal.timeout(20_000),
        });
      } catch (e) {
        return { url, chain, error: e instanceof Error ? e.message : String(e) };
      }

      if (res.status === 304) {
        await res.body?.cancel().catch(() => undefined);
        return { url, chain, status: 200, notModified: true };
      }

      const location = res.headers.get("location");
      if (REDIRECTS.has(res.status) && location) {
        await res.body?.cancel().catch(() => undefined);
        const next = normalise(new URL(location, current).toString());
        chain.push({ url: current, status: res.status, to: next });
        if (chain.some((h) => h.url === next)) return { url, chain, loop: true };
        current = next;
        continue;
      }

      const contentType = res.headers.get("content-type") ?? null;
      const html = contentType?.includes("html") ? await res.text() : undefined;
      if (html === undefined) await res.body?.cancel().catch(() => undefined);

      return {
        url,
        finalUrl: current,
        status: res.status,
        html,
        contentType,
        chain,
        etag: res.headers.get("etag") ?? null,
        lastModified: res.headers.get("last-modified") ?? null,
        xRobotsTag: res.headers.get("x-robots-tag") ?? null,
      };
    }

    return { url, chain, tooManyHops: true };
  });
}

export function loadRobots(origin) {
  return withOutboundSlot(async () => {
    try {
      const res = await crawlFetch(new URL("/robots.txt", origin), {
        headers: { "user-agent": USER_AGENT },
        signal: AbortSignal.timeout(10_000),
      });
      if (!res.ok) {
        await res.body?.cancel().catch(() => undefined);
        return {
          robots: null,
          sitemaps: [],
          found: false,
          status: res.status,
          body: null,
          fetchedAt: new Date().toISOString(),
          ...(res.status === 404 || res.status === 410 ? {} : { error: `HTTP ${res.status}` }),
        };
      }
      const body = await res.text();
      const robots = robotsParser(new URL("/robots.txt", origin).toString(), body);
      return {
        robots,
        sitemaps: robots.getSitemaps() ?? [],
        found: true,
        status: res.status,
        body: body.slice(0, 200_000),
        fetchedAt: new Date().toISOString(),
      };
    } catch (e) {
      return {
        robots: null,
        sitemaps: [],
        found: false,
        status: null,
        body: null,
        fetchedAt: new Date().toISOString(),
        error: e instanceof Error ? e.message : String(e),
      };
    }
  });
}

export function loadLlms(origin) {
  return withOutboundSlot(async () => {
    const fetchedAt = new Date().toISOString();
    try {
      const res = await crawlFetch(new URL("/llms.txt", origin), {
        headers: { "user-agent": USER_AGENT, accept: "text/plain, text/markdown, */*" },
        signal: AbortSignal.timeout(10_000),
      });
      if (!res.ok) {
        await res.body?.cancel().catch(() => undefined);
        return { status: res.status, body: null, fetchedAt };
      }
      const body = await res.text();
      return { status: res.status, body: body.slice(0, 200_000), fetchedAt };
    } catch {
      return { status: null, body: null, fetchedAt };
    }
  });
}

export async function pool(items, limit, work) {
  const out = [];
  let i = 0;
  const runners = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (i < items.length) {
      const idx = i++;
      out[idx] = await work(items[idx]);
    }
  });
  await Promise.all(runners);
  return out;
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
