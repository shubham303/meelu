import { ENV_DEFAULTS, meeluAuthHeaders } from "./config.js";
import { apiFetch } from "./net.js";

const RETRY_MS = 15 * 1000;
const ATTEMPTS = 8;

async function fetchSites(cookieHeader) {
  const res = await apiFetch(`${ENV_DEFAULTS.meeluBaseUrl}/api/v1/sites?page_size=100`, {
    headers: meeluAuthHeaders(cookieHeader),
  });
  if (!res.ok) return null;
  const json = await res.json().catch(() => ({}));
  const sites = json?.data;
  return Array.isArray(sites) ? sites : null;
}

async function reap(path, siteId, cookieHeader) {
  const res = await apiFetch(`${ENV_DEFAULTS.meeluBaseUrl}/api/v1${path}`, {
    method: "POST",
    headers: {
      ...meeluAuthHeaders(cookieHeader),
      "content-type": "application/json",
      "x-meelu-site": siteId,
    },
    body: JSON.stringify({ staleMs: 0 }),
  });
  const json = await res.json().catch(() => ({}));
  return res.ok ? Number(json?.data?.reaped ?? 0) : 0;
}

async function attempt({ cookieHeader, log }) {
  const cookie = await cookieHeader().catch(() => "");
  if (!cookie && !ENV_DEFAULTS.meeluApiKey) return false;
  const sites = await fetchSites(cookie).catch(() => null);
  if (!sites) return false;

  for (const site of sites) {
    if (!site?.id) continue;
    const crawls = await reap("/site/crawl-jobs/reap", site.id, cookie).catch(() => 0);
    const renders = await reap("/site/render-jobs/reap", site.id, cookie).catch(() => 0);
    if (crawls > 0) log(`cleared ${crawls} crawl(s) of ${site.domain} left running by the previous app process`);
    if (renders > 0) log(`cleared ${renders} render(s) of ${site.domain} left running by the previous app process`);
  }
  return true;
}

export function clearOrphanedJobs({ cookieHeader, log }) {
  let left = ATTEMPTS;
  const run = async () => {
    left -= 1;
    const done = await attempt({ cookieHeader, log }).catch(() => false);
    if (!done && left > 0) setTimeout(run, RETRY_MS);
  };
  void run();
}
