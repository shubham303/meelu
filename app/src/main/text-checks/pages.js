import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";

const PAGE_SIZE = 100;
const PAUSE_MS = 500;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function fetchBatch({ siteId, cookieHeader, page }) {
  const params = new URLSearchParams({
    view: "text",
    statusCode: "200",
    pageSize: String(PAGE_SIZE),
    page: String(page),
  });
  const res = await apiFetch(`${ENV_DEFAULTS.meeluBaseUrl}/api/v1/site/pages?${params}`, {
    headers: { ...meeluAuthHeaders(cookieHeader), "x-meelu-site": siteId },
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(json?.error?.message ?? `Site pages could not be read (${res.status}).`);
  }
  return { pages: Array.isArray(json?.data) ? json.data : [], hasNext: !!json?.pagination?.has_next };
}

export async function sitePageTexts({ siteId, cookieHeader }) {
  if (!siteId) throw new Error("No website in force.");
  const pages = [];
  let page = 1;
  for (;;) {
    const batch = await fetchBatch({ siteId, cookieHeader, page });
    for (const item of batch.pages) {
      if (typeof item.bodyText === "string" && item.bodyText.trim()) {
        pages.push({ id: item.id, url: item.url, title: item.title ?? null, bodyText: item.bodyText });
      }
    }
    if (!batch.hasNext) break;
    page += 1;
    await sleep(PAUSE_MS);
  }
  return pages;
}
