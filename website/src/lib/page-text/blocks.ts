/**
 * Splits HTML into the passages a reader meets, in order.
 *
 * The one block splitter on the site: the content tools feed it an article that
 * Readability has already isolated, and the SEO audit feeds it a whole page. A
 * bug in reading a page is fixed here, once.
 */

import * as cheerio from "cheerio";
import { MAX_BLOCKS, MAX_EXTRACT_CHARS, type BlockKind, type PageBlock } from "./types";

/** Markup that is furniture rather than reading matter. */
const STRIPPED =
  "script, style, noscript, svg, template, iframe, object, embed, canvas, " +
  "nav, header, footer, aside, form, button, select, textarea, label, " +
  "[hidden], [aria-hidden='true'], [role='navigation'], " +
  "[role='banner'], [role='contentinfo'], [role='search'], [role='complementary']";

const BLOCK_SELECTOR =
  "p, li, h1, h2, h3, h4, h5, h6, blockquote, dd, dt, figcaption, td, th";

function kindOf(tag: string): BlockKind {
  if (/^h[1-6]$/.test(tag)) return "heading";
  if (tag === "li" || tag === "dd" || tag === "dt") return "list-item";
  if (tag === "blockquote") return "quote";
  if (tag === "td" || tag === "th") return "cell";
  if (tag === "figcaption") return "caption";
  return "paragraph";
}

export function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

function tidy(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

/**
 * Paragraphs inside one element's text, split where the author left a blank
 * line. A <br> is a line break and two of them are a paragraph break, which on
 * an older page is the only paragraph mark there is.
 */
function paragraphsIn(text: string): string[] {
  return text
    .split(/\n\s*\n+/)
    .map(tidy)
    .filter((part) => part.length > 0);
}

export interface SplitResult {
  blocks: PageBlock[];
  truncated: boolean;
  /** Readable words on the page as a whole, whether or not a block caught them. */
  pageWords: number;
}

/**
 * Only leaf blocks are kept: a `li` wrapping a `p` would otherwise be counted
 * twice, once as the list item and once as the paragraph inside it.
 */
export function splitBlocks(html: string): SplitResult {
  const $ = cheerio.load(html.slice(0, MAX_EXTRACT_CHARS * 6));

  $(STRIPPED).remove();

  // Before any text is read: a <br> carries no whitespace of its own, so
  // "August 2026<br>How should" reads as "2026How" — one invented word, and a
  // sentence boundary lost. Turning every break into a newline keeps the
  // author's line structure, which on a page that lays an essay out as <font>
  // runs instead of <p> elements is the only paragraph mark there is.
  $("br").replaceWith("\n");

  const root = $("body").length > 0 ? $("body") : $("*").first();

  const blocks: PageBlock[] = [];
  const seen = new Set<string>();
  let truncated = false;
  let chars = 0;

  const push = (tag: string, kind: BlockKind, level: number | null, text: string) => {
    if (blocks.length >= MAX_BLOCKS || chars + text.length > MAX_EXTRACT_CHARS) {
      truncated = true;
      return;
    }
    chars += text.length + 1;
    blocks.push({
      index: blocks.length + 1,
      tag,
      kind,
      ...(level ? { level } : {}),
      text,
      words: countWords(text),
    });
  };

  root.find(BLOCK_SELECTOR).each((_, el) => {
    if (truncated) return;

    const node = $(el);
    if (node.find(BLOCK_SELECTOR).length > 0) return;

    const tag = (el.tagName ?? "p").toLowerCase();
    const isHeading = /^h[1-6]$/.test(tag);
    const raw = node.text();
    if (tidy(raw).length < 2) return;

    // A heading that is nothing but a link is a card in a "related posts" or
    // "read next" list, not a heading in the document. Those lists sit in plain
    // sections no landmark selector catches, and their headlines are dense noun
    // phrases that drag a score away from the article's own prose.
    if (isHeading && tidy(node.find("a").text()) === tidy(raw)) return;

    const parts = paragraphsIn(raw);
    // A cell holding several paragraphs is a page laid out in a table, not a
    // table of data — the pieces are paragraphs, whatever element held them.
    const asParagraphs = parts.length > 1 && !isHeading;
    const level = /^h([1-6])$/.exec(tag);

    for (const part of parts) {
      // Navigation that escaped the strip tends to repeat itself word for word.
      const key = `${tag}:${part.toLowerCase()}`;
      if (seen.has(key)) continue;
      seen.add(key);

      push(
        asParagraphs ? "p" : tag,
        asParagraphs ? "paragraph" : kindOf(tag),
        level ? Number(level[1]) : null,
        part,
      );
      if (truncated) return;
    }
  });

  return { blocks, truncated, pageWords: countWords(tidy(root.text())) };
}
