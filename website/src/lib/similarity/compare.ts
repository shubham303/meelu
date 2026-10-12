/**
 * Near-duplicate detection without a model.
 *
 * Three measurements, because no single number answers the question people
 * actually ask:
 *
 *  1. Five-word shingles with Jaccard containment, reported in both directions.
 *     "How much of A appears in B" is not "how much of B appears in A", and the
 *     gap between them is the whole story when one document is longer.
 *  2. TF-IDF cosine plus content-word overlap between every sentence pair, so a
 *     copied paragraph still registers after somebody swaps a few words around.
 *  3. The longest runs of identical words shared by the two texts, which is what
 *     anyone accusing anyone else of copying will actually want to point at.
 *
 * Everything here is deterministic and runs in the browser. There is no model,
 * no embedding and no network call, so it cannot read meaning — only wording.
 */

import { FREE_WORD_LIMIT, limitWords } from "@/lib/limits";
import type {
  Band,
  MatchKind,
  SentenceMatch,
  SentenceRef,
  SharedPassage,
  SideReport,
  SimilarityResult,
} from "./types";
import {
  contentTokens,
  intersectionSize,
  segments,
  shingles,
  tokenise,
  type Token,
} from "./text";

/** Per side. Big enough for a long article, small enough to stay instant. */
/** What one free comparison reads per side. Shared with the other free tools. */
export const MAX_WORDS = FREE_WORD_LIMIT;

/** Below this a sentence pair is not a match. */
export const MATCH_THRESHOLD = 0.75;
/** At or above this it is word-for-word bar a token or two. */
export const NEAR_THRESHOLD = 0.95;

export const SHINGLE_K = 5;
/** A run of shared words has to be this long before it means anything. */
export const MIN_PASSAGE_WORDS = 8;
/**
 * Fragments shorter than this are headings, navigation labels and list stubs
 * rather than evidence. They are left out of both the matched count and the
 * total, so two pages sharing a menu do not read as sharing content.
 */
export const MIN_SENTENCE_WORDS = 6;

const MAX_CANDIDATES = 12;
const MAX_PASSAGES = 12;
const ANCHOR = 4;

type Sentence = {
  index: number;
  text: string;
  start: number;
  end: number;
  tokens: string[];
  content: string[];
  contentSet: Set<string>;
  norm: string;
  words: number;
  eligible: boolean;
  vector: Map<string, number>;
};

type Side = {
  text: string;
  chars: number;
  tokens: Token[];
  words: number;
  sentences: Sentence[];
  shingles: Set<number>;
  truncated: boolean;
};

function prepare(raw: string): Side {
  const trimmed = raw.replace(/\r\n?/g, "\n");
  const capped = limitWords(trimmed, MAX_WORDS);
  const text = capped.text;
  const tokens = tokenise(text);
  const sentences: Sentence[] = segments(text).map((segment, index) => {
    const sentenceTokens = tokenise(segment.text).map((t) => t.text);
    const content = contentTokens(sentenceTokens);
    return {
      index,
      text: segment.text,
      start: segment.start,
      end: segment.end,
      tokens: sentenceTokens,
      content,
      contentSet: new Set(content),
      norm: sentenceTokens.join(" "),
      words: sentenceTokens.length,
      eligible: sentenceTokens.length >= MIN_SENTENCE_WORDS,
      vector: new Map(),
    };
  });

  const words = tokens.length;
  const k = Math.max(2, Math.min(SHINGLE_K, words));

  return {
    text,
    chars: text.length,
    tokens,
    words,
    sentences: sentences.filter((s) => s.tokens.length > 0),
    shingles: shingles(
      tokens.map((t) => t.text),
      k,
    ),
    truncated: capped.truncated,
  };
}

/**
 * IDF is computed over the two documents' sentences pooled together. A word
 * that turns up in every other sentence of both articles — "content", "page",
 * "the" — ends up weighing almost nothing, which is the point.
 */
