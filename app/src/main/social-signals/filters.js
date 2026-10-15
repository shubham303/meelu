import { crawlFetch, withOutboundSlot } from "../net.js";

async function urlGone(url) {
  try {
    return await withOutboundSlot(async () => {
      const res = await crawlFetch(url, { method: "HEAD", redirect: "follow" });
      return res.status === 404;
    });
  } catch {
    return false;
  }
}

export async function deadIds(posts) {
  const gone = await Promise.all(posts.map((p) => urlGone(p.url)));
  return new Set(posts.filter((_, i) => gone[i]).map((p) => p.id));
}
