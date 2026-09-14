import * as cheerio from "cheerio";
import { sha } from "./extract.js";
import { fetchPage, pool } from "./fetch.js";

const SAMPLE_PATH = /^\/[a-z0-9][a-z0-9\-/_.]*$/;
const MIN_COMPARABLE_TEXT = 200;

function absolute(href, base) {
  try {
    const u = new URL(href, base);
    if (u.protocol !== "http:" && u.protocol !== "https:") return null;
    u.hash = "";
    return u.toString();
  } catch {
    return null;
  }
}

function facts(html, url) {
  const $ = cheerio.load(html);
  const href = $('link[rel="canonical"]').attr("href");
  $("script, style, noscript, template").remove();
  const text = $("body").text().replace(/\s+/g, " ").trim();
  return {
    canonical: href ? absolute(href.trim(), url) : null,
    fingerprint: text.length >= MIN_COMPARABLE_TEXT ? sha(text) : null,
  };
}

async function read(url, crawlToken) {
  const res = await fetchPage(url, {}, crawlToken);
  const hops = res.chain?.length ?? 0;

  if (res.error || res.loop || res.tooManyHops) {
    return { url, failed: true, status: null, hops, finalUrl: null, canonical: null, fingerprint: null };
  }

  const finalUrl = res.finalUrl ?? url;
  const { canonical, fingerprint } = res.html
    ? facts(res.html, finalUrl)
    : { canonical: null, fingerprint: null };

  return { url, failed: false, status: res.status ?? null, hops, finalUrl, canonical, fingerprint };
}

function sameTarget(a, b) {
  if (!a || !b) return false;
  try {
    const x = new URL(a);
    const y = new URL(b);
    const pathOf = (u) => (u.pathname === "" ? "/" : u.pathname);
    return (
      x.protocol === y.protocol &&
      x.host.toLowerCase() === y.host.toLowerCase() &&
      pathOf(x) === pathOf(y) &&
      x.search === y.search
    );
  } catch {
    return false;
  }
}

function judge(baseline, variant, target) {
  if (variant.failed || variant.status === null) return "unknown";
  if (variant.hops > 0) return sameTarget(variant.finalUrl, target) ? "redirects" : "elsewhere";
  if (variant.status >= 400) return "absent";
  if (variant.status !== 200 || !variant.fingerprint) return "unknown";
  if (variant.fingerprint !== baseline.fingerprint) return "distinct";
  return sameTarget(variant.canonical, target) ? "canonicalised" : "duplicate";
}

function usable(probe) {
  return !!probe && !probe.failed && probe.status === 200 && !!probe.fingerprint;
}

function toggleWww(host) {
  return host.startsWith("www.") ? host.slice(4) : `www.${host}`;
}

function sampleUrl(worklist, preferredOrigin) {
  const paths = [];
  for (const raw of worklist) {
    let u;
    try {
      u = new URL(raw);
    } catch {
      continue;
    }
    if (u.search) continue;
    const pathname = u.pathname;
    if (pathname.length < 2 || pathname.endsWith("/")) continue;
    if (!SAMPLE_PATH.test(pathname) || !/[a-z]/.test(pathname)) continue;
    paths.push(pathname);
  }

  paths.sort(
    (a, b) => a.split("/").length - b.split("/").length || a.length - b.length || a.localeCompare(b),
  );
  return paths.length ? new URL(paths[0], preferredOrigin).toString() : null;
}

function uppercased(url) {
  try {
    const u = new URL(url);
    const upper = u.pathname.toUpperCase();
    if (upper === u.pathname) return null;
    u.pathname = upper;
    return u.toString();
  } catch {
    return null;
  }
}

export async function probeHostVariants(origin, worklist = [], crawlToken = null) {
  const checkedAt = new Date().toISOString();
  const home = await read(new URL("/", origin).toString(), crawlToken);

  let preferredOrigin;
  try {
    preferredOrigin = new URL(home.finalUrl ?? origin).origin;
  } catch {
    preferredOrigin = new URL(origin).origin;
  }
  const preferred = `${preferredOrigin}/`;

  if (!usable(home)) return { checkedAt, preferred, sample: null, variants: [] };

  const preferredUrl = new URL(preferred);
  const planned = [];

  if (preferredUrl.protocol === "https:") {
    planned.push({
      kind: "scheme",
      url: `http://${preferredUrl.host}/`,
      target: preferred,
      baseline: home,
    });
  }
  const otherHostOrigin = `${preferredUrl.protocol}//${toggleWww(preferredUrl.host)}`;
  planned.push({
    kind: "host",
    url: `${otherHostOrigin}/`,
    target: preferred,
    baseline: home,
  });

  const sample = sampleUrl(worklist, preferredOrigin);
  const sampleHome = sample ? await read(sample, crawlToken) : null;

  if (sample) {
    planned.push({
      kind: "host-path",
      url: new URL(new URL(sample).pathname, otherHostOrigin).toString(),
      target: sample,
      baseline: sampleHome ?? home,
    });
  }

  if (sample && usable(sampleHome) && sampleHome.hops === 0) {
    planned.push({
      kind: "trailing-slash",
      url: `${sample}/`,
      target: sample,
      baseline: sampleHome,
    });
    const upper = uppercased(sample);
    if (upper) {
      planned.push({ kind: "case", url: upper, target: sample, baseline: sampleHome });
    }
  }

  const results = await pool(planned, 4, (plan) => read(plan.url, crawlToken));

  return {
    checkedAt,
    preferred,
    sample,
    variants: planned.map((plan, i) => {
      const result = results[i];
      return {
        kind: plan.kind,
        url: plan.url,
        target: plan.target,
        verdict: judge(plan.baseline, result, plan.target),
        status: result.status,
        hops: result.hops,
        finalUrl: result.finalUrl,
        canonical: result.canonical,
      };
    }),
  };
}