function weight(a: Side, b: Side) {
  const all = [...a.sentences, ...b.sentences];
  const df = new Map<string, number>();
  for (const sentence of all) {
    for (const term of new Set(sentence.content)) {
      df.set(term, (df.get(term) ?? 0) + 1);
    }
  }
  const n = all.length;
  for (const sentence of all) {
    const tf = new Map<string, number>();
    for (const term of sentence.content) tf.set(term, (tf.get(term) ?? 0) + 1);
    let norm = 0;
    for (const [term, count] of tf) {
      const idf = Math.log((n + 1) / ((df.get(term) ?? 0) + 1)) + 1;
      const w = (1 + Math.log(count)) * idf;
      sentence.vector.set(term, w);
      norm += w * w;
    }
    norm = Math.sqrt(norm);
    if (norm > 0) {
      for (const [term, w] of sentence.vector) sentence.vector.set(term, w / norm);
    }
  }
}

/**
 * Posting lists, so a sentence is only ever scored against sentences it shares
 * a word with. A term that turns up in most sentences of a long document is
 * left out: it generates candidates without separating them, and it is what
 * makes the naive all-pairs version quadratic in practice.
 */
function invert(sentences: Sentence[]): Map<string, number[]> {
  const index = new Map<string, number[]>();
  for (const sentence of sentences) {
    for (const term of sentence.vector.keys()) {
      const list = index.get(term);
      if (list) list.push(sentence.index);
      else index.set(term, [sentence.index]);
    }
  }
  const cap = Math.max(200, sentences.length * 0.6);
  for (const [term, list] of index) {
    if (list.length > cap) index.delete(term);
  }
  return index;
}

function cosine(a: Map<string, number>, b: Map<string, number>): number {
  const [small, large] = a.size <= b.size ? [a, b] : [b, a];
  let sum = 0;
  for (const [term, weightA] of small) {
    const weightB = large.get(term);
    if (weightB !== undefined) sum += weightA * weightB;
  }
  return sum;
}

/** Dice coefficient over content words: 1 when the vocabulary is identical. */
function overlap(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 || b.size === 0) return 0;
  let shared = 0;
  const [small, large] = a.size <= b.size ? [a, b] : [b, a];
  for (const term of small) if (large.has(term)) shared += 1;
  return (2 * shared) / (a.size + b.size);
}

function classify(score: number, exact: boolean): MatchKind {
  if (exact) return "exact";
  return score >= NEAR_THRESHOLD ? "near" : "close";
}

type Pair = { to: number; score: number; cosine: number; overlap: number; kind: MatchKind };

/**
 * Best partner in `to` for every sentence in `from`. Candidates come from the
 * inverted index; the score is then recomputed in full so pruning never changes
 * the number that gets reported.
 */
function pairUp(
  from: Sentence[],
  to: Sentence[],
  index: Map<string, number[]>,
  byNorm: Map<string, number>,
): Array<Pair | null> {
  const out: Array<Pair | null> = new Array(from.length).fill(null);
  if (to.length === 0) return out;

  const positions = new Map<number, number>();
  to.forEach((sentence, i) => positions.set(sentence.index, i));
  const scratch = new Float64Array(to.length);

  for (let i = 0; i < from.length; i++) {
    const sentence = from[i];
    if (!sentence.eligible) continue;

    const identical = byNorm.get(sentence.norm);
    if (identical !== undefined) {
      out[i] = { to: identical, score: 1, cosine: 1, overlap: 1, kind: "exact" };
      continue;
    }

    const touched: number[] = [];
    for (const [term, weightA] of sentence.vector) {
      const list = index.get(term);
      if (!list) continue;
      for (const other of list) {
        const slot = positions.get(other);
        if (slot === undefined) continue;
        if (scratch[slot] === 0) touched.push(slot);
        scratch[slot] += weightA * (to[slot].vector.get(term) ?? 0);
      }
    }
    if (touched.length === 0) continue;

    touched.sort((x, y) => scratch[y] - scratch[x]);
    const candidates = touched.slice(0, MAX_CANDIDATES);
    for (const slot of touched) scratch[slot] = 0;

    let best: Pair | null = null;
    for (const slot of candidates) {
      const other = to[slot];
      if (!other.eligible) continue;
      const cos = cosine(sentence.vector, other.vector);
      const dice = overlap(sentence.contentSet, other.contentSet);
      const score = 0.6 * cos + 0.4 * dice;
      if (score < MATCH_THRESHOLD) continue;
      if (!best || score > best.score) {
        best = {
          to: other.index,
          score,
          cosine: cos,
          overlap: dice,
          kind: classify(score, false),
        };
      }
    }
    out[i] = best;
  }
  return out;
}

