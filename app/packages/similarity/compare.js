import { DEFAULT_MAX_WORDS, limitWords } from "./limits.js";
import { contentTokens, intersectionSize, segments, shingles, tokenise } from "./text.js";

export const MATCH_THRESHOLD = 0.75;
export const NEAR_THRESHOLD = 0.95;
export const SHINGLE_K = 5;
export const MIN_PASSAGE_WORDS = 8;
export const MIN_SENTENCE_WORDS = 6;

const MAX_CANDIDATES = 12;
const MAX_PASSAGES = 12;
const ANCHOR = 4;

function prepare(raw, maxWords) {
  const trimmed = raw.replace(/\r\n?/g, "\n");
  const capped = limitWords(trimmed, maxWords);
  const text = capped.text;
  const tokens = tokenise(text);
  const sentences = segments(text).map((segment, index) => {
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

function weight(a, b) {
  const all = [...a.sentences, ...b.sentences];
  const df = new Map();
  for (const sentence of all) {
    for (const term of new Set(sentence.content)) {
      df.set(term, (df.get(term) ?? 0) + 1);
    }
  }
  const n = all.length;
  for (const sentence of all) {
    const tf = new Map();
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

function invert(sentences) {
  const index = new Map();
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

function cosine(a, b) {
  const [small, large] = a.size <= b.size ? [a, b] : [b, a];
  let sum = 0;
  for (const [term, weightA] of small) {
    const weightB = large.get(term);
    if (weightB !== undefined) sum += weightA * weightB;
  }
  return sum;
}

function overlap(a, b) {
  if (a.size === 0 || b.size === 0) return 0;
  let shared = 0;
  const [small, large] = a.size <= b.size ? [a, b] : [b, a];
  for (const term of small) if (large.has(term)) shared += 1;
  return (2 * shared) / (a.size + b.size);
}

function classify(score, exact) {
  if (exact) return "exact";
  return score >= NEAR_THRESHOLD ? "near" : "close";
}

function pairUp(from, to, index, byNorm) {
  const out = new Array(from.length).fill(null);
  if (to.length === 0) return out;

  const positions = new Map();
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

    const touched = [];
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

    let best = null;
    for (const slot of candidates) {
      const other = to[slot];
      if (!other.eligible) continue;
      const cos = cosine(sentence.vector, other.vector);
      const dice = overlap(sentence.contentSet, other.contentSet);
      const score = 0.6 * cos + 0.4 * dice;
      if (score < MATCH_THRESHOLD) continue;
      if (!best || score > best.score) {
        best = { to: other.index, score, cosine: cos, overlap: dice, kind: classify(score, false) };
      }
    }
    out[i] = best;
  }
  return out;
}

function sharedPassages(a, b, aSentenceAt, bSentenceAt) {
  const index = new Map();
  for (let j = 0; j + ANCHOR <= b.tokens.length; j++) {
    let key = b.tokens[j].text;
    for (let n = 1; n < ANCHOR; n++) key += ` ${b.tokens[j + n].text}`;
    const list = index.get(key);
    if (list) {
      if (list.length < 40) list.push(j);
    } else index.set(key, [j]);
  }

  const found = [];
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

function locator(sentences) {
  return (offset) => {
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

function containment(mine, theirs) {
  if (mine.size === 0) return 0;
  return intersectionSize(mine, theirs) / mine.size;
}

function verbatimShare(mine, theirs) {
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

const pct = (value) => Math.round(Math.min(1, Math.max(0, value)) * 100);

function refs(sentences) {
  return sentences.map((s) => ({
    index: s.index,
    text: s.text,
    start: s.start,
    end: s.end,
    words: s.words,
    eligible: s.eligible,
  }));
}

export function bandFor(overallScore) {
  if (overallScore < 30) return "original";
  return overallScore <= 60 ? "partial" : "high";
}

export const VERDICTS = {
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

function sideReport(label, side, matched, unique) {
  return {
    label,
    chars: side.chars,
    words: side.words,
    sentenceCount: side.sentences.length,
    sentences: refs(side.sentences),
    coverage: pct(matched.coverage),
    verbatim: pct(matched.verbatim),
    containment: pct(Math.max(matched.coverage, matched.verbatim)),
    matchedWords: matched.matchedWords,
    judgedWords: matched.judgedWords,
    unique,
    truncated: side.truncated,
    text: side.text,
  };
}

export function compare(rawA, rawB, { maxWords = DEFAULT_MAX_WORDS } = {}) {
  const startedAt = Date.now();
  const a = prepare(String(rawA ?? ""), maxWords);
  const b = prepare(String(rawB ?? ""), maxWords);

  weight(a, b);

  const indexA = invert(a.sentences);
  const indexB = invert(b.sentences);
  const normA = new Map();
  for (const s of a.sentences) if (s.eligible && !normA.has(s.norm)) normA.set(s.norm, s.index);
  const normB = new Map();
  for (const s of b.sentences) if (s.eligible && !normB.has(s.norm)) normB.set(s.norm, s.index);

  const forward = pairUp(a.sentences, b.sentences, indexB, normB);
  const backward = pairUp(b.sentences, a.sentences, indexA, normA);

  const matches = [];
  let exactSentences = 0;
  let nearSentences = 0;
  const uniqueA = [];
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

  const reverse = [];
  const uniqueB = [];
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

  const sideA = sideReport(
    "A",
    a,
    {
      coverage: judgedWordsA > 0 ? matchedWordsA / judgedWordsA : 0,
      verbatim: verbatimShare(a, b),
      matchedWords: matchedWordsA,
      judgedWords: judgedWordsA,
    },
    uniqueA,
  );
  const sideB = sideReport(
    "B",
    b,
    {
      coverage: judgedWordsB > 0 ? matchedWordsB / judgedWordsB : 0,
      verbatim: verbatimShare(b, a),
      matchedWords: matchedWordsB,
      judgedWords: judgedWordsB,
    },
    uniqueB,
  );

  const overall = Math.max(sideA.containment, sideB.containment);
  const band = bandFor(overall);
  const passages = sharedPassages(a, b, locator(a.sentences), locator(b.sentences));

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
