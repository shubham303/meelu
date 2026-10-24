import { jsonCall, webSearch } from "./llm.js";

export const WEB_PLATFORM = "web";
export const WEB_OPTION = { id: WEB_PLATFORM, label: "Web search", access: "web", available: true };
export const MAX_AGE_DAYS = 30;
const MAX_POSTS = 15;
const MAX_SEARCHES = 3;
const RESULTS_PER_SEARCH = 8;
const LINE_CONCURRENCY = 3;
const SEARCH_TIMEOUT_MS = 300_000;
const MAX_TEXT_CHARS = 2000;
const DAY_MS = 24 * 60 * 60 * 1000;

const PLATFORM_HOSTS = {
  reddit: ["reddit.com", "redd.it"],
  x: ["x.com", "twitter.com"],
  linkedin: ["linkedin.com"],
  facebook: ["facebook.com"],
  hackernews: ["news.ycombinator.com"],
  stackexchange: ["stackexchange.com", "stackoverflow.com", "superuser.com", "serverfault.com", "askubuntu.com"],
  devto: ["dev.to"],
  github: ["github.com"],
  bluesky: ["bsky.app"],
};

export const WEB_SEARCHED_PLATFORMS = ["reddit", "x", "linkedin", "facebook"];

export function hostsOf(platforms) {
  return [...new Set((platforms ?? []).flatMap((p) => PLATFORM_HOSTS[p] ?? []))];
}

function scope(only, skipped) {
  if (only.length) {
    return ` Search only ${only.join(", ")}: add site:${only[0]} to every search and return only conversations on ${only.join(" or ")}.`;
  }
  return skipped.length ? ` Leave out ${skipped.join(", ")}; those are searched separately.` : "";
}

function system(siteContext, today, only, skipped) {
  return `Today is ${today}. You find public conversations a marketer could join with a helpful reply.
${siteContext ? `\nThe marketer's site:\n${siteContext}\n` : ""}
Search the web for recent conversations where someone raises what the marketer's line describes. Run several different searches and return as many distinct conversations as you find, up to ${MAX_POSTS}. Return only places where a reply can be posted: forum threads, Q&A pages, community posts and comment threads. Leave out articles, listicles, product pages, news and anything without a way to answer.${scope(only, skipped)} Who counts is decided only by the line; add no rule of your own.

Reply with ONLY a JSON object, no prose and no code fences, of this exact shape:
{"posts":[{"url":"...","title":"...","text":"...","author":"...","handle":"...","published":"YYYY-MM-DD"}]}

- At most ${MAX_POSTS} posts, only ones you actually found in a search result, each a different conversation.
- url: the exact page of the conversation.
- title: the thread or question title.
- text: what the person wrote, in their own words, from the page or the search result. A few sentences at most.
- author: their name or handle when shown, else empty.
- handle: their username as shown on the platform, such as u/name on Reddit or @name on X, else empty.
- published: the date the conversation started, from the page or the search result. Use only conversations from the last ${MAX_AGE_DAYS} days; leave out older or undated ones.
- Never invent a post, a quote or a URL.`;
}

function cleanUrl(value) {
  const raw = String(value ?? "").trim();
  if (!raw) return null;
  try {
    const url = new URL(raw.includes("://") ? raw : `https://${raw}`);
    return url.protocol === "http:" || url.protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}

function onHost(url, hosts) {
  const host = url.hostname.toLowerCase().replace(/^www\./, "");
  return hosts.some((h) => host === h || host.endsWith(`.${h}`));
}

function recentDate(value, now) {
  const raw = String(value ?? "").trim();
  if (!/^\d{4}-\d{2}-\d{2}/.test(raw)) return null;
  const at = Date.parse(raw.slice(0, 10));
  if (Number.isNaN(at) || at > now + DAY_MS || now - at > MAX_AGE_DAYS * DAY_MS) return null;
  return new Date(at).toISOString();
}

const URL_HANDLES = {
  x: /^\/([A-Za-z0-9_]{1,15})\/status\//,
  linkedin: /^\/posts\/([A-Za-z0-9-]+?)_/,
  reddit: /^\/user\/([A-Za-z0-9_-]+)/,
};

export function handleOf(platform, url, said) {
  const fromUrl = URL_HANDLES[platform]?.exec(url.pathname)?.[1];
  if (fromUrl) return fromUrl;
  const clean = String(said ?? "").trim().replace(/^@/, "").replace(/^u\//i, "");
  return /^[A-Za-z0-9_.-]{2,40}$/.test(clean) ? clean : null;
}

export function webPosts(parsed, { only = [], skipped = [], platform = null } = {}, now = Date.now()) {
  const out = [];
  for (const p of Array.isArray(parsed?.posts) ? parsed.posts : []) {
    const url = cleanUrl(p?.url);
    const postedAt = recentDate(p?.published, now);
    const title = String(p?.title ?? "").trim() || null;
    const text = String(p?.text ?? "").trim().slice(0, MAX_TEXT_CHARS) || null;
    if (!url || !postedAt || (!title && !text)) continue;
    if (only.length ? !onHost(url, only) : onHost(url, skipped)) continue;
    out.push({
      url: url.toString(),
      title,
      text,
      authorName: String(p?.author ?? "").trim() || null,
      authorHandle: platform ? handleOf(platform, url, p?.handle) : null,
      postedAt,
    });
  }
  return out.slice(0, MAX_POSTS);
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

async function searchLine(line, siteContext, scope, target) {
  const today = new Date().toISOString().slice(0, 10);
  try {
    const parsed = await jsonCall(
      system(siteContext, today, scope.only, scope.skipped),
      `The line:\n${line.text}`,
      target,
      { ...webSearch({ searches: MAX_SEARCHES, results: RESULTS_PER_SEARCH }), timeoutMs: SEARCH_TIMEOUT_MS },
    );
    return { posts: webPosts(parsed, scope), error: null };
  } catch (err) {
    return { posts: [], error: err instanceof Error ? err.message : String(err) };
  }
}

export const SKIP_HOURS = 12;

export function lineKey(text) {
  return String(text ?? "").toLowerCase().split(/\s+/).filter(Boolean).join(" ");
}

export function recentLines(lines, searches, now = Date.now()) {
  const at = new Map(searches.map((row) => [lineKey(row.query), row.searchedAt]));
  const fresh = [];
  const skippedQueries = [];
  for (const line of lines) {
    const when = at.get(lineKey(line.text));
    const time = Date.parse(when ?? "");
    if (!Number.isNaN(time) && now - time < SKIP_HOURS * 60 * 60 * 1000) {
      skippedQueries.push({ query: line.text, searchedAt: when });
    } else {
      fresh.push(line);
    }
  }
  return { fresh, skippedQueries };
}

export function searchScope(source, selected) {
  if (source === WEB_PLATFORM) {
    return { only: [], skipped: hostsOf(selected.filter((p) => p !== WEB_PLATFORM)), platform: null };
  }
  return { only: PLATFORM_HOSTS[source] ?? [], skipped: [], platform: source };
}

export async function searchWebLines({ lines, siteContext, source, selected, guard }, target) {
  const scope = searchScope(source, selected);
  const outcomes = await inPool(lines, LINE_CONCURRENCY, (line) => {
    guard();
    return searchLine(line, siteContext, scope, target);
  });
  const failed = outcomes.filter((o) => o.error);
  return {
    posts: outcomes.flatMap((o) => o.posts),
    searchedLines: outcomes.length,
    failedLines: failed.length,
    searchedQueries: lines.filter((_, i) => !outcomes[i].error).map((line) => line.text),
    error: failed[0]?.error ?? null,
  };
}
