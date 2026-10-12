import type { SerpPair } from "./types";

export function normalizeUrl(raw: string): string {
  try {
    const url = new URL(raw);
    const host = url.hostname.toLowerCase().replace(/^www\./, "");
    const path = decodeURIComponent(url.pathname).replace(/\/+$/, "").toLowerCase();
    return `${host}${path || ""}`;
  } catch {
    return raw.trim().toLowerCase();
  }
}

export function serpOverlap(a: string, aUrls: string[], b: string, bUrls: string[]): SerpPair {
  const left = new Set(aUrls.map(normalizeUrl));
  const right = new Set(bUrls.map(normalizeUrl));
  const sharedUrls = [...left].filter((url) => right.has(url));
  return {
    a,
    b,
    shared: sharedUrls.length,
    compared: Math.min(left.size, right.size),
    sharedUrls,
  };
}
