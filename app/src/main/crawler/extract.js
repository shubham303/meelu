import * as cheerio from "cheerio";
import { createHash } from "node:crypto";
import { sameSite } from "./url.js";

const BLOCK_SELECTOR = "p, li, h1, h2, h3, h4, h5, h6, td, th, dd, dt, blockquote, figcaption";

export function sha(text) {
  return createHash("sha256").update(text).digest("hex").slice(0, 32);
}

function abs(href, base) {
  try {
    const u = new URL(href, base);
    if (u.protocol !== "http:" && u.protocol !== "https:") return undefined;
    u.hash = "";
    if (u.pathname.length > 1 && u.pathname.endsWith("/")) u.pathname = u.pathname.slice(0, -1);
    return u.toString();
  } catch {
    return undefined;
  }
}

function schemaLines(value, depth = 0) {
  if (depth > 4 || value === null || value === undefined) return [];
  if (typeof value === "string" || typeof value === "number") return [String(value)];
  if (Array.isArray(value)) return value.flatMap((v) => schemaLines(v, depth + 1));
  if (typeof value === "object") {
    const out = [];
    for (const [k, v] of Object.entries(value)) {
      if (k.startsWith("@")) continue;
      const inner = schemaLines(v, depth + 1);
      if (inner.length === 0) continue;
      const joined = inner.join(" ").trim();
      if (joined) out.push(`${k}: ${joined}`);
    }
    return out;
  }
  return [];
}

const DATED_TYPES = new Set([
  "article",
  "blogposting",
  "newsarticle",
  "webpage",
  "product",
  "recipe",
  "event",
]);

function flattenLd(value, depth = 0) {
  if (depth > 3 || !value || typeof value !== "object") return [];
  if (Array.isArray(value)) return value.flatMap((v) => flattenLd(v, depth + 1));
  const graph = value["@graph"];
  return graph ? [value, ...flattenLd(graph, depth + 1)] : [value];
}

function stated(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim() !== "";
  if (Array.isArray(value)) return value.some(stated);
  if (typeof value === "object") return Object.keys(value).length > 0;
  return true;
}

function ldProps(node) {
  const declared = Object.entries(node).filter(([key]) => !key.startsWith("@"));
  return {
    keys: declared.length,
    props: declared.filter(([, value]) => stated(value)).map(([key]) => key),
  };
}

function ldDate(value) {
  if (typeof value !== "string") return null;
  const at = Date.parse(value);
  if (!Number.isFinite(at)) return null;
  const year = new Date(at).getUTCFullYear();
  if (year < 1990 || year > new Date().getUTCFullYear() + 1) return null;
  return new Date(at).toISOString();
}

