import * as cheerio from "cheerio";
import { splitBlocks } from "@/lib/page-text/blocks";
import { absolute, sameSite } from "./url";
import type { Heading, ImageRef, LinkRef, PageKind, SchemaNode } from "./types";

const DATED_TYPES = new Set([
  "article",
  "blogposting",
  "newsarticle",
  "webpage",
  "product",
  "recipe",
  "event",
]);

type Json = string | number | boolean | null | Json[] | { [key: string]: Json };

function flattenLd(value: Json, depth = 0): Array<Record<string, Json>> {
  if (depth > 3 || !value || typeof value !== "object") return [];
  if (Array.isArray(value)) return value.flatMap((v) => flattenLd(v, depth + 1));
  const graph = value["@graph"];
  const node = value as Record<string, Json>;
  return graph ? [node, ...flattenLd(graph, depth + 1)] : [node];
}

function stated(value: Json): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim() !== "";
  if (Array.isArray(value)) return value.some(stated);
  if (typeof value === "object") return Object.keys(value).length > 0;
  return true;
}

function ldProps(node: Record<string, Json>): { keys: number; props: string[] } {
  const declared = Object.entries(node).filter(([key]) => !key.startsWith("@"));
  return {
    keys: declared.length,
    props: declared.filter(([, value]) => stated(value)).map(([key]) => key),
  };
}

/**
 * Google measures titles in pixels, not characters, so a title of capitals is
 * cut off long before one of the same length in narrow letters.
 */
