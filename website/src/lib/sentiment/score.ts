import {
  BOOSTERS,
  BOOSTER_INCREMENT,
  NEGATIONS,
  NEGATION_SCALAR,
  reviewLexicon,
  reviewPhrases,
} from "./lexicon";
import type { Label, Scored, TermHit } from "./types";

/**
 * A rule-based sentiment scorer in the VADER tradition: a valence lexicon plus
 * the five things that change what a word means in a sentence — negation,
 * degree modifiers, capitalisation, punctuation and the word "but".
 *
 * Rule-based rather than a neural classifier on purpose. It is deterministic,
 * needs no model download, gets through ten thousand rows in the time a model
 * takes to load, and — unlike a binary classifier fine-tuned on SST-2 — it
 * produces a real neutral class, which is the point when you are triaging
 * reviews rather than forcing every one into positive or negative.
 */

/** Constants from the VADER paper. Do not tune these casually. */
const CAPS_BOOST = 0.733;
const EXCLAMATION_BOOST = 0.292;
const QUESTION_BOOST_MANY = 0.96;
const QUESTION_BOOST_FEW = 0.18;
const ALPHA = 15;

/** Band edges for the three-way label. */
export const POSITIVE_AT = 0.05;
export const NEGATIVE_AT = -0.05;

/** Marks a folded multi-word phrase. Never occurs in real review text. */
const PHRASE_MARK = "\u0001";

const EDGE_PUNCT = /^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu;
const CONTRAST_WORDS = new Set(["but", "however", "although", "though"]);

interface Valence {
  /** Index into the token array, so the contrast rule knows what sits where. */
  at: number;
  value: number;
  hit: TermHit;
}

function isWordy(token: string): boolean {
  return /[\p{L}\p{N}]/u.test(token);
}

function stripPunct(token: string): string {
  const bare = token.replace(EDGE_PUNCT, "");
  return bare.length > 0 ? bare : token;
}

function isCaps(token: string): boolean {
  return token === token.toUpperCase() && /\p{Lu}/u.test(token);
}

/** ALL CAPS only reads as emphasis when the whole text is not already shouting. */
function hasMixedCaps(tokens: string[]): boolean {
  let caps = 0;
  let words = 0;
  for (const token of tokens) {
    if (!isWordy(token)) continue;
    words += 1;
    if (isCaps(token)) caps += 1;
  }
  return caps > 0 && caps < words;
}

/** Exclamation and question marks raise the intensity of whatever was said. */
function punctuationAmplifier(text: string): number {
  const bangs = Math.min((text.match(/!/g) ?? []).length, 4);
  let amp = bangs * EXCLAMATION_BOOST;

  const marks = Math.min((text.match(/\?/g) ?? []).length, 4);
  if (marks > 1) amp += marks <= 3 ? marks * QUESTION_BOOST_FEW : QUESTION_BOOST_MANY;

  return amp;
}

/**
 * Squash an unbounded sum of valences into -1..1. The curve is deliberately
 * gentle: a review with ten positive words reads as more positive than one with
 * two, but not five times as positive.
 */
function normalize(total: number): number {
  const scaled = total / Math.sqrt(total * total + ALPHA);
  return Math.max(-1, Math.min(1, scaled));
}

function tokenize(text: string): string[] {
  return text.split(/\s+/).filter((token) => token.length > 0);
}

