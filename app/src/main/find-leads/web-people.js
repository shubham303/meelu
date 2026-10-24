import { jsonCall, webSearch } from "../social-signals/llm.js";
import { handleOf, hostsOf } from "../social-signals/web.js";
import { angleDecision, MAX_AGE_DAYS, queryKey } from "./web.js";

const MAX_PEOPLE = 15;
const MAX_SEARCHES = 3;
const RESULTS_PER_SEARCH = 8;
const SEARCH_TIMEOUT_MS = 300_000;
const SNIPPET_CHARS = 600;
const QUOTE_CHARS = 400;
const DAY_MS = 24 * 60 * 60 * 1000;
const LINKEDIN_PROFILE = /^\/in\/([^/?#]+)/;

const PLATFORM_NAMES = { reddit: "Reddit", x: "X (Twitter)", linkedin: "LinkedIn" };

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

function clip(text, size) {
  return String(text ?? "").split(/\s+/).filter(Boolean).join(" ").slice(0, size);
}

export function linkedinQuery(plan) {
  return [plan?.query ?? "", (plan?.titles ?? []).join(", "), (plan?.locations ?? []).join(", ")]
    .map((part) => part.trim())
    .filter(Boolean)
    .join(" | ");
}

function peopleSystem(siteContext, today) {
  return `Today is ${today}. You find people on LinkedIn a founder could contact personally about their product.
${siteContext ? `\nThe founder's site:\n${siteContext}\n` : ""}
Search the web for public LinkedIn profile pages (linkedin.com/in/...) of people who match the brief and the search you are given. Add site:linkedin.com/in to every search. Return as many distinct people as you find, up to ${MAX_PEOPLE}. Who counts is decided only by the brief; add no rule of your own.

Reply with ONLY a JSON object, no prose and no code fences, of this exact shape:
{"people":[{"name":"...","headline":"...","profileUrl":"...","location":"...","why":"..."}]}

- Only people you actually found in a search result, each a different person.
- profileUrl: the linkedin.com/in/ address exactly as found.
- headline: their role and company as shown in the result. location: as shown, else empty.
- why: one plain sentence on what in the result matches the brief.
- Never invent a person, a headline or a URL.`;
}

export function linkedinPeople(parsed) {
  const out = [];
  for (const p of Array.isArray(parsed?.people) ? parsed.people : []) {
    const url = cleanUrl(p?.profileUrl);
    const name = clip(p?.name, 120);
    if (!url || !name || !onHost(url, ["linkedin.com"]) || !LINKEDIN_PROFILE.test(url.pathname)) continue;
    out.push({
      name,
      headline: clip(p?.headline, 200) || null,
      profileUrl: `https://www.linkedin.com${url.pathname.match(LINKEDIN_PROFILE)[0]}/`,
      location: clip(p?.location, 120) || null,
      why: clip(p?.why, 300) || null,
    });
  }
  return out.slice(0, MAX_PEOPLE);
}

export function personCandidate(brief, person) {
  return {
    briefId: brief.id,
    name: person.name,
    headline: person.headline,
    profileUrl: person.profileUrl,
    snippet: [person.headline, person.location, person.why].filter(Boolean).join(" · ").slice(0, SNIPPET_CHARS),
    evidence: [],
  };
}

