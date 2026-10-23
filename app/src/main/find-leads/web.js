import { crawlFetch, withOutboundSlot } from "../net.js";
import { jsonCall, webSearch } from "../social-signals/llm.js";

const MAX_RESULTS = 15;
const MAX_SEARCHES = 3;
const RESULTS_PER_SEARCH = 8;
const ANGLE_CONCURRENCY = 3;
const EMAIL_CONCURRENCY = 6;
export const MAX_AGE_DAYS = 30;
const DAY_MS = 24 * 60 * 60 * 1000;
const HOUR_MS = 60 * 60 * 1000;
export const CACHE_HOURS = 6;
export const SKIP_HOURS = 12;
const SEARCH_TIMEOUT_MS = 300_000;
const PAGE_TIMEOUT_MS = 15_000;
const MAX_PAGE_CHARS = 400_000;
const FALLBACK_PATHS = ["/contact", "/about"];
const SNIPPET_CHARS = 600;

const MAILTO = /mailto:([^"'?\s>]+)/gi;
const EMAIL = /\b[A-Za-z0-9][A-Za-z0-9._%+-]{0,63}@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}\b/g;
const FILE_SUFFIX = /\.(png|jpe?g|gif|webp|svg|avif|ico|css|js|woff2?)$/i;
const IGNORED_LOCAL = /^(no-?reply|do-?not-?reply|mailer-daemon|postmaster|abuse|example|test|user|email|name|your\.?name|you)$/i;
const IGNORED_DOMAINS = /(^|\.)((example|domain|email|yourdomain|sentry|wixpress|sentry-next)\.(com|org|net|io)|sentry\.io)$/i;

function system(siteContext, today) {
  return `Today is ${today}. You find real people and small businesses a founder could contact personally about their product.
${siteContext ? `\nThe founder's site:\n${siteContext}\n` : ""}
Search the web for people who match the founder's brief, following the search angle you are given. Run several different searches and return as many distinct matches as you find, up to ${MAX_RESULTS}. Return only named people or small businesses that have their own website, because the founder will reach them through it: their own site, a profile on a directory or marketplace that links to it, or something they wrote. Skip anonymous or unnamed forum posters and lists that only name others without their sites. Who counts is decided only by the brief; add no rule of your own.

Reply with ONLY a JSON object, no prose and no code fences, of this exact shape:
{"results":[{"name":"...","headline":"...","website":"...","url":"...","kind":"site","published":"","why":"..."}]}

- At most ${MAX_RESULTS} results, only ones you actually found in a search result, each a different person or business.
- name: the person or business. headline: their role or what the business does, a few words.
- website: their own site's home page. Leave out anyone without one.
- url: the exact page where you found them.
- kind: "site" when that page is their own website, profile or listing; "post" when it is a post, thread, article or announcement they wrote.
- published: for a "post", the date it was published as YYYY-MM-DD, from the page or the search result. Use only posts from the last ${MAX_AGE_DAYS} days; leave out older or undated ones. Empty for a "site".
- why: one plain sentence on what you saw that matches the brief.
- Never invent an email address, a person or a URL.`;
}

function cleanUrl(value) {
  const raw = String(value ?? "").trim();
  if (!raw) return null;
  try {
    const url = new URL(raw.includes("://") ? raw : `https://${raw}`);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

function recentDate(value, now) {
  const raw = String(value ?? "").trim();
  if (!/^\d{4}-\d{2}-\d{2}/.test(raw)) return null;
  const at = Date.parse(raw.slice(0, 10));
  if (Number.isNaN(at) || at > now + DAY_MS || now - at > MAX_AGE_DAYS * DAY_MS) return null;
  return new Date(at).toISOString();
}

export function webResults(parsed, now = Date.now()) {
  const out = [];
  for (const r of Array.isArray(parsed?.results) ? parsed.results : []) {
    const url = cleanUrl(r?.url);
    const website = cleanUrl(r?.website);
    const name = String(r?.name ?? "").trim();
    const post = String(r?.kind ?? "").trim().toLowerCase() === "post";
    const published = recentDate(r?.published, now);
    if (!url || !name || !website || (post && !published)) continue;
    out.push({
      name,
      headline: String(r?.headline ?? "").trim() || null,
      website,
      url,
      published: post ? published : null,
      why: String(r?.why ?? "").trim() || null,
    });
  }
  return out.slice(0, MAX_RESULTS);
}

function usable(email) {
  const clean = email.trim().replace(/^[<(]|[>).,;:]+$/g, "").toLowerCase();
  const at = clean.lastIndexOf("@");
  if (at <= 0) return null;
  const local = clean.slice(0, at);
  const domain = clean.slice(at + 1);
  if (FILE_SUFFIX.test(clean) || IGNORED_LOCAL.test(local) || IGNORED_DOMAINS.test(domain)) return null;
  if (!/^[a-z0-9.-]+\.[a-z]{2,24}$/.test(domain) || /^\d/.test(domain.split(".").at(-2) ?? "")) {
    return null;
  }
  return clean;
}

export function emailIn(html) {
  const text = String(html ?? "");
  for (const m of text.matchAll(MAILTO)) {
    let raw = m[1];
    try {
      raw = decodeURIComponent(raw);
    } catch {}
    const email = usable(raw);
    if (email) return email;
  }
  for (const m of text.matchAll(EMAIL)) {
    const email = usable(m[0]);
    if (email) return email;
  }
  return null;
}

async function pageHtml(url) {
  try {
    return await withOutboundSlot(async () => {
      const res = await crawlFetch(url, {
        redirect: "follow",
        signal: AbortSignal.timeout(PAGE_TIMEOUT_MS),
      });
      if (!res.ok || !String(res.headers.get("content-type") ?? "").includes("html")) return null;
      return (await res.text()).slice(0, MAX_PAGE_CHARS);
    });
  } catch {
    return null;
  }
}

export function contactPages(result) {
  const pages = [result.url];
  const base = result.website ?? result.url;
  try {
    const origin = new URL(base).origin;
    for (const path of FALLBACK_PATHS) pages.push(`${origin}${path}`);
  } catch {}
  return [...new Set(pages)];
}

async function publicEmail(result, guard) {
  for (const page of contactPages(result)) {
    guard();
    const html = await pageHtml(page);
    const email = html ? emailIn(html) : null;
    if (email) return { email, emailSourceUrl: page };
  }
  return { email: null, emailSourceUrl: null };
}

export function candidateOf(brief, result, contact) {
  return {
    briefId: brief.id,
    name: result.name,
    headline: result.headline,
    website: result.website,
    profileUrl: result.url,
    email: contact.email,
    emailSourceUrl: contact.emailSourceUrl,
    snippet: [result.headline, result.why].filter(Boolean).join(" · ").slice(0, SNIPPET_CHARS),
    evidence: result.why
      ? [{ url: result.url, quote: result.why, ...(result.published ? { at: result.published } : {}) }]
      : [],
  };
}

function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return url;
  }
}

