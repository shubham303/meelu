/**
 * Reads a fetched HTML page the way a reader does.
 *
 * This is the one page-text extractor on the site — the readability checker,
 * the AI detector, the similarity checker and the sentiment analyzers all read
 * a page through here, so a page means the same thing to every tool.
 *
 * Finding the article inside a page is a problem with twenty years of edge
 * cases in it, so that part is Mozilla's Readability — the code behind Firefox
 * Reader Mode. It also rebuilds paragraphs on pages that never had any, which
 * older essays laid out as <br><br> between <font> runs do not. What it returns
 * is clean article HTML; turning that into ordered, scoreable passages is ours.
 *
 * Server only: it parses a DOM. Import the types from ./types in components.
 */

import { Readability } from "@mozilla/readability";
import { parseHTML } from "linkedom";
import { countWords, splitBlocks } from "./blocks";
import { MAX_EXTRACT_CHARS, type PageExtract } from "./types";

/** Readability's own floor for "is there an article here at all". */
const CHAR_THRESHOLD = 250;

/**
 * Below this share of the page's readable words, the article finder is assumed
 * to have cut too deep — a Q&A page or a link-heavy post can lose its body —
 * and the whole page is read instead.
 */
const COVERAGE_FLOOR = 0.5;

function documentTitle(html: string): string | null {
  const match = /<title[^>]*>([\s\S]{0,300}?)<\/title>/i.exec(html);
  return match ? match[1].replace(/\s+/g, " ").trim() || null : null;
}

export function extractPageText(html: string): PageExtract {
  const capped = html.slice(0, MAX_EXTRACT_CHARS * 6);
  const fallbackTitle = documentTitle(capped);

  let article: { title: string | null; content: string } | null = null;
  try {
    const { document } = parseHTML(capped);
    const parsed = new Readability(document, { charThreshold: CHAR_THRESHOLD }).parse();
    if (parsed?.content) {
      article = { title: parsed.title?.trim() || null, content: parsed.content };
    }
  } catch {
    // A page too broken to parse is not a reason to fail; read it whole below.
  }

  const whole = splitBlocks(capped);

  let chosen = whole;
  let usedFallback = true;
  let title = fallbackTitle;

  if (article) {
    const inner = splitBlocks(article.content);
    const innerWords = countWords(inner.blocks.map((b) => b.text).join(" "));
    // The article has to account for a fair share of the page's words. Below
    // that, Readability has thrown away the body rather than the furniture.
    if (innerWords > 0 && innerWords >= whole.pageWords * COVERAGE_FLOOR) {
      chosen = inner;
      usedFallback = false;
      title = article.title ?? fallbackTitle;
    }
  }

  const text = chosen.blocks.map((b) => b.text).join("\n");
  return {
    title,
    blocks: chosen.blocks,
    text,
    words: countWords(text),
    truncated: chosen.truncated,
    usedFallback,
  };
}
