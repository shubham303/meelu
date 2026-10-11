import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";
import { extract } from "../crawler/extract.js";
import { fetchPage } from "../crawler/fetch.js";
import { crawlToken } from "../crawler/token.js";
import { jsonCall } from "../social-signals/llm.js";

const TICK_MS = Number(process.env.MEELU_SITE_SUMMARY_TICK_MS ?? 30 * 60 * 1000);
const FIRST_TICK_MS = Number(process.env.MEELU_SITE_SUMMARY_FIRST_TICK_MS ?? 60 * 1000);
const PAGE_CHARS = 6000;

const SYSTEM = `You write the one-paragraph description of a website that every later task reads to know what the business is, and you name the market it serves.
Reply with ONLY a JSON object — no prose, no code fences — of this exact shape:
{"summary":"...","markets":["US"],"language":"en"}

- 2 to 4 plain sentences: what the business offers, who it is for, and what sets it apart if the page says so.
- Use only what the page states. Never invent products, prices, locations or claims.
- Write in the third person, naming the business. No marketing adjectives the page does not use.
- If the page says too little to tell what the business does, return "summary":"".
- "markets": two-letter country codes (ISO 3166, GB for the United Kingdom) of the countries the business sells to or serves. Deduce them from evidence: a country domain such as .co.uk or .de, prices in a local currency, addresses, phone numbers, shipping or service areas. List only countries the page gives evidence for; a business that serves everyone, or a page with no such signal, gets [].
- "language": the two-letter code of the language the page is written in, such as en or de.`;

const inFlight = new Set();
const attempted = new Set();
let timer = null;
let firstTick = null;

async function meelu(path, { cookieHeader, method = "GET", body } = {}) {
  const res = await apiFetch(`${ENV_DEFAULTS.meeluBaseUrl}/api/v1${path}`, {
    method,
    headers: {
      ...meeluAuthHeaders(cookieHeader),
      ...(body ? { "content-type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(payload?.error?.message ?? `${path} failed (${res.status})`);
  return payload.data;
}

async function readHomepage(domain) {
  const url = `https://${domain}/`;
  const page = await fetchPage(url, {}, crawlToken(domain));
  if (page.error) throw new Error(`Could not reach ${url}: ${page.error}`);
  if (!page.html || page.status >= 400) {
    throw new Error(`${url} answered ${page.status ?? "without a page"}.`);
  }
  return extract(page.html, page.finalUrl ?? url, page.status);
}

function pageBrief(site, facts) {
  return [
    `Business name: ${site.name}`,
    `Website: ${site.domain}`,
    facts.title ? `Title: ${facts.title}` : "",
    facts.metaDescription ? `Meta description: ${facts.metaDescription}` : "",
    facts.socialMeta?.["og:description"] ? `Share description: ${facts.socialMeta["og:description"]}` : "",
    facts.h1.length ? `H1: ${facts.h1.join(" | ")}` : "",
    "",
    "Homepage text:",
    facts.bodyText.slice(0, PAGE_CHARS),
  ]
    .filter((line) => line !== "")
    .join("\n");
}

function described(site) {
  return Boolean(site.summary) && (site.markets?.length ?? 0) > 0;
}

function recordChanges(site, answer) {
  const changes = {};
  const summary = typeof answer?.summary === "string" ? answer.summary.trim() : "";
  if (!site.summary && summary) changes.summary = summary;
  if (!site.markets?.length) {
    const markets = Array.isArray(answer?.markets)
      ? answer.markets.filter((c) => typeof c === "string" && /^[A-Za-z]{2}$/.test(c.trim()))
      : [];
    if (markets.length) changes.markets = markets.map((c) => c.trim().toUpperCase());
    const language = typeof answer?.language === "string" ? answer.language.trim().toLowerCase() : "";
    if (!site.language && /^[a-z]{2}$/.test(language)) changes.language = language;
  }
  return changes;
}

export async function describeSite(siteId, { cookieHeader, llm, emit = () => {}, log = () => {} }) {
  if (!siteId || inFlight.has(siteId)) return { started: false };
  inFlight.add(siteId);
  attempted.add(siteId);
  emit("summary:start", { siteId });
  try {
    const site = await meelu(`/sites/${siteId}`, { cookieHeader });
    if (described(site)) {
      emit("summary:done", { siteId, ok: true, skipped: true });
      return { started: false, skipped: true };
    }
    const facts = await readHomepage(site.domain);
    const answer = await jsonCall(SYSTEM, pageBrief(site, facts), {
      llm,
      cookieHeader,
      siteId,
      purpose: "site_summary",
    });
    const changes = recordChanges(site, answer);
    if (!site.summary && !changes.summary) {
      throw new Error(`The homepage of ${site.domain} says too little to describe the site.`);
    }
    if (Object.keys(changes).length) {
      await meelu(`/sites/${siteId}`, { cookieHeader, method: "PATCH", body: changes });
    }
    const summary = changes.summary ?? site.summary;
    log(`described ${site.domain}`);
    emit("summary:done", { siteId, ok: true, summary });
    return { started: true, summary };
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err);
    log(`describing site ${siteId} failed:`, error);
    emit("summary:done", { siteId, ok: false, error });
    return { started: true, error };
  } finally {
    inFlight.delete(siteId);
  }
}

async function tick({ cookieHeader, llm, emit, log }) {
  const cookie = await cookieHeader().catch(() => "");
  if (!cookie && !ENV_DEFAULTS.meeluApiKey) return;
  const sites = await meelu("/sites?page_size=100", { cookieHeader: cookie }).catch(() => null);
  if (!Array.isArray(sites)) return;
  for (const site of sites) {
    if (!site?.id || described(site) || attempted.has(site.id)) continue;
    await describeSite(site.id, { cookieHeader: cookie, llm: llm(), emit, log });
  }
}

export function startSiteSummarySchedule({ cookieHeader, llm, emit, log }) {
  if (timer || firstTick) return;
  const run = () => void tick({ cookieHeader, llm, emit, log });
  firstTick = setTimeout(() => {
    firstTick = null;
    run();
    timer = setInterval(run, TICK_MS);
  }, FIRST_TICK_MS);
}
