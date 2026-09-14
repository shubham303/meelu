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

export function extract(html, url, status) {
  const $ = cheerio.load(html);

  const title = $("title").not("svg title").first().text().trim() || null;
  const metaDescription = $('meta[name="description"]').attr("content")?.trim() || null;
  const canonical = $('link[rel="canonical"]').attr("href");
  const robotsDirectives = $('meta[name="robots"]').attr("content") ?? null;
  const lang = $("html").attr("lang") ?? null;
  const hasViewport = $('meta[name="viewport"]').length > 0;

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

  const outLinks = [];
  const externalLinks = [];
  $("a[href]").each((_, el) => {
    const href = $(el).attr("href");
    if (!href) return;
    const target = abs(href, url);
    if (!target) return;
    const anchor = $(el).text().replace(/\s+/g, " ").trim().slice(0, 200);
    const rel = $(el).attr("rel") ?? null;
    if (sameSite(target, url)) outLinks.push({ url: target, anchor, rel });
    else externalLinks.push({ url: target, anchor, rel });
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

  $("script, style, noscript, svg").remove();
  const blocks = [];

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

    blocks.push(line);
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
    lang,
    hreflang,
    schemaTypes: [...new Set(schemaTypes)],
    schemaNodes,
    author: author || null,
    images,
    publishedAt,
    modifiedAt,
    wordCount,
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
