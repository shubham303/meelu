import type { Chunk } from "./types";
import {
  MAX_CHUNK_WORDS,
  MIN_CHUNK_WORDS,
  SOFT_BREAK_WORDS,
  TARGET_CHUNK_WORDS,
} from "./constants";

/** Collapse runs of whitespace but keep paragraph breaks, so offsets stay meaningful. */
export function normalise(input: string): string {
  return input
    .replace(/\r\n?/g, "\n")
    .replace(/[ \t]+/g, " ")
    .replace(/ ?\n ?/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function countWords(text: string): number {
  const matched = text.match(/[\p{L}\p{N}][\p{L}\p{N}'’-]*/gu);
  return matched ? matched.length : 0;
}

type Sentence = {
  start: number;
  end: number;
  words: number;
  /** True when this is the last sentence of its paragraph — a nicer place to cut. */
  endsParagraph: boolean;
};

function sentences(normalised: string): Sentence[] {
  const out: Sentence[] = [];

  const paraRe = /[^\n]+/g;
  let para: RegExpExecArray | null;
  while ((para = paraRe.exec(normalised)) !== null) {
    const base = para.index;
    const body = para[0];
    const found: Array<{ start: number; end: number }> = [];

    const sentRe = /[^.!?…]+(?:[.!?…]+["'”’)\]]*|$)/g;
    let match: RegExpExecArray | null;
    while ((match = sentRe.exec(body)) !== null) {
      if (!match[0].trim()) continue;
      found.push({ start: base + match.index, end: base + match.index + match[0].length });
    }
    if (found.length === 0) found.push({ start: base, end: base + body.length });

    found.forEach((span, i) => {
      out.push({
        start: span.start,
        end: span.end,
        words: countWords(normalised.slice(span.start, span.end)),
        endsParagraph: i === found.length - 1,
      });
    });
  }

  return out;
}

/**
 * Cut the text into scoring windows.
 *
 * Window size is the single biggest lever on this classifier's false-positive rate, and
 * we measured it before picking one. Feeding it 40-word windows of hand-written prose,
 * it called 61.7% of them AI. At 100 words that fell to 11.7%, and at 170–220 words to
 * zero — while genuinely generated text scored 100% at every size. Short windows are not
 * a finer-grained reading, they are a noisier one, so we cut at roughly
 * TARGET_CHUNK_WORDS and refuse to score anything under MIN_CHUNK_WORDS on its own.
 *
 * Paragraph ends are preferred break points but not hard ones — a run of short
 * paragraphs is joined rather than scored a fragment at a time.
 */
export function chunkText(normalised: string): Chunk[] {
  const chunks: Chunk[] = [];
  const all = sentences(normalised);

  let start: number | null = null;
  let end = 0;
  let words = 0;

  const flush = () => {
    if (start === null) return;
    const text = normalised.slice(start, end).trim();
    if (text) {
      chunks.push({ index: chunks.length, text, words, start, end });
    }
    start = null;
    end = 0;
    words = 0;
  };

  for (const sentence of all) {
    // A single sentence longer than a whole window: emit it in word-sized pieces.
    if (sentence.words > MAX_CHUNK_WORDS) {
      flush();
      const slice = normalised.slice(sentence.start, sentence.end);
      const wordRe = /\S+/g;
      let pieceStart = sentence.start;
      let seen = 0;
      let match: RegExpExecArray | null;
      while ((match = wordRe.exec(slice)) !== null) {
        seen += 1;
        if (seen >= TARGET_CHUNK_WORDS) {
          const wordEnd = sentence.start + match.index + match[0].length;
          const text = normalised.slice(pieceStart, wordEnd).trim();
          if (text) {
            chunks.push({ index: chunks.length, text, words: seen, start: pieceStart, end: wordEnd });
          }
          pieceStart = wordEnd;
          seen = 0;
        }
      }
      if (seen > 0) {
        start = pieceStart;
        end = sentence.end;
        words = seen;
      }
      continue;
    }

    if (start === null) start = sentence.start;
    end = sentence.end;
    words += sentence.words;

    if (words >= TARGET_CHUNK_WORDS) {
      flush();
    } else if (sentence.endsParagraph && words >= SOFT_BREAK_WORDS) {
      flush();
    }
  }

  flush();

  // Fold undersized windows into a neighbour rather than scoring a fragment, which is
  // where this model does most of its false flagging.
  for (let i = chunks.length - 1; i >= 0 && chunks.length > 1; i--) {
    const chunk = chunks[i];
    if (chunk.words >= MIN_CHUNK_WORDS) continue;

    const prev = i > 0 ? chunks[i - 1] : null;
    const next = i < chunks.length - 1 ? chunks[i + 1] : null;

    // Merge into whichever neighbour is smaller, so windows stay even.
    let into: Chunk | null = null;
    if (prev && next) into = prev.words <= next.words ? prev : next;
    else into = prev ?? next;
    if (!into) continue;
    if (into.words + chunk.words > MAX_CHUNK_WORDS) continue;

    into.start = Math.min(into.start, chunk.start);
    into.end = Math.max(into.end, chunk.end);
    into.words += chunk.words;
    into.text = normalised.slice(into.start, into.end).trim();
    chunks.splice(i, 1);
  }

  chunks.sort((a, b) => a.start - b.start);
  chunks.forEach((chunk, i) => {
    chunk.index = i;
  });
  return chunks;
}

/** One sentence of the normalised text, with the offsets needed to highlight it. */
export type SentenceSpan = {
  /** Position in the document, counted from one. */
  index: number;
  start: number;
  end: number;
  text: string;
  words: number;
};

/**
 * The same sentence split the chunker uses, exposed with offsets.
 *
 * The surface signals need to point at the exact sentence that triggered them, and a
 * second, slightly different splitter would put the highlight in a different place from
 * the window it sits inside. One splitter, one set of offsets.
 */
export function sentenceSpans(normalised: string): SentenceSpan[] {
  const out: SentenceSpan[] = [];
  for (const sentence of sentences(normalised)) {
    const raw = normalised.slice(sentence.start, sentence.end);
    const lead = raw.length - raw.trimStart().length;
    const trail = raw.length - raw.trimEnd().length;
    const start = sentence.start + lead;
    const end = sentence.end - trail;
    if (end <= start) continue;
    out.push({
      index: out.length + 1,
      start,
      end,
      text: normalised.slice(start, end),
      words: sentence.words,
    });
  }
  return out;
}
