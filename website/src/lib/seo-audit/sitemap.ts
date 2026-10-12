import { fetchUrl } from "./net";

export const STANDARD_SITEMAP_PATH = "/sitemap.xml";

const SITEMAP_PROBES = [
  STANDARD_SITEMAP_PATH,
  "/sitemap_index.xml",
  "/sitemap-index.xml",
  "/sitemap/sitemap.xml",
  "/sitemaps/sitemap.xml",
  "/wp-sitemap.xml",
  "/sitemap/index.xml",
  "/sitemap.txt",
];

const LOC = /<loc>\s*(?:<!\[CDATA\[)?\s*([^<\]]+?)\s*(?:\]\]>)?\s*<\/loc>/gi;

function locsIn(xml: string): string[] {
  const out: string[] = [];
  for (const match of xml.matchAll(LOC)) {
    const value = match[1]
      .trim()
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&apos;/g, "'");
    if (/^https?:\/\//i.test(value)) out.push(value);
  }
  return out;
}

/** Some sites publish a plain-text sitemap: one absolute URL per line. */
function plainTextUrls(body: string): string[] {
  const lines = body.split(/\r?\n/).map((l) => l.trim());
  const urls = lines.filter((l) => /^https?:\/\/\S+$/i.test(l));
  return urls.length > 0 && urls.length >= lines.filter(Boolean).length * 0.8
    ? urls
    : [];
}

export type SitemapRead = { urls: string[]; used: string[]; unreadable: string[] };

export async function readSitemaps(
  urls: string[],
  limit: number,
  depth = 0,
  signal?: AbortSignal,
): Promise<SitemapRead> {
  if (depth > 2) return { urls: [], used: [], unreadable: [] };
  const out: string[] = [];
  const used: string[] = [];
  const unreadable: string[] = [];

  for (const url of urls.slice(0, 25)) {
    if (out.length >= limit) break;
    if (/\.gz$/i.test(url)) {
      unreadable.push(url);
      continue;
    }
    const res = await fetchUrl(url, {
      timeoutMs: 15_000,
      accept: "application/xml,text/xml,text/plain,*/*",
      htmlOnly: false,
      signal,
    });
    const body = res.text;
    if (res.status !== 200 || !body) {
      unreadable.push(url);
      continue;
    }

    if (/<sitemapindex[\s>]/i.test(body)) {
      const nested = locsIn(body);
      const inner = await readSitemaps(nested, limit - out.length, depth + 1, signal);
      if (inner.urls.length > 0) {
        out.push(...inner.urls);
        used.push(url, ...inner.used);
      }
      unreadable.push(...inner.unreadable);
      continue;
    }

    const locs = locsIn(body);
    const found = locs.length > 0 ? locs : plainTextUrls(body);
    if (found.length > 0) {
      out.push(...found);
      used.push(url);
    } else {
      unreadable.push(url);
    }
  }

  return {
    urls: [...new Set(out)],
    used: [...new Set(used)],
    unreadable: [...new Set(unreadable)],
  };
}

export type SitemapDiscovery = SitemapRead & { tried: string[]; atRoot: boolean };

export async function discoverSitemaps(
  origin: string,
  fromRobots: string[],
  limit: number,
  signal?: AbortSignal,
): Promise<SitemapDiscovery> {
  const probes = SITEMAP_PROBES.map((path) => new URL(path, origin).toString());
  const tried: string[] = [];

  for (const candidates of [fromRobots, probes]) {
    if (candidates.length === 0) continue;
    tried.push(...candidates);
    const found = await readSitemaps(candidates, limit, 0, signal);
    if (found.urls.length > 0) {
      const standard = new URL(STANDARD_SITEMAP_PATH, origin).toString();
      const atRoot =
        found.used.includes(standard) ||
        (await readSitemaps([standard], 1, 0, signal)).urls.length > 0;
      return { ...found, tried: [...new Set(tried)], atRoot };
    }
  }

  return { urls: [], used: [], unreadable: [], tried: [...new Set(tried)], atRoot: false };
}