function authorsSystem(platform, siteContext, today) {
  const hosts = hostsOf([platform]);
  return `Today is ${today}. You find people on ${PLATFORM_NAMES[platform]} a founder could contact personally about their product.
${siteContext ? `\nThe founder's site:\n${siteContext}\n` : ""}
Search the web for recent posts on ${hosts.join(" or ")} where the author shows they match the brief, for example by asking for help with the problem it describes. Add site:${hosts[0]} to every search. Return as many distinct posts as you find, up to ${MAX_PEOPLE}. Who counts is decided only by the brief; add no rule of your own.

Reply with ONLY a JSON object, no prose and no code fences, of this exact shape:
{"posts":[{"url":"...","title":"...","text":"...","author":"...","handle":"...","published":"YYYY-MM-DD"}]}

- Only posts you actually found in a search result, each by a different author.
- url: the exact address of the post.
- text: what the author wrote, in their own words, from the result. A few sentences at most.
- handle: the author's username as shown, such as u/name or @name. Leave out posts where no author is shown.
- published: the date of the post. Use only posts from the last ${MAX_AGE_DAYS} days; leave out older or undated ones.
- Never invent a post, a quote, a person or a URL.`;
}

export function authorPosts(platform, parsed, now = Date.now()) {
  const hosts = hostsOf([platform]);
  const byHandle = new Map();
  for (const p of Array.isArray(parsed?.posts) ? parsed.posts : []) {
    const url = cleanUrl(p?.url);
    const at = recentDate(p?.published, now);
    const text = clip(p?.text, QUOTE_CHARS);
    const title = clip(p?.title, 160);
    if (!url || !at || !onHost(url, hosts) || (!text && !title)) continue;
    const handle = handleOf(platform, url, p?.handle);
    if (!handle || byHandle.has(handle.toLowerCase())) continue;
    byHandle.set(handle.toLowerCase(), {
      handle,
      name: clip(p?.author, 120) || handle,
      url: url.toString(),
      quote: [title, text].filter(Boolean).join(" · ").slice(0, QUOTE_CHARS),
      at,
    });
  }
  return [...byHandle.values()].slice(0, MAX_PEOPLE);
}

export function authorCandidate(brief, post) {
  return {
    briefId: brief.id,
    name: post.name,
    handle: post.handle,
    snippet: post.quote.slice(0, SNIPPET_CHARS),
    evidence: [{ url: post.url, quote: post.quote, at: post.at }],
  };
}

async function searchOnce({ key, earlier, remember, skipped, run, parse, guard }) {
  guard();
  const before = earlier.get(key);
  const decision = angleDecision(before);
  if (decision === "cache") return { found: parse(before.results), cached: true };
  if (decision === "skip") {
    skipped.push({ query: key, searchedAt: before.searchedAt });
    return { found: [], cached: false };
  }
  const found = await run();
  await remember(key, found);
  return { found, cached: false };
}

export async function searchLinkedinPeople({ brief, siteContext, guard, earlier, remember }, target) {
  const query = linkedinQuery(brief.plan?.linkedin);
  const skipped = [];
  const { found, cached } = await searchOnce({
    key: queryKey(`linkedin people: ${query}`),
    earlier,
    remember,
    skipped,
    guard,
    parse: (results) => linkedinPeople({ people: results }),
    run: async () => {
      const today = new Date().toISOString().slice(0, 10);
      const parsed = await jsonCall(
        peopleSystem(siteContext, today),
        `The brief:\n${brief.text}\n\nSearch:\n${query}`,
        target,
        { ...webSearch({ searches: MAX_SEARCHES, results: RESULTS_PER_SEARCH }), timeoutMs: SEARCH_TIMEOUT_MS },
      );
      return linkedinPeople(parsed);
    },
  });
  return { candidates: found.map((p) => personCandidate(brief, p)), skipped, fromCache: cached ? 1 : 0 };
}

export async function searchPostAuthors({ brief, platform, siteContext, guard, earlier, remember }, target) {
  const keywords = (brief.plan?.keywords ?? []).join(", ");
  const skipped = [];
  const { found, cached } = await searchOnce({
    key: queryKey(`${platform} authors: ${brief.text} | ${keywords}`),
    earlier,
    remember,
    skipped,
    guard,
    parse: (results) =>
      authorPosts(platform, {
        posts: results.map((r) => ({ url: r.url, text: r.quote, author: r.name, handle: r.handle, published: r.at })),
      }),
    run: async () => {
      const today = new Date().toISOString().slice(0, 10);
      const parsed = await jsonCall(
        authorsSystem(platform, siteContext, today),
        `The brief:\n${brief.text}${keywords ? `\n\nSearch words:\n${keywords}` : ""}`,
        target,
        { ...webSearch({ searches: MAX_SEARCHES, results: RESULTS_PER_SEARCH }), timeoutMs: SEARCH_TIMEOUT_MS },
      );
      return authorPosts(platform, parsed);
    },
  });
  return { candidates: found.map((p) => authorCandidate(brief, p)), skipped, fromCache: cached ? 1 : 0 };
}
