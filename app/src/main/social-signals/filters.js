import { crawlFetch, withOutboundSlot } from "../net.js";

export function withinAge(posts, maxAgeDays) {
  const days = Number(maxAgeDays);
  if (!Number.isFinite(days) || days <= 0) return posts;
  const cutoff = Date.now() - days * 86_400_000;
  return posts.filter((p) => {
    const t = new Date(p.createdAt ?? "").getTime();
    return !Number.isFinite(t) || t >= cutoff;
  });
}

function flaggedDead(p) {
  const tags = (p.context?.tags ?? []).map((t) => String(t).toLowerCase());
  return tags.includes("archived") || tags.includes("locked");
}

async function urlGone(url) {
  try {
    return await withOutboundSlot(async () => {
      const res = await crawlFetch(url, { method: "HEAD", redirect: "follow" });
      return res.status === 404 || res.status === 410;
    });
  } catch {
    return false;
  }
}

export async function dropDead(posts) {
  const alive = posts.filter((p) => !flaggedDead(p));
  const checks = await Promise.all(alive.map((p) => urlGone(p.url)));
  return alive.filter((_, i) => !checks[i]);
}
