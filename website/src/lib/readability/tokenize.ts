/**
 * Sentence, paragraph and word splitting.
 *
 * Every readability formula divides by the sentence count, so a splitter that
 * breaks on "Dr." or "3.5" does not produce a slightly wrong score. It produces
 * a badly wrong one. Dots that are not full stops are masked before the split
 * and put back afterwards.
 */

/** A character that cannot appear in pasted prose, used to hide non-terminal dots. */
const MASK = "\u0001";

/** Abbreviations whose full stop does not end a sentence. */
export const ABBREVIATIONS = [
  "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "mt", "rev", "hon", "gen",
  "col", "capt", "lt", "sgt", "messrs", "fig", "figs", "vs", "etc", "al", "inc",
  "ltd", "co", "corp", "dept", "est", "vol", "pp", "approx", "cf", "eg", "ie",
  "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sept", "sep", "oct", "nov",
  "dec", "mon", "tue", "tues", "wed", "thur", "thurs", "thu", "fri", "sat", "sun",
];

const ABBREVIATION_RE = new RegExp(`\\b(?:${ABBREVIATIONS.join("|")})\\.`, "gi");

const WORD_RE = /[A-Za-z0-9À-ɏ]+(?:['’-][A-Za-z0-9À-ɏ]+)*/g;
const LETTER_RE = /[A-Za-z0-9À-ɏ]/g;

const CLOSERS = "\"')]}”’»";
const TERMINATORS = ".!?";

function maskDots(text: string): string {
  return (
    text
      // decimals and version numbers: 3.5, 1.25, v2.0
      .replace(/(\d)\.(\d)/g, `$1${MASK}$2`)
      // dotted acronyms: U.S.A., e.g., a.m., Ph.D.
      .replace(/\b(?:[A-Za-z]\.){2,}/g, (m) => m.replace(/\./g, MASK))
      // titles and short forms: Dr. Smith, etc.
      .replace(ABBREVIATION_RE, (m) => m.replace(/\./g, MASK))
      // initials: J. R. R. Tolkien
      .replace(/\b([A-Z])\.(?=\s)/g, `$1${MASK}`)
      // ellipses
      .replace(/\.{2,}/g, (m) => MASK.repeat(m.length))
  );
}

function unmask(text: string): string {
  return text.split(MASK).join(".");
}

/**
 * Paragraphs. Every non-empty line counts as one, which is how a CMS editor
 * treats a line break, and it stops a heading being glued to the sentence
 * underneath it.
 */
export function splitParagraphs(text: string): string[] {
  return text
    .split(/\r?\n+/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

/** Sentences inside one paragraph. A paragraph with no full stop is one sentence. */
export function splitSentences(paragraph: string): string[] {
  const masked = maskDots(paragraph);
  const out: string[] = [];
  let start = 0;
  let i = 0;

  while (i < masked.length) {
    if (!TERMINATORS.includes(masked[i])) {
      i += 1;
      continue;
    }
    let end = i + 1;
    while (end < masked.length && TERMINATORS.includes(masked[end])) end += 1;
    while (end < masked.length && CLOSERS.includes(masked[end])) end += 1;

    if (end >= masked.length || /\s/.test(masked[end])) {
      const piece = masked.slice(start, end).trim();
      if (piece.length > 0) out.push(unmask(piece));
      start = end;
    }
    i = end;
  }

  const tail = masked.slice(start).trim();
  if (tail.length > 0) out.push(unmask(tail));
  return out;
}

/** Words. Hyphenated compounds and contractions stay whole; numbers count as words. */
export function splitWords(text: string): string[] {
  return text.match(WORD_RE) ?? [];
}

/** Letters and digits only, no spaces and no punctuation. ARI and Coleman-Liau need this. */
export function countLetters(text: string): number {
  return (text.match(LETTER_RE) ?? []).length;
}