/**
 * The longest runs of identical words the two texts share. Anchored on a
 * four-word window, extended as far as it goes, then skipped past — so a
 * copied paragraph is reported once as one long run rather than a hundred
 * overlapping short ones.
 */
function sharedPassages(
  a: Side,
  b: Side,
  aSentenceAt: (offset: number) => number,
  bSentenceAt: (offset: number) => number,
): SharedPassage[] {
  const index = new Map<string, number[]>();
  for (let j = 0; j + ANCHOR <= b.tokens.length; j++) {
    let key = b.tokens[j].text;
    for (let n = 1; n < ANCHOR; n++) key += ` ${b.tokens[j + n].text}`;
    const list = index.get(key);
    if (list) {
      if (list.length < 40) list.push(j);
    } else index.set(key, [j]);
  }

  const found: SharedPassage[] = [];
  let i = 0;
  while (i + ANCHOR <= a.tokens.length) {
    let key = a.tokens[i].text;
    for (let n = 1; n < ANCHOR; n++) key += ` ${a.tokens[i + n].text}`;
    const candidates = index.get(key);
    if (!candidates) {
      i += 1;
      continue;
    }
    let bestLength = 0;
    let bestStart = -1;
    for (const j of candidates) {
      let length = ANCHOR;
      while (
        i + length < a.tokens.length &&
        j + length < b.tokens.length &&
        a.tokens[i + length].text === b.tokens[j + length].text
      ) {
        length += 1;
      }
      if (length > bestLength) {
        bestLength = length;
        bestStart = j;
      }
    }
    if (bestLength >= MIN_PASSAGE_WORDS) {
      const aStart = a.tokens[i].start;
      const aEnd = a.tokens[i + bestLength - 1].end;
      const bStart = b.tokens[bestStart].start;
      const bEnd = b.tokens[bestStart + bestLength - 1].end;
      found.push({
        text: a.text.slice(aStart, aEnd),
        words: bestLength,
        aStart,
        aEnd,
        bStart,
        bEnd,
        aSentence: aSentenceAt(aStart),
        bSentence: bSentenceAt(bStart),
      });
      i += bestLength;
      continue;
    }
    i += 1;
  }

  return found.sort((x, y) => y.words - x.words).slice(0, MAX_PASSAGES);
}

function locator(sentences: Sentence[]) {
  return (offset: number): number => {
    let low = 0;
    let high = sentences.length - 1;
    let best = -1;
    while (low <= high) {
      const mid = (low + high) >> 1;
      if (sentences[mid].start <= offset) {
        best = sentences[mid].index;
        low = mid + 1;
      } else high = mid - 1;
    }
    return best;
  };
}

function containment(mine: Set<number>, theirs: Set<number>): number {
  if (mine.size === 0) return 0;
  return intersectionSize(mine, theirs) / mine.size;
}

/** Falls back to word sets when a document is too short to shingle. */
function verbatimShare(mine: Side, theirs: Side): number {
  if (mine.shingles.size > 0 && theirs.shingles.size > 0) {
    return containment(mine.shingles, theirs.shingles);
  }
  const mineWords = new Set(mine.tokens.map((t) => t.text));
  const theirWords = new Set(theirs.tokens.map((t) => t.text));
  if (mineWords.size === 0) return 0;
  let shared = 0;
  for (const word of mineWords) if (theirWords.has(word)) shared += 1;
  return shared / mineWords.size;
}

const pct = (value: number) => Math.round(Math.min(1, Math.max(0, value)) * 100);

function refs(sentences: Sentence[]): SentenceRef[] {
  return sentences.map((s) => ({
    index: s.index,
    text: s.text,
    start: s.start,
    end: s.end,
    words: s.words,
    eligible: s.eligible,
  }));
}

function bandFor(overallScore: number): Band {
  if (overallScore < 30) return "original";
  return overallScore <= 60 ? "partial" : "high";
}

const VERDICTS: Record<Band, { verdict: string; advice: string }> = {
  original: {
    verdict: "Safe to publish",
    advice:
      "The two texts do not share enough wording to count as duplicates. Whatever they have in common is the sort of phrasing any two articles on the subject would share.",
  },
  partial: {
    verdict: "Moderate overlap",
    advice:
      "Enough shared wording to be worth a look. Work down the matched sentences: quoted material and boilerplate are fine, whole paragraphs that turned up twice are not.",
  },
  high: {
    verdict: "Heavily duplicated — rewrite",
    advice:
      "Most of one document is the other document. If both are yours, canonicalise one or merge them. If one is somebody else's, rewrite it or cite it.",
  },
};

