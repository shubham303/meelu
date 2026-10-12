/**
 * What the free tools will read in one go.
 *
 * One number, counted in words rather than characters, because a word is the
 * unit a writer thinks in and because two tools quoting different character
 * caps for "the same" limit is confusing. It applies to pasted text and to a
 * fetched page alike: the same article has to score the same however it
 * arrived, and it cannot do that if one path is cut in a different place.
 */
export const FREE_WORD_LIMIT = 5_000;

const WORD = /\S+/g;

export interface WordLimit {
  text: string;
  /** True when there was more text than the limit allows. */
  truncated: boolean;
}

/**
 * Cuts `text` after `max` words, on a word boundary, leaving line breaks where
 * they are — paragraph structure is what the passage views are built on.
 */
export function limitWords(text: string, max: number = FREE_WORD_LIMIT): WordLimit {
  WORD.lastIndex = 0;
  let seen = 0;
  let cut = -1;
  let match: RegExpExecArray | null;

  while ((match = WORD.exec(text)) !== null) {
    seen += 1;
    if (seen === max) {
      cut = match.index + match[0].length;
      break;
    }
  }

  if (cut < 0 || text.slice(cut).trim().length === 0) {
    return { text, truncated: false };
  }
  return { text: text.slice(0, cut), truncated: true };
}

export function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}
