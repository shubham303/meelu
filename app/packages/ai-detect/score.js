import { AI_AT, FLAG_AT, HUMAN_AT, MAX_CONFIDENCE, MIN_CONFIDENCE, MIN_WORDS_TO_JUDGE } from "./constants.js";
import { surfaceSignals } from "./signals.js";

const clamp01 = (n) => Math.min(1, Math.max(0, n));

function median(values) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function decideVerdict({ score, words, hasHigh, hasLow, aiWordShare }) {
  if (words < MIN_WORDS_TO_JUDGE) return "too-short";
  if (hasHigh && hasLow && aiWordShare >= 0.2 && aiWordShare <= 0.8) return "mixed";
  if (score >= AI_AT) return "ai";
  if (score <= HUMAN_AT) return "human";
  return "unclear";
}

function bandFor(confidence) {
  if (confidence <= 50) return "low";
  if (confidence <= 68) return "moderate";
  return "reasonable";
}

export function analyse(scored, normalisedText) {
  const words = scored.reduce((acc, c) => acc + c.words, 0);
  const percents = scored.map((c) => c.ai * 100);
  const totalWeight = words || 1;
  const score = scored.reduce((acc, c) => acc + c.ai * 100 * c.words, 0) / totalWeight;
  const mid = median(percents);

  const mean = percents.reduce((a, b) => a + b, 0) / (percents.length || 1);
  const spread =
    percents.length > 1
      ? Math.sqrt(percents.reduce((acc, p) => acc + (p - mean) ** 2, 0) / percents.length)
      : 0;

  const high = scored.filter((c) => c.ai * 100 >= AI_AT);
  const low = scored.filter((c) => c.ai * 100 <= HUMAN_AT);
  const aiWordShare = high.reduce((acc, c) => acc + c.words, 0) / (words || 1);

  const verdict = decideVerdict({ score, words, hasHigh: high.length > 0, hasLow: low.length > 0, aiWordShare });

  const lengthFactor = clamp01((words - MIN_WORDS_TO_JUDGE) / 400);
  let agreementFactor = 0.5;
  if (percents.length >= 3) {
    const side = score >= 50;
    const withMajority = percents.filter((p) => p >= 50 === side).length;
    agreementFactor = clamp01((withMajority / percents.length - 0.5) * 2);
  }
  const marginFactor = clamp01(Math.abs(score - 50) / 35);
  const raw = 0.35 * lengthFactor + 0.35 * agreementFactor + 0.3 * marginFactor;

  let confidence = Math.round(MIN_CONFIDENCE + raw * (MAX_CONFIDENCE - MIN_CONFIDENCE));
  if (words < MIN_WORDS_TO_JUDGE) confidence = Math.min(confidence, 45);
  confidence = Math.max(MIN_CONFIDENCE, Math.min(MAX_CONFIDENCE, confidence));

  const flagged = [...scored]
    .filter((c) => c.ai * 100 >= FLAG_AT)
    .sort((a, b) => b.ai - a.ai)
    .slice(0, 5);

  return {
    score: Math.round(score),
    median: Math.round(mid),
    verdict,
    confidence,
    confidenceBand: bandFor(confidence),
    words,
    chunks: scored,
    flagged,
    spread: Math.round(spread),
    text: normalisedText,
    signals: surfaceSignals(normalisedText),
  };
}

export const VERDICT_LABEL = {
  ai: "Likely AI-generated",
  human: "Likely human-written",
  mixed: "Mixed — parts read as AI",
  unclear: "Unclear",
  "too-short": "Too short to judge",
};

export const VERDICT_BLURB = {
  ai: "The classifier put most of this text on the AI side, and the windows broadly agreed. That is evidence, not proof — read the flagged passages and decide for yourself.",
  human: "The classifier put most of this text on the human side. Worth knowing that lightly edited AI text lands here too, so a human reading is not the same as a human author.",
  mixed: "Some windows read as machine-written and others as human. That pattern shows up in AI drafts a person has rewritten in places, and in human drafts with a generated section pasted in.",
  unclear: "The score landed near the middle, where this classifier is close to guessing. Treat it as no answer rather than a soft yes.",
  "too-short": `Under ${MIN_WORDS_TO_JUDGE} words there is not enough text for a detector of this kind to say anything useful.`,
};

export const CONFIDENCE_LABEL = {
  low: "Low confidence",
  moderate: "Moderate confidence",
  reasonable: "Reasonable confidence",
};
