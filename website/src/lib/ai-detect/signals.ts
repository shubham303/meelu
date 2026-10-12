import type { Signal, SignalSpan } from "./types";
import { countWords, sentenceSpans, type SentenceSpan } from "./chunk";

/**
 * Surface statistics about the writing. These are DESCRIPTIVE ONLY — none of them feed
 * the score, and none of them prove anything on their own. They are here because a bare
 * percentage tells you nothing about why, and a reader deserves something they can check
 * against the text in front of them.
 *
 * Every signal now carries the passages that made it count. A total on its own ("twenty
 * sentences start with 'the'") is not checkable: you cannot argue with it, and you cannot
 * edit it. The sentence itself is both. What a span says is "this is what was counted" —
 * not "this sentence was written by a machine", which is a claim no surface count can
 * support for a single sentence.
 */

/** Openers that machine-written prose leans on far harder than people do. */
const CONNECTIVES = [
  "furthermore",
  "moreover",
  "additionally",
  "consequently",
  "nevertheless",
  "nonetheless",
  "in conclusion",
  "in summary",
  "overall",
  "importantly",
  "notably",
  "ultimately",
  "however",
  "therefore",
  "thus",
  "in today's",
  "it is important to note",
  "it is worth noting",
  "play a crucial role",
  "plays a vital role",
  "a wide range of",
  "a testament to",
  "delve into",
  "navigate the",
  "landscape",
  "realm",
  "harness",
  "leverage",
  "robust",
  "seamless",
  "holistic",
  "multifaceted",
  "underscore",
];