function titlePixels(title) {
  if (!title) return null;
  let px = 0;
  for (const ch of title) {
    if (/[ilj|!.,:;'`]/.test(ch)) px += 4;
    else if (/[A-Z@#%&WM]/.test(ch)) px += 12;
    else px += 8;
  }
  return px;
}


const REGION_MARKERS = [
  ["breadcrumb", (el, cls, id, role, aria, tag) =>
    /breadcrumb/.test(cls) || /breadcrumb/.test(id) || /breadcrumb/.test(aria) ||
    /BreadcrumbList/.test(el.attribs?.itemtype ?? "")],
  ["pagination", (el, cls, id, role, aria, tag) =>
    /pagination|pager|page-numbers/.test(cls) || /pagination|pager/.test(id) || /pagination/.test(aria)],
  ["footer", (el, cls, id, role, aria, tag) =>
    tag === "footer" || role === "contentinfo" || /(^|[\s_-])footer/.test(cls) || /footer/.test(id)],
  ["header", (el, cls, id, role, aria, tag) =>
    tag === "header" || role === "banner" || /(^|[\s_-])(site-|page-|main-)?header/.test(cls) || /^(site-|page-|main-)?header/.test(id)],
  ["nav", (el, cls, id, role, aria, tag) =>
    tag === "nav" || role === "navigation" || role === "menubar" || /(^|[\s_-])(nav|menu)/.test(cls) || /(^|[\s_-])(nav|menu)/.test(id)],
  ["aside", (el, cls, id, role, aria, tag) =>
    tag === "aside" || role === "complementary" || /(^|[\s_-])sidebar/.test(cls) || /sidebar/.test(id)],
];

function markedRegion(el) {
  for (let node = el; node && node.type === "tag"; node = node.parent) {
    const tag = node.tagName?.toLowerCase() ?? "";
    if (tag === "body" || tag === "html") break;
    const cls = (node.attribs?.class ?? "").toLowerCase();
    const id = (node.attribs?.id ?? "").toLowerCase();
    const role = (node.attribs?.role ?? "").toLowerCase();
    const aria = (node.attribs?.["aria-label"] ?? "").toLowerCase();
    for (const [region, test] of REGION_MARKERS) {
      if (test(node, cls, id, role, aria, tag)) return region;
    }
  }
  return null;
}

function inBreadcrumbTrail($, el, url, breadcrumbUrls) {
  if (breadcrumbUrls.size === 0) return false;
  for (let node = el.parent; node && node.type === "tag"; node = node.parent) {
    const links = $(node).find("a[href]");
    if (links.length < 2) continue;
    if (links.length > breadcrumbUrls.size + 1) return false;
    return links.get().every((a) => breadcrumbUrls.has(abs($(a).attr("href") ?? "", url) ?? ""));
  }
  return false;
}

function inside(el, ancestor) {
  for (let node = el; node; node = node.parent) if (node === ancestor) return true;
  return false;
}

function sentenceContext(text, anchor, limit = 300) {
  if (text.length <= limit) return text;
  const at = anchor ? Math.max(text.indexOf(anchor), 0) : 0;
  const bounds = [...text.matchAll(/[.!?](?=\s)/g)].map((m) => m.index + 1);
  let start = 0;
  for (const b of bounds) if (b <= at) start = b;
  let end = text.length;
  for (const b of bounds) if (b > at + anchor.length) { end = b; break; }
  let out = text.slice(start, end).trim();
  if (out.length > limit) {
    const from = Math.max(0, Math.min(at - start - limit / 2, out.length - limit));
    out = out.slice(from, from + limit).trim();
  }
  return out;
}

function breadcrumbTargets($, url) {
  const targets = new Set();
  $('script[type="application/ld+json"]').each((_, el) => {
    try {
      for (const node of flattenLd(JSON.parse($(el).text()))) {
        if (String(node["@type"] ?? "").toLowerCase() !== "breadcrumblist") continue;
        for (const item of node.itemListElement ?? []) {
          const target = item?.item?.["@id"] ?? item?.item?.url ?? item?.item ?? item?.url;
          const resolved = typeof target === "string" ? abs(target, url) : undefined;
          if (resolved) targets.add(resolved);
        }
      }
    } catch {
    }
  });
  return targets;
}

function extractLinks($, url, { scope, blockOrdinal, blockText, breadcrumbUrls }) {
  const internal = new Map();
  const externalLinks = [];
  let passedScope = false;
  $("a[href]").each((_, el) => {
    const href = $(el).attr("href");
    if (!href) return;
    const target = abs(href, url);
    if (!target) return;
    const anchor = $(el).text().replace(/\s+/g, " ").trim().slice(0, 200);
    const rel = $(el).attr("rel") ?? null;
    const inScope = scope ? inside(el, scope) : true;
    if (inScope) passedScope = true;

    let region = markedRegion(el);
    if (/(^|\s)(next|prev|previous)(\s|$)/.test((rel ?? "").toLowerCase())) region = "pagination";
    if (region === null && inBreadcrumbTrail($, el, url, breadcrumbUrls)) region = "breadcrumb";
    if (region === null && !inScope) region = passedScope ? "footer" : "header";
    if (region === null) region = "body";

    if (!sameSite(target, url)) {
      externalLinks.push({ url: target, anchor, rel, region });
      return;
    }

    const key = `${region} ${target}`;
    const seen = internal.get(key);
    if (seen) {
      seen.count += 1;
      return;
    }
    const entry = { url: target, anchor, rel, region, count: 1 };
    if (region === "body") {
      const block = $(el).closest(BLOCK_SELECTOR).get(0);
      const ordinal = block ? blockOrdinal.get(block) : undefined;
      if (ordinal !== undefined) {
        entry.ordinal = ordinal;
        entry.context = sentenceContext(blockText.get(block), anchor);
      }
    }
    internal.set(key, entry);
  });
  return { outLinks: [...internal.values()], externalLinks };
}

export function extract(html, url, status) {
  const $ = cheerio.load(html);

  const title = $("title").not("svg title").first().text().trim() || null;
  const metaDescription = $('meta[name="description"]').attr("content")?.trim() || null;
  const canonical = $('link[rel="canonical"]').attr("href");
  const robotsDirectives = $('meta[name="robots"]').attr("content") ?? null;
  const lang = $("html").attr("lang") ?? null;
  const hasViewport = $('meta[name="viewport"]').length > 0;
  const viewportMeta = $('meta[name="viewport"]').first().attr("content")?.trim() || null;
  const nosnippetCount = $("[data-nosnippet]").length;
  const socialMetaCount = $('meta[property^="og:"], meta[name^="twitter:"]').length;
  const socialMeta = {};
  $('meta[property^="og:"], meta[name^="twitter:"]').each((_, el) => {
    const key = $(el).attr("property") ?? $(el).attr("name");
    let content = $(el).attr("content")?.trim();
    if (!key || !content || key in socialMeta) return;
    if (/^(og:image|og:url|twitter:image)/.test(key)) content = abs(content, url) ?? content;
    socialMeta[key] = content;
  });

  const hreflang = {};
  $('link[rel="alternate"][hreflang]').each((_, el) => {
    const k = $(el).attr("hreflang");
    const href = $(el).attr("href");
    if (k && href) hreflang[k] = abs(href, url) ?? href;
  });

  const h1 = $("h1")
    .map((_, el) => $(el).text().trim())
    .get()
    .filter(Boolean);

  const headings = [];
  $("h1, h2, h3, h4, h5, h6").each((i, el) => {
    const text = $(el).text().replace(/\s+/g, " ").trim();
    if (!text) return;
    headings.push({ level: Number(el.tagName.slice(1)), text, ordinal: i });
  });

  const schemaTypes = [];
  const schemaNodes = [];
  const schemaText = [];
  let publishedAt = null;
  let modifiedAt = null;
  $('script[type="application/ld+json"]').each((_, el) => {
    try {
      for (const node of flattenLd(JSON.parse($(el).text()))) {
        const t = node["@type"];
        const types = typeof t === "string" ? [t] : Array.isArray(t) ? t.map(String) : [];
        schemaTypes.push(...types);
        schemaText.push(...schemaLines(node));

        if (types.length && schemaNodes.length < 60) {
          const { keys, props } = ldProps(node);
          for (const type of types) schemaNodes.push({ type, keys, props });
        }

        const dated = types.some((x) => DATED_TYPES.has(x.toLowerCase()));
        const pub = ldDate(node.datePublished);
        const mod = ldDate(node.dateModified);
        if (pub && (dated || !publishedAt)) publishedAt = pub;
        if (mod && (dated || !modifiedAt)) modifiedAt = mod;
      }
    } catch {
    }
  });

  const author =
    $('meta[name="author"]').attr("content") ?? $('[rel="author"]').first().text().trim() ?? null;

  const mixedContent =
    url.startsWith("https://") &&
    $(
      "img[src^='http://'], script[src^='http://'], iframe[src^='http://'], " +
        "source[src^='http://'], video[src^='http://'], audio[src^='http://'], " +
        "embed[src^='http://'], object[data^='http://'], link[href^='http://'][rel='stylesheet']",
    ).length > 0;

  const gaScriptSrc = $("script[src]")
    .toArray()
    .some((el) => {
      const src = $(el).attr("src") ?? "";
      return (
        /googletagmanager\.com\/(gtag\/js|gtm\.js)/i.test(src) ||
        /google-analytics\.com\/(analytics|ga)\.js/i.test(src)
      );
    });
  const gaInline = $("script:not([src])")
    .toArray()
    .some((el) => {
      const text = $(el).text();
      return (
        /gtag\s*\(\s*['"]config['"]\s*,\s*['"](G|UA|AW|DC)-/i.test(text) ||
        /googletagmanager\.com\/gtm\.js/i.test(text) ||
        /GoogleAnalyticsObject/.test(text)
      );
    });
  const hasGoogleAnalytics = gaScriptSrc || gaInline;

  const breadcrumbUrls = breadcrumbTargets($, url);
  $("script, style, noscript, svg").remove();
  const blocks = [];
  const blockOrdinal = new Map();
  const blockText = new Map();

  const scoped = [$("main"), $("article")].find((el) => el.find(BLOCK_SELECTOR).length > 0);
  const root = scoped ?? $("body");
  root.find(BLOCK_SELECTOR).each((_, el) => {
    const tag = el.tagName?.toLowerCase() ?? "p";
    const text = $(el).text().replace(/\s+/g, " ").trim();
    if (!text) return;

    let line = text;
    if (/^h[1-6]$/.test(tag)) line = `${"#".repeat(Number(tag[1]))} ${text}`;
    else if (tag === "li") line = `- ${text}`;
    else if (tag === "td" || tag === "th") line = `| ${text}`;

    blockOrdinal.set(el, blocks.length);
    blockText.set(el, text);
    blocks.push(line);
  });

  const { outLinks, externalLinks } = extractLinks($, url, {
    scope: scoped ? scoped.get(0) : null,
    blockOrdinal,
    blockText,
    breadcrumbUrls,
  });

  const parts = schemaText.length ? [...blocks, ...schemaText] : blocks;

  const images = [];
  const seenSrc = new Set();
  $("img").each((_, el) => {
    if (images.length >= 100) return;
    const src = abs($(el).attr("src") ?? "", url);
    if (!src || seenSrc.has(src)) return;
    seenSrc.add(src);
    const alt = $(el).attr("alt");
    const width = Number($(el).attr("width"));
    const height = Number($(el).attr("height"));
    images.push({
      src,
      ...(alt === undefined ? {} : { alt: alt.trim() }),
      ...(Number.isFinite(width) && width > 0 ? { width } : {}),
      ...(Number.isFinite(height) && height > 0 ? { height } : {}),
    });
  });

  const bodyText = parts.join("\n");
  const wordCount = bodyText.split(/\s+/).filter(Boolean).length;
  const bodyExternalLinks = externalLinks.filter((l) => l.region === "body").length;
  const externalLinkDensity = wordCount > 0 ? (bodyExternalLinks * 100) / wordCount : null;

  return {
    url,
    status,
    title,
    titlePixels: titlePixels(title),
    metaDescription,
    h1,
    headings,
    bodyText,
    outLinks,
    externalLinks,
    canonical: canonical ? (abs(canonical, url) ?? canonical) : null,
    robotsDirectives,
    hasViewport,
    viewportMeta,
    nosnippetCount,
    socialMetaCount,
    socialMeta,
    hasGoogleAnalytics,
    lang,
    hreflang,
    schemaTypes: [...new Set(schemaTypes)],
    schemaNodes,
    author: author || null,
    images,
    publishedAt,
    modifiedAt,
    wordCount,
    externalLinkDensity,
    mixedContent,
    contentHash: sha(blocks.join("\n")),
  };
}

export function classify(facts, origin) {
  const path = new URL(facts.url).pathname.toLowerCase();
  const types = facts.schemaTypes.map((t) => t.toLowerCase());

  if (facts.url === origin || path === "" || path === "/") return { kind: "home" };
  if (types.includes("product") || /\/(product|item|shop)\//.test(path)) return { kind: "product" };
  if (/\/(pricing|plans|price)/.test(path)) return { kind: "pricing" };
  if (/\/(privacy|terms|legal|cookie|disclaimer|refund)/.test(path)) return { kind: "legal" };
  if (/\/(contact|support|help-desk)/.test(path)) return { kind: "contact" };
  if (/\/(about|team|story|careers)/.test(path)) return { kind: "about" };
  if (types.includes("faqpage")) return { kind: "docs" };
  if (/\/(docs|documentation|guide|manual)\//.test(path)) return { kind: "docs" };
  if (
    types.includes("article") ||
    types.includes("blogposting") ||
    types.includes("newsarticle") ||
    /\/(blog|news|article|post)\//.test(path)
  ) {
    return { kind: "article", format: guessFormat(facts) };
  }
  if (/\/(category|collection|tag|topics)\//.test(path)) return { kind: "category" };
  return { kind: "other" };
}

function guessFormat(facts) {
  const t = (facts.title ?? "").toLowerCase();
  if (/^how to|^how i\b/.test(t)) return "how-to";
  if (/^\d+\s/.test(t)) return "listicle";
  if (/\bvs\.?\b|\bcompared?\b/.test(t)) return "comparison";
  if (/case study/.test(t)) return "case study";
  return null;
}

export function shallowReason(facts, kind) {
  if (kind === "legal") return "legal";
  if (/[?&]page=\d+|\/page\/\d+/.test(facts.url)) return "pagination";
  if (facts.wordCount < 80) return "thin";
  return null;
}
