import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";
import { startLeadsRun } from "./pipeline.js";
import { fetchCampaigns, latestRun } from "./store.js";

const ENABLED = process.env.MEELU_AUTO_LEADS !== "0";
const TICK_MS = Number(process.env.MEELU_AUTO_LEADS_TICK_MS ?? 30 * 60 * 1000);
const FIRST_TICK_MS = Number(process.env.MEELU_AUTO_LEADS_FIRST_TICK_MS ?? 5 * 60 * 1000);
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

async function dueCampaign(sites, cookie) {
  for (const site of sites) {
    if (!site?.id) continue;
    let campaigns;
    try {
      campaigns = await fetchCampaigns(site.id, cookie);
    } catch {
      continue;
    }
    for (const campaign of campaigns) {
      if (campaign?.status !== "active") continue;
      const hours = INTERVAL_HOURS[campaign.schedule];
      if (!hours) continue;
      const key = `${site.id}:${campaign.id}`;
      if (inFlight.has(key)) continue;
      try {
        const last = await latestRun(site.id, campaign.id, cookie);
        const startedAt = last?.startedAt ? Date.parse(last.startedAt) : NaN;
        if (
          last?.status === "running" &&
          Number.isFinite(startedAt) &&
          Date.now() - startedAt < hours * 3_600_000
        ) {
          continue;
        }
        if (!Number.isFinite(startedAt) || Date.now() - startedAt >= hours * 3_600_000) {
          return { site, campaign, key };
        }
      } catch {
        continue;
      }
    }
  }
  return null;
}

function releaseWhenDone(emit, key) {
  return (message) => {
    if (["done", "stopped", "error"].includes(message?.event)) inFlight.delete(key);
    emit(message);
  };
}

async function tick({ cookieHeader, emit, log, providersFor, llm }) {
  if (inFlight.size > 0) return;

  const cookie = await cookieHeader().catch(() => "");
  if (!cookie && !ENV_DEFAULTS.meeluApiKey) return;

  const sites = await fetchSites(cookie);
  if (!sites) return;

  const due = await dueCampaign(sites, cookie);
  if (!due) return;

  const { site, campaign, key } = due;
  inFlight.add(key);
  try {
    const res = startLeadsRun(
      { siteId: site.id, campaignId: campaign.id },
      releaseWhenDone(emit, key),
      { providers: await providersFor(), llm: llm(), cookieHeader: cookie },
    );
    if (res.jobId) log(`auto-leads ${site.domain} "${campaign.name}" (job ${res.jobId})`);
    else inFlight.delete(key);
  } catch (err) {
    inFlight.delete(key);
    log(`auto-leads ${site.domain} failed:`, err instanceof Error ? err.message : err);
  }
}

export function startLeadsSchedule(deps) {
  if (!ENABLED || timer || firstTick) return;
  const run = () => void tick(deps);
  firstTick = setTimeout(() => {
    firstTick = null;
    run();
    timer = setInterval(run, TICK_MS);
  }, FIRST_TICK_MS);
}