export function compare(rawA: string, rawB: string): SimilarityResult {
  const startedAt = Date.now();
  const a = prepare(rawA);
  const b = prepare(rawB);

  weight(a, b);

  const indexA = invert(a.sentences);
  const indexB = invert(b.sentences);
  const normA = new Map<string, number>();
  for (const s of a.sentences) if (s.eligible && !normA.has(s.norm)) normA.set(s.norm, s.index);
  const normB = new Map<string, number>();
  for (const s of b.sentences) if (s.eligible && !normB.has(s.norm)) normB.set(s.norm, s.index);

  const forward = pairUp(a.sentences, b.sentences, indexB, normB);
  const backward = pairUp(b.sentences, a.sentences, indexA, normA);

  const matches: SentenceMatch[] = [];
  let exactSentences = 0;
  let nearSentences = 0;
  const uniqueA: number[] = [];
  let matchedWordsA = 0;
  let judgedWordsA = 0;

  a.sentences.forEach((sentence, i) => {
    if (!sentence.eligible) return;
    judgedWordsA += sentence.words;
    const pair = forward[i];
    if (!pair) {
      uniqueA.push(sentence.index);
      return;
    }
    matchedWordsA += sentence.words;
    if (pair.kind === "exact") exactSentences += 1;
    else if (pair.kind === "near") nearSentences += 1;
    matches.push({
      a: sentence.index,
      b: pair.to,
      score: pct(pair.score),
      cosine: pct(pair.cosine),
      overlap: pct(pair.overlap),
      kind: pair.kind,
    });
  });

  const reverse: SentenceMatch[] = [];
  const uniqueB: number[] = [];
  let matchedWordsB = 0;
  let judgedWordsB = 0;
  b.sentences.forEach((sentence, i) => {
    if (!sentence.eligible) return;
    judgedWordsB += sentence.words;
    const pair = backward[i];
    if (!pair) {
      uniqueB.push(sentence.index);
      return;
    }
    matchedWordsB += sentence.words;
    reverse.push({
      a: pair.to,
      b: sentence.index,
      score: pct(pair.score),
      cosine: pct(pair.cosine),
      overlap: pct(pair.overlap),
      kind: pair.kind,
    });
  });

  matches.sort((x, y) => y.score - x.score || x.a - y.a);
  reverse.sort((x, y) => y.score - x.score || x.b - y.b);

  const coverageA = judgedWordsA > 0 ? matchedWordsA / judgedWordsA : 0;
  const coverageB = judgedWordsB > 0 ? matchedWordsB / judgedWordsB : 0;
  const verbatimA = verbatimShare(a, b);
  const verbatimB = verbatimShare(b, a);

  const containmentA = pct(Math.max(coverageA, verbatimA));
  const containmentB = pct(Math.max(coverageB, verbatimB));
  const overall = Math.max(containmentA, containmentB);
  const band = bandFor(overall);

  const passages = sharedPassages(a, b, locator(a.sentences), locator(b.sentences));

  const sideA: SideReport = {
    label: "A",
    chars: a.chars,
    words: a.words,
    sentenceCount: a.sentences.length,
    sentences: refs(a.sentences),
    coverage: pct(coverageA),
    verbatim: pct(verbatimA),
    containment: containmentA,
    matchedWords: matchedWordsA,
    judgedWords: judgedWordsA,
    unique: uniqueA,
    truncated: a.truncated,
    text: a.text,
  };

  const sideB: SideReport = {
    label: "B",
    chars: b.chars,
    words: b.words,
    sentenceCount: b.sentences.length,
    sentences: refs(b.sentences),
    coverage: pct(coverageB),
    verbatim: pct(verbatimB),
    containment: containmentB,
    matchedWords: matchedWordsB,
    judgedWords: judgedWordsB,
    unique: uniqueB,
    truncated: b.truncated,
    text: b.text,
  };

  return {
    overall,
    band,
    verdict: VERDICTS[band].verdict,
    advice: VERDICTS[band].advice,
    a: sideA,
    b: sideB,
    matches,
    reverse,
    passages,
    longestPassageWords: passages.length > 0 ? passages[0].words : 0,
    exactSentences,
    nearSentences,
    durationMs: Date.now() - startedAt,
  };
}