function titlePixels(title: string | null): number | null {
  if (!title) return null;
  let px = 0;
  for (const ch of title) {
    if (/[ilj|!.,:;'`]/.test(ch)) px += 4;
    else if (/[A-Z@#%&WM]/.test(ch)) px += 12;
    else px += 8;
  }
  return px;
}

export type Facts = {
  title: string | null;
  titlePixels: number | null;
  metaDescription: string | null;
  h1: string[];
  headings: Heading[];
  bodyText: string;
  wordCount: number;
  outLinks: LinkRef[];
  externalLinks: LinkRef[];
  canonical: string | null;
  robotsDirectives: string | null;
  hasViewport: boolean;
  lang: string | null;
  hreflang: Record<string, string>;
  schemaTypes: string[];
  schemaNodes: SchemaNode[];
  images: ImageRef[];
  mixedContent: boolean;
  openGraph: boolean;
  twitterCard: boolean;
  favicon: boolean;
  ampHtml: string | null;
};

export function extract(html: string, url: string): Facts {
  const $ = cheerio.load(html);

  const title = $("title").not("svg title").first().text().trim() || null;
  const metaDescription =
    $('meta[name="description"]').attr("content")?.trim() || null;
  const canonical = $('link[rel="canonical"]').attr("href");
  const robotsDirectives = $('meta[name="robots"]').attr("content")?.trim() ?? null;
  const lang = $("html").attr("lang")?.trim() || null;
  const hasViewport = $('meta[name="viewport"]').length > 0;
  const ampHtml = $('link[rel="amphtml"]').attr("href") ?? null;

  const hreflang: Record<string, string> = {};
  $('link[rel="alternate"][hreflang]').each((_, el) => {
    const key = $(el).attr("hreflang");
    const href = $(el).attr("href");
    if (key && href) hreflang[key.toLowerCase()] = absolute(href, url) ?? href;
  });

  const h1 = $("h1")
    .map((_, el) => $(el).text().replace(/\s+/g, " ").trim())
    .get()
    .filter(Boolean);

  const headings: Heading[] = [];
  $("h1, h2, h3, h4, h5, h6").each((_, el) => {
    const text = $(el).text().replace(/\s+/g, " ").trim();
    if (!text) return;
    headings.push({ level: Number(el.tagName.slice(1)), text });
  });

  const outLinks: LinkRef[] = [];
  const externalLinks: LinkRef[] = [];
  $("a[href]").each((_, el) => {
    const href = $(el).attr("href");
    if (!href) return;
    const target = absolute(href, url);
    if (!target) return;
    const anchor = $(el).text().replace(/\s+/g, " ").trim().slice(0, 200);
    const rel = $(el).attr("rel") ?? null;
    const ref = { url: target, anchor, rel };
    if (sameSite(target, url)) {
      if (outLinks.length < 500) outLinks.push(ref);
    } else if (externalLinks.length < 300) {
      externalLinks.push(ref);
    }
  });

  const schemaTypes: string[] = [];
  const schemaNodes: SchemaNode[] = [];
  const schemaText: string[] = [];
  $('script[type="application/ld+json"]').each((_, el) => {
    try {
      for (const node of flattenLd(JSON.parse($(el).text()) as Json)) {
        const declared = node["@type"];
        const types =
          typeof declared === "string"
            ? [declared]
            : Array.isArray(declared)
              ? declared.map(String)
              : [];
        schemaTypes.push(...types);
        if (types.length && schemaNodes.length < 60) {
          const { keys, props } = ldProps(node);
          for (const type of types) schemaNodes.push({ type, keys, props });
        }
        if (DATED_TYPES.has(types[0]?.toLowerCase() ?? "")) {
          const name = node.name ?? node.headline;
          if (typeof name === "string") schemaText.push(name);
        }
      }
    } catch {
      // Malformed JSON-LD is itself reported by the structured-data checks.
    }
  });

  const mixedContent =
    url.startsWith("https://") &&
    $(
      "img[src^='http://'], script[src^='http://'], iframe[src^='http://'], " +
        "source[src^='http://'], video[src^='http://'], audio[src^='http://'], " +
        "embed[src^='http://'], object[data^='http://'], link[href^='http://'][rel='stylesheet']",
    ).length > 0;

  const openGraph =
    $('meta[property="og:title"]').length > 0 ||
    $('meta[property="og:description"]').length > 0 ||
    $('meta[property="og:image"]').length > 0;
  const twitterCard = $('meta[name="twitter:card"]').length > 0;
  const favicon =
    $('link[rel~="icon"]').length > 0 || $('link[rel="shortcut icon"]').length > 0;

  const images: ImageRef[] = [];
  const seenSrc = new Set<string>();
  $("img").each((_, el) => {
    if (images.length >= 200) return;
    const src = absolute($(el).attr("src") ?? "", url);
    if (!src || seenSrc.has(src)) return;
    seenSrc.add(src);
    const alt = $(el).attr("alt");
    const width = Number($(el).attr("width"));
    const height = Number($(el).attr("height"));
    const loading = $(el).attr("loading");
    images.push({
      src,
      ...(alt === undefined ? {} : { alt: alt.trim() }),
      ...(Number.isFinite(width) && width > 0 ? { width } : {}),
      ...(Number.isFinite(height) && height > 0 ? { height } : {}),
      ...(loading ? { loading } : {}),
    });
  });

  // The same block splitter the content tools read a page with, so "the
  // readable text of this page" means one thing across the site. The audit
  // keeps its own markers on the front of each line because a person reading
  // the extract wants to see which lines were headings.
  const bodyText = splitBlocks(html)
    .blocks.map((block) => {
      if (block.kind === "heading") return `${"#".repeat(block.level ?? 1)} ${block.text}`;
      if (block.kind === "list-item") return `- ${block.text}`;
      if (block.kind === "cell") return `| ${block.text}`;
      return block.text;
    })
    .join("\n");

  return {
    title,
    titlePixels: titlePixels(title),
    metaDescription,
    h1,
    headings,
    bodyText,
    wordCount: bodyText.split(/\s+/).filter(Boolean).length,
    outLinks,
    externalLinks,
    canonical: canonical ? (absolute(canonical, url) ?? canonical) : null,
    robotsDirectives,
    hasViewport,
    lang,
    hreflang,
    schemaTypes: [...new Set(schemaTypes)],
    schemaNodes,
    images,
    mixedContent,
    openGraph,
    twitterCard,
    favicon,
    ampHtml,
  };
}

export function classify(
  url: string,
  origin: string,
  schemaTypes: string[],
): PageKind {
  let path: string;
  try {
    path = new URL(url).pathname.toLowerCase();
  } catch {
    return "other";
  }
  const types = schemaTypes.map((t) => t.toLowerCase());

  if (url === origin || path === "" || path === "/") return "home";
  if (types.includes("product") || /\/(product|item|shop)\//.test(path)) return "product";
  if (/\/(pricing|plans|price)/.test(path)) return "pricing";
  if (/\/(privacy|terms|legal|cookie|disclaimer|refund)/.test(path)) return "legal";
  if (/\/(contact|support|help-desk)/.test(path)) return "contact";
  if (/\/(about|team|story|careers)/.test(path)) return "about";
  if (types.includes("faqpage")) return "docs";
  if (/\/(docs|documentation|guide|manual)\//.test(path)) return "docs";
  if (
    types.includes("article") ||
    types.includes("blogposting") ||
    types.includes("newsarticle") ||
    /\/(blog|news|article|post)\//.test(path)
  ) {
    return "article";
  }
  if (/\/(category|collection|tag|topics)\//.test(path)) return "category";
  return "other";
}