export function distinctResults(groups) {
  const seen = new Map();
  for (const result of groups.flat()) {
    const key = hostOf(result.website);
    if (!seen.has(key)) seen.set(key, result);
  }
  return [...seen.values()];
}

export function searchAngles(brief) {
  const angles = (brief?.plan?.web ?? []).map((a) => String(a ?? "").trim()).filter(Boolean);
  return angles.length > 0 ? angles : [brief.text];
}

async function inPool(items, size, work) {
  const out = new Array(items.length);
  let cursor = 0;
  const worker = async () => {
    while (cursor < items.length) {
      const index = cursor;
      cursor += 1;
      out[index] = await work(items[index]);
    }
  };
  await Promise.all(Array.from({ length: Math.min(size, items.length) }, worker));
  return out;
}

async function searchAngle(brief, angle, siteContext, target) {
  const today = new Date().toISOString().slice(0, 10);
  const prompt = `The brief:\n${brief.text}\n\nSearch angle:\n${angle}`;
  try {
    const parsed = await jsonCall(system(siteContext, today), prompt, target, {
      ...webSearch({ searches: MAX_SEARCHES, results: RESULTS_PER_SEARCH }),
      timeoutMs: SEARCH_TIMEOUT_MS,
    });
    return { results: webResults(parsed), error: null };
  } catch (err) {
    return { results: [], error: err };
  }
}

export function queryKey(value) {
  return String(value ?? "").split(/\s+/).filter(Boolean).join(" ");
}

export function cachedResults(results) {
  return results.map((r) => ({ ...r, kind: r.published ? "post" : "site" }));
}

export function angleDecision(earlier, now = Date.now()) {
  const at = Date.parse(earlier?.searchedAt ?? "");
  if (Number.isNaN(at)) return "search";
  if (now - at < CACHE_HOURS * HOUR_MS && Array.isArray(earlier.results)) return "cache";
  if (now - at < SKIP_HOURS * HOUR_MS) return "skip";
  return "search";
}

export async function searchWeb({ brief, siteContext, guard, earlier, remember }, target) {
  const angles = searchAngles(brief);
  const skipped = [];
  let fromCache = 0;
  const outcomes = await inPool(angles, ANGLE_CONCURRENCY, async (angle) => {
    guard();
    const key = queryKey(angle);
    const before = earlier.get(key);
    const decision = angleDecision(before);
    if (decision === "cache") {
      fromCache += 1;
      return { results: webResults({ results: before.results }), error: null };
    }
    if (decision === "skip") {
      skipped.push({ query: key, searchedAt: before.searchedAt });
      return { results: [], error: null };
    }
    const outcome = await searchAngle(brief, angle, siteContext, target);
    if (!outcome.error) await remember(key, cachedResults(outcome.results));
    return outcome;
  });
  const failed = outcomes.filter((o) => o.error);
  if (failed.length > 0 && failed.length === outcomes.length) throw failed[0].error;
  const results = distinctResults(outcomes.map((o) => o.results));
  const candidates = await inPool(results, EMAIL_CONCURRENCY, async (result) => {
    guard();
    return candidateOf(brief, result, await publicEmail(result, guard));
  });
  return { candidates, skipped, fromCache };
}
