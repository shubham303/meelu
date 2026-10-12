/**
 * The shape of a page once it has been read. Kept apart from the extractor so
 * client components can name these types without pulling a server-only parser
 * into the browser bundle.
 */

export type BlockKind = "heading" | "paragraph" | "list-item" | "quote" | "cell" | "caption";

export interface PageBlock {
  /** Position on the page, counted from one, so the order survives sorting. */
  index: number;
  /** The element the text came out of: p, h2, li and so on. */
  tag: string;
  kind: BlockKind;
  /** 1 to 6 for headings, absent otherwise. */
  level?: number;
  text: string;
  words: number;
}

export interface PageExtract {
  title: string | null;
  blocks: PageBlock[];
  /** Every block joined with newlines, which is what a document score reads. */
  text: string;
  words: number;
  truncated: boolean;
  /** True when the article finder found nothing and the whole page was read. */
  usedFallback: boolean;
}

/** Past this a page is an archive listing, not an article worth scoring. */
export const MAX_BLOCKS = 400;

/** Long enough for a very long essay, short enough to keep the response small. */
export const MAX_EXTRACT_CHARS = 200_000;