const CONNECTIVE_PATTERNS = CONNECTIVES.map((phrase) => ({
  phrase,
  re: new RegExp(`\\b${phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "g"),
}));

/** Enough passages to see the pattern, few enough that the card stays readable. */
const MAX_SPANS = 12;

function toSpan(sentence: SentenceSpan, detail: string): SignalSpan {
  return {
    index: sentence.index,
    start: sentence.start,
    end: sentence.end,
    text: sentence.text,
    detail,
  };
}

/** Deduplicates while keeping first-seen order, so a detail reads the way the text does. */
function unique(values: string[]): string[] {
  return [...new Set(values)];
}

function quoted(values: string[], limit = 4): string {
  const shown = values.slice(0, limit).map((v) => `“${v}”`);
  const extra = values.length - shown.length;
  return extra > 0 ? `${shown.join(", ")} +${extra} more` : shown.join(", ");
}

export function surfaceSignals(text: string): Signal[] {
  const out: Signal[] = [];
  const sents = sentenceSpans(text).filter((s) => s.words > 0);
  const words = countWords(text);
  if (words === 0 || sents.length === 0) return out;

  // 1. Sentence-length variation. People write in bursts; models even out.
  const lengths = sents.map((s) => s.words);
  const mean = lengths.reduce((a, b) => a + b, 0) / lengths.length;
  const sd = Math.sqrt(
    lengths.reduce((acc, n) => acc + (n - mean) ** 2, 0) / lengths.length,
  );
  const burstiness = mean > 0 ? sd / mean : 0;
  const even = burstiness < 0.35;

  // The measure is about the spread, so the passages that show it are the two ends of
  // the range plus, when the text is unusually even, the sentences sitting on the mean.
  const byLength = [...sents].sort((a, b) => a.words - b.words);
  const shortest = byLength[0];
  const longest = byLength[byLength.length - 1];
  const lengthSpans: SignalSpan[] = [];
  if (sents.length >= 2 && shortest.index !== longest.index) {
    lengthSpans.push(toSpan(longest, `longest — ${longest.words} words`));
    lengthSpans.push(toSpan(shortest, `shortest — ${shortest.words} words`));
  }
  const nearMean = even
    ? sents
        .filter((s) => Math.abs(s.words - mean) <= Math.max(2, sd))
        .filter((s) => s.index !== shortest.index && s.index !== longest.index)
    : [];
  for (const sentence of nearMean.slice(0, MAX_SPANS - lengthSpans.length)) {
    lengthSpans.push(toSpan(sentence, `${sentence.words} words — on the average`));
  }

  out.push({
    id: "length-variation",
    label: "Sentence length variation",
    value: `${Math.round(mean)} words avg, ±${Math.round(sd)}`,
    note: even
      ? "Sentences are unusually even in length. Human drafts normally swing more than this."
      : "Sentence lengths swing about as much as a human draft usually does.",
    leaning: even ? "ai" : "human",
    trigger:
      sents.length < 2
        ? "There is only one sentence, so there is no spread to show."
        : even
          ? `The two ends of the range, then every sentence sitting within ${Math.max(2, Math.round(sd))} words of the ${Math.round(mean)}-word average — the cluster that makes the spread small.`
          : "The longest and the shortest sentence, which is the range this number describes.",
    spans: lengthSpans,
    totalSpans: lengthSpans.length + (even ? Math.max(0, nearMean.length - (MAX_SPANS - 2)) : 0),
  });

  // 2. Stock connectives and the vocabulary chat models over-reach for.
  let connectiveHits = 0;
  const connectiveSpans: SignalSpan[] = [];
  let connectiveSentences = 0;
  for (const sentence of sents) {
    const lower = sentence.text.toLowerCase();
    const found: string[] = [];
    for (const { phrase, re } of CONNECTIVE_PATTERNS) {
      re.lastIndex = 0;
      const matches = lower.match(re);
      if (matches) {
        connectiveHits += matches.length;
        found.push(...matches.map(() => phrase));
      }
    }
    if (found.length === 0) continue;
    connectiveSentences += 1;
    if (connectiveSpans.length < MAX_SPANS) {
      connectiveSpans.push(toSpan(sentence, quoted(unique(found))));
    }
  }
  const per100 = (connectiveHits / words) * 100;
  out.push({
    id: "stock-phrases",
    label: "Stock transitions and filler",
    value: `${connectiveHits} in ${words} words`,
    note:
      per100 >= 1.2
        ? "Heavy use of the connectives and adjectives chat models reach for by default."
        : "Not leaning on the phrases chat models default to.",
    leaning: per100 >= 1.2 ? "ai" : "human",
    trigger:
      connectiveSentences === 0
        ? "Nothing triggered: none of the phrases on the list appear in this text."
        : `The ${connectiveSentences === 1 ? "sentence" : `${connectiveSentences} sentences`} containing one of the listed phrases. Each is a normal English word or two — the list is about how often they turn up together, not about any one of them.`,
    spans: connectiveSpans,
    totalSpans: connectiveSentences,
  });

  // 3. Repeated sentence openers — the give-away of a model working through a list.
  const openerOf = (sentence: SentenceSpan) =>
    sentence.text.split(/\s+/)[0]?.toLowerCase().replace(/[^\p{L}]/gu, "") ?? "";
  const openers = new Map<string, number>();
  for (const sentence of sents) {
    const first = openerOf(sentence);
    if (first && first.length > 2) openers.set(first, (openers.get(first) ?? 0) + 1);
  }
  const worst = [...openers.entries()].sort((a, b) => b[1] - a[1])[0];
  const repeatShare = worst ? worst[1] / sents.length : 0;
  const repeated = worst && worst[1] > 1;
  const openerMatches = repeated ? sents.filter((s) => openerOf(s) === worst[0]) : [];
  out.push({
    id: "repeated-openers",
    label: "Repeated sentence openers",
    value: repeated ? `“${worst[0]}” starts ${worst[1]} sentences` : "none repeated",
    note:
      repeatShare >= 0.25 && sents.length >= 4
        ? "The same opener keeps coming back, which is what a model doing a list looks like."
        : "Openers are varied.",
    leaning: repeatShare >= 0.25 && sents.length >= 4 ? "ai" : "human",
    trigger: repeated
      ? `Every sentence that opens with “${worst[0]}”, out of ${sents.length} sentences in total. These are the ones counted — repeating an opener is a habit, not a tell.`
      : "Nothing triggered: no opening word is used twice.",
    spans: openerMatches
      .slice(0, MAX_SPANS)
      .map((sentence) => toSpan(sentence, `opens with “${worst![0]}”`)),
    totalSpans: openerMatches.length,
  });

  // 4. Contractions and first person — usually stripped out of generated prose.
  const contractionRe = /\b[\p{L}]+['’](?:s|t|re|ve|ll|d|m)\b/giu;
  const firstPersonRe = /\b(?:i|i['’]m|i['’]ve|my|we|our|us)\b/gi;
  let contractions = 0;
  let firstPerson = 0;
  const voiceSpans: SignalSpan[] = [];
  let voiceSentences = 0;
  for (const sentence of sents) {
    const lower = sentence.text.toLowerCase();
    const cs = lower.match(contractionRe) ?? [];
    const fp = lower.match(firstPersonRe) ?? [];
    contractions += cs.length;
    firstPerson += fp.length;
    if (cs.length + fp.length === 0) continue;
    voiceSentences += 1;
    if (voiceSpans.length < MAX_SPANS) {
      voiceSpans.push(toSpan(sentence, quoted(unique([...cs, ...fp]))));
    }
  }
  const personal = contractions + firstPerson;
  out.push({
    id: "voice",
    label: "Contractions and first person",
    value: `${contractions} contraction${contractions === 1 ? "" : "s"}, ${firstPerson} personal pronoun${firstPerson === 1 ? "" : "s"}`,
    note:
      personal === 0
        ? "No contractions and nobody in the room. Common in generated copy — and in formal human writing too."
        : "Written in a voice, which generated copy usually is not.",
    leaning: personal === 0 ? "ai" : "human",
    trigger:
      personal === 0
        ? "Nothing triggered: there is no contraction and no first-person pronoun anywhere in the text, so there is no passage to show. Plenty of house styles ban both."
        : `The ${voiceSentences === 1 ? "sentence" : `${voiceSentences} sentences`} where a contraction or a first-person pronoun appears. This one leans human, so read it as the text arguing in its own favour.`,
    spans: voiceSpans,
    totalSpans: voiceSentences,
  });

  return out;
}