export function labelFor(compound: number): Label {
  if (compound >= POSITIVE_AT) return "positive";
  if (compound <= NEGATIVE_AT) return "negative";
  return "neutral";
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Replace known multi-word phrases with one marker token carrying the phrase
 * valence, so "not worth" is read as a single idea rather than a negated
 * "worth". Longest first, so "would not recommend" wins over "not worth".
 */
function foldPhrases(
  lower: string,
  source: Array<[string, number]>,
): { text: string; phrases: TermHit[] } {
  const phrases: TermHit[] = [];
  let text = lower;

  for (const [phrase, valence] of [...source].sort((a, b) => b[0].length - a[0].length)) {
    if (!text.includes(phrase)) continue;
    const pattern = new RegExp(
      `(?<![\\p{L}\\p{N}])${escapeRegex(phrase)}(?![\\p{L}\\p{N}])`,
      "gu",
    );
    const marker = ` ${PHRASE_MARK}${phrases.length} `;
    let matched = false;
    text = text.replace(pattern, () => {
      matched = true;
      return marker;
    });
    if (matched) phrases.push({ term: phrase, valence, weight: valence });
  }

  return { text, phrases };
}

export interface ScoreOptions {
  /** Collect the words that drove the score. Off in bulk runs, on for one row. */
  explain?: boolean;
  /**
   * Swap the valence lexicon. Defaults to the review lexicon; the CRM tool
   * passes one with sales vocabulary layered on, where "qualified" and
   * "unresponsive" mean something they do not mean in a product review.
   */
  lexicon?: Map<string, number>;
  /** Multi-word phrases to fold, longest first. Defaults to the review set. */
  phrases?: Array<[string, number]>;
}

/** Score one piece of text. */
export function score(text: string, options: ScoreOptions = {}): Scored {
  const trimmed = text.trim();
  if (trimmed.length === 0) {
    return { compound: 0, positive: 0, negative: 0, neutral: 1, label: "neutral", hits: [] };
  }

  const lexicon = options.lexicon ?? reviewLexicon();
  const { text: folded, phrases } = foldPhrases(
    trimmed.toLowerCase(),
    options.phrases ?? reviewPhrases(),
  );

  const tokens = tokenize(folded);
  const original = tokenize(trimmed);
  // Folding changes token counts, so caps are read off the original text only.
  const mixedCaps = hasMixedCaps(original);
  const capsWords = new Set(
    original.filter((token) => isCaps(token)).map((token) => stripPunct(token).toLowerCase()),
  );

  const valences: Valence[] = [];

  for (let i = 0; i < tokens.length; i += 1) {
    const raw = tokens[i];

    if (raw.startsWith(PHRASE_MARK)) {
      const phrase = phrases[Number(raw.slice(1))];
      if (phrase) valences.push({ at: i, value: phrase.valence, hit: phrase });
      continue;
    }

    const word = stripPunct(raw);
    const base = lexicon.get(word);
    if (base === undefined) continue;

    let valence = base;

    // Shouting a word makes it louder, in whichever direction it already points.
    if (mixedCaps && capsWords.has(word)) {
      valence += valence > 0 ? CAPS_BOOST : -CAPS_BOOST;
    }

    // Degree modifiers, fading with distance.
    for (let back = 1; back <= 3 && i - back >= 0; back += 1) {
      const priorRaw = tokens[i - back];
      if (priorRaw.startsWith(PHRASE_MARK)) continue;
      const prior = stripPunct(priorRaw);

      const booster = BOOSTERS[prior];
      if (booster === undefined) continue;

      let delta = booster;
      if (back === 2) delta *= 0.95;
      if (back === 3) delta *= 0.9;
      if (valence < 0) delta = -delta;
      if (mixedCaps && capsWords.has(prior)) {
        delta += valence > 0 ? BOOSTER_INCREMENT : -BOOSTER_INCREMENT;
      }
      valence += delta;
    }

    // Negation within three words flips the sign and softens the magnitude:
    // "not great" is mildly negative, not the opposite of great.
    const negated = negationBefore(tokens, i);
    if (negated) valence *= NEGATION_SCALAR;

    valences.push({
      at: i,
      value: valence,
      hit: { term: negated ? `not ${word}` : word, valence: base, weight: valence },
    });
  }

  applyContrast(tokens, valences);

  let total = valences.reduce((sum, entry) => sum + entry.value, 0);

  if (total !== 0) {
    const amp = punctuationAmplifier(trimmed);
    total += total > 0 ? amp : -amp;
  }

  const compound = normalize(total);

  // Proportions, for the "mostly positive with one complaint" case.
  let pos = 0;
  let neg = 0;
  for (const { value } of valences) {
    if (value > 0) pos += value + 1;
    else if (value < 0) neg += value - 1;
  }

  const wordCount = tokens.filter((token) => token.startsWith(PHRASE_MARK) || isWordy(token)).length;
  const neutralCount = Math.max(0, wordCount - valences.length);
  const magnitude = pos + Math.abs(neg) + neutralCount;

  const hits = options.explain
    ? valences
        .map((entry) => ({ ...entry.hit, weight: entry.value }))
        .sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight))
    : [];

  return {
    compound: Number(compound.toFixed(4)),
    positive: magnitude === 0 ? 0 : Number((pos / magnitude).toFixed(3)),
    negative: magnitude === 0 ? 0 : Number((Math.abs(neg) / magnitude).toFixed(3)),
    neutral: magnitude === 0 ? 1 : Number((neutralCount / magnitude).toFixed(3)),
    label: labelFor(compound),
    hits,
  };
}

/** "never so good" and "at least" are not negations, whatever they look like. */
function negationBefore(tokens: string[], index: number): boolean {
  for (let back = 1; back <= 3 && index - back >= 0; back += 1) {
    const prior = stripPunct(tokens[index - back]).toLowerCase();

    if (prior === "least") {
      const before = index - back - 1 >= 0 ? stripPunct(tokens[index - back - 1]) : "";
      if (before !== "at" && before !== "very") return true;
      continue;
    }

    if (prior === "never") {
      const next = index - back + 1 < tokens.length ? stripPunct(tokens[index - back + 1]) : "";
      if (next === "so" || next === "this") continue;
      return true;
    }

    if (NEGATIONS.has(prior) || prior.endsWith("n't")) return true;
  }
  return false;
}

/**
 * "The room was lovely but the service was appalling." Everything before the
 * "but" is discounted and everything after amplified, because that is how the
 * sentence is meant to be read.
 */
function applyContrast(tokens: string[], valences: Valence[]): void {
  const pivot = tokens.findIndex((token) =>
    CONTRAST_WORDS.has(stripPunct(token).toLowerCase()),
  );
  if (pivot === -1) return;

  for (const entry of valences) {
    entry.value *= entry.at < pivot ? 0.5 : 1.5;
  }
}
