import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";
import { startSignalsSearch } from "./pipeline.js";
import { fetchListeningSetup, latestRun } from "./store.js";

const ENABLED = process.env.MEELU_AUTO_LISTENING !== "0";
const TICK_MS = Number(process.env.MEELU_AUTO_LISTENING_TICK_MS ?? 30 * 60 * 1000);
const FIRST_TICK_MS = Number(process.env.MEELU_AUTO_LISTENING_FIRST_TICK_MS ?? 3 * 60 * 1000);
const INTERVAL_HOURS = { daily: 24, weekly: 24 * 7 };

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

async function dueSite(sites, cookie) {
  for (const site of sites) {
    if (!site?.id || inFlight.has(site.id)) continue;
    try {
      const setup = await fetchListeningSetup(site.id, cookie);
      const hours = INTERVAL_HOURS[setup.config?.schedule];
      if (!hours) continue;
      const last = await latestRun(site.id, cookie);
      const startedAt = last?.startedAt ? Date.parse(last.startedAt) : NaN;
      if (last?.status === "running" && Number.isFinite(startedAt) && Date.now() - startedAt < hours * 3_600_000) {
        continue;
      }
      if (!Number.isFinite(startedAt) || Date.now() - startedAt >= hours * 3_600_000) {
        return site;
      }
    } catch {
      continue;
    }
  }
  return null;
}

function releaseWhenDone(emit, siteId) {
  return (message) => {
    if (["done", "stopped", "error"].includes(message?.event)) inFlight.delete(siteId);
    emit(message);
  };
}

async function tick({ cookieHeader, emit, log, providersFor, llm }) {
  if (inFlight.size > 0) return;

  const cookie = await cookieHeader().catch(() => "");
  if (!cookie && !ENV_DEFAULTS.meeluApiKey) return;

  const sites = await fetchSites(cookie);
  if (!sites) return;

  const site = await dueSite(sites, cookie);
  if (!site) return;

  inFlight.add(site.id);
  try {
    const res = startSignalsSearch(
      { siteId: site.id },
      releaseWhenDone(emit, site.id),
      { providers: await providersFor(), llm: llm(), cookieHeader: cookie },
    );
    if (res.jobId) log(`auto-listening ${site.domain} (job ${res.jobId})`);
    else inFlight.delete(site.id);
  } catch (err) {
    inFlight.delete(site.id);
    log(`auto-listening ${site.domain} failed:`, err instanceof Error ? err.message : err);
  }
}

export function startListeningSchedule(deps) {
  if (!ENABLED || timer || firstTick) return;
  const run = () => void tick(deps);
  firstTick = setTimeout(() => {
    firstTick = null;
    run();
    timer = setInterval(run, TICK_MS);
  }, FIRST_TICK_MS);
}
