import { crawlFetch, withOutboundSlot } from "../net.js";
import { pool, USER_AGENT } from "./fetch.js";

export const IMAGE_PROBE_BUDGET = 3000;
const IMAGE_PER_PAGE = 25;

function headers(crawlToken) {
  const out = { "user-agent": USER_AGENT, accept: "image/*,*/*" };
  if (crawlToken) out["x-meelu-crawl"] = crawlToken;
  return out;
}

function imageType(res) {
  const raw = res.headers.get("content-type")?.split(";")[0].trim().toLowerCase() ?? "";
  return raw.startsWith("image/") ? raw : null;
}

function size(value) {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : null;
}

async function byHead(url, crawlToken) {
  const res = await crawlFetch(url, {
    method: "HEAD",
    headers: headers(crawlToken),
    redirect: "follow",
    signal: AbortSignal.timeout(10_000),
  });
  await res.body?.cancel().catch(() => undefined);
  if (!res.ok) return null;
  return { bytes: size(res.headers.get("content-length")), type: imageType(res) };
}

async function byRange(url, crawlToken) {
  const res = await crawlFetch(url, {
    method: "GET",
    headers: { ...headers(crawlToken), range: "bytes=0-0" },
    redirect: "follow",
    signal: AbortSignal.timeout(10_000),
  });
  await res.body?.cancel().catch(() => undefined);
  if (!res.ok) return null;
  return {
    bytes: size(res.headers.get("content-range")?.split("/")[1]),
    type: imageType(res),
  };
}

function probeImage(url, crawlToken = null) {
  return withOutboundSlot(async () => {
    let head = null;
    try {
      head = await byHead(url, crawlToken);
      if (head?.bytes) return head;
    } catch {
    }
    try {
      const range = await byRange(url, crawlToken);
      if (range?.bytes) return { bytes: range.bytes, type: range.type ?? head?.type ?? null };
      return head ?? range;
    } catch {
      return head;
    }
  });
}

export async function weighImages(rows, cache, budget, crawlToken, concurrency) {
  if (budget <= 0) return 0;

  const pending = new Set();
  for (const row of rows) {
    for (const image of row.images.slice(0, IMAGE_PER_PAGE)) {
      if (!cache.has(image.src)) pending.add(image.src);
    }
  }

  const batch = [...pending].slice(0, budget);
  const weights = await pool(batch, concurrency, (url) => probeImage(url, crawlToken));
  batch.forEach((url, i) => cache.set(url, weights[i] ?? null));

  for (const row of rows) {
    for (const image of row.images) {
      const weight = cache.get(image.src);
      if (!weight) continue;
      if (weight.bytes !== null) image.bytes = weight.bytes;
      if (weight.type !== null) image.type = weight.type;
    }
  }

  return batch.length;
}
