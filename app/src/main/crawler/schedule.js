import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";
import { runCrawl } from "./index.js";

const ENABLED = process.env.MEELU_AUTO_CRAWL !== "0";
const EVERY_HOURS = Number(process.env.MEELU_AUTO_CRAWL_EVERY_HOURS ?? 24);
const TICK_MS = Number(process.env.MEELU_AUTO_CRAWL_TICK_MS ?? 30 * 60 * 1000);
const FIRST_TICK_MS = Number(process.env.MEELU_AUTO_CRAWL_FIRST_TICK_MS ?? 2 * 60 * 1000);

const inFlight = new Set();
let timer = null;
let firstTick = null;

async function fetchSites(cookieHeader) {
  try {
    const res = await apiFetch(`${ENV_DEFAULTS.meeluBaseUrl}/api/v1/sites?page_size=100`, {
      headers: meeluAuthHeaders(cookieHeader),
    });
    if (!res.ok) return null;
    const json = await res.json().catch(() => ({}));
    const sites = json?.data;
    return Array.isArray(sites) ? sites : null;
  } catch {
    return null;
  }
}

function dueSite(sites, cutoff) {
  return sites.find((site) => {
    if (!site?.id || inFlight.has(site.id)) return false;
    const last = site.lastCrawledAt ? Date.parse(site.lastCrawledAt) : NaN;
    return Number.isFinite(last) && last < cutoff;
  });
}

function releaseWhenDone(emit, siteId) {
  return (event, data) => {
    if (event === "crawl:done") inFlight.delete(siteId);
    emit(event, data);
  };
}

async function tick({ cookieHeader, emit, log }) {
  if (inFlight.size > 0) return;

  const cookie = await cookieHeader().catch(() => "");
  if (!cookie && !ENV_DEFAULTS.meeluApiKey) return;

  const sites = await fetchSites(cookie);
  if (!sites) return;

  const site = dueSite(sites, Date.now() - EVERY_HOURS * 60 * 60 * 1000);
  if (!site) return;

  inFlight.add(site.id);
  try {
    const res = await runCrawl(
      { siteId: site.id, trigger: "schedule" },
      releaseWhenDone(emit, site.id),
      { cookieHeader: cookie },
    );
    if (res.started) log(`auto-crawl ${site.domain} (job ${res.jobId})`);
    else inFlight.delete(site.id);
  } catch (err) {
    inFlight.delete(site.id);
    log(`auto-crawl ${site.domain} failed:`, err instanceof Error ? err.message : err);
  }
}

export function startCrawlSchedule({ cookieHeader, emit, log }) {
  if (!ENABLED || timer || firstTick) return;
  const run = () => void tick({ cookieHeader, emit, log });
  firstTick = setTimeout(() => {
    firstTick = null;
    run();
    timer = setInterval(run, TICK_MS);
  }, FIRST_TICK_MS);
}
