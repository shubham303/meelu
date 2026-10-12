const TRACKING = new Set([
  "gclid",
  "fbclid",
  "msclkid",
  "mc_cid",
  "mc_eid",
  "igshid",
  "ref",
  "_hsenc",
  "_hsmi",
]);

/**
 * Strips the parts of a URL that make the same page look like two. The trailing
 * slash is deliberately left alone: rewriting /about/ to /about would make the
 * tool report a redirect the site's own links never asked for.
 */
export function normalise(url: string): string {
  try {
    const u = new URL(url);
    u.hash = "";
    u.hostname = u.hostname.toLowerCase();
    for (const key of [...u.searchParams.keys()]) {
      if (key.startsWith("utm_") || TRACKING.has(key)) u.searchParams.delete(key);
    }
    u.searchParams.sort();
    return u.toString();
  } catch {
    return url;
  }
}

export function absolute(href: string, base: string): string | undefined {
  try {
    const u = new URL(href, base);
    if (u.protocol !== "http:" && u.protocol !== "https:") return undefined;
    u.hash = "";
    return u.toString();
  } catch {
    return undefined;
  }
}

function registrable(url: string): string {
  return new URL(url).hostname.replace(/^www\./, "").toLowerCase();
}

export function sameSite(url: string, other: string): boolean {
  try {
    return registrable(url) === registrable(other);
  } catch {
    return false;
  }
}

export function sameHost(url: string, other: string): boolean {
  try {
    return (
      new URL(url).hostname.toLowerCase() === new URL(other).hostname.toLowerCase()
    );
  } catch {
    return false;
  }
}

export function pathOf(url: string): string {
  try {
    const u = new URL(url);
    return `${u.pathname}${u.search}`;
  } catch {
    return "/";
  }
}

export function slugOf(url: string): string {
  try {
    return new URL(url).pathname;
  } catch {
    return "/";
  }
}

/** Turns whatever the visitor typed into a URL, or null if it cannot be one. */
export function parseInput(raw: string): URL | null {
  const trimmed = raw.trim();
  if (!trimmed || trimmed.length > 2000) return null;
  const withScheme = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
  let url: URL;
  try {
    url = new URL(withScheme);
  } catch {
    return null;
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") return null;
  if (url.username || url.password) return null;
  if (!url.hostname.includes(".") || url.hostname.endsWith(".")) return null;
  return url;
}

export function looksLikeSitemap(url: URL): boolean {
  const path = url.pathname.toLowerCase();
  return (
    path.endsWith(".xml") ||
    path.endsWith(".xml.gz") ||
    path.includes("sitemap") ||
    url.pathname.toLowerCase().endsWith("/robots.txt")
  );
}

export const BINARY_PATH =
  /\.(pdf|jpe?g|png|gif|webp|avif|svg|ico|zip|gz|tar|mp4|mp3|wav|mov|css|js|xml|json|txt|rss|atom|woff2?|ttf|eot|dmg|exe)$/i;

/** Guards against link traps like /a/b/a/b/a/b. */
export function repeatsSegments(url: string): boolean {
  try {
    const counts = new Map<string, number>();
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
