import type { Analysis, ConfidenceBand, ScoredChunk, Verdict } from "./types";
import {
  AI_AT,
  FLAG_AT,
  HUMAN_AT,
  MAX_CONFIDENCE,
  MIN_CONFIDENCE,
  MIN_WORDS_TO_JUDGE,
} from "./constants";
import { surfaceSignals } from "./signals";

const clamp01 = (n: number) => Math.min(1, Math.max(0, n));

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/**
 * Turn per-window model probabilities into one reading.
 *
 * Two things are deliberately kept apart here. The SCORE is the model's opinion, averaged
 * over the windows and weighted by how much text each one covers. The CONFIDENCE is ours,
 * and it is not the model's softmax — that number saturates at 1.0 on text the model gets
 * wrong, so repeating it would be reporting certainty we do not have. Ours is built from
 * how much text we had, how much the windows agreed with each other, and how far the
 * result sits from the fence, then capped at the measured accuracy of the classifier.
 */
export function analyse(scored: ScoredChunk[], normalisedText: string): Analysis {
  const words = scored.reduce((acc, c) => acc + c.words, 0);
  const percents = scored.map((c) => c.ai * 100);

  const totalWeight = words || 1;
  const score =
    scored.reduce((acc, c) => acc + c.ai * 100 * c.words, 0) / totalWeight;
  const mid = median(percents);

  const mean = percents.reduce((a, b) => a + b, 0) / (percents.length || 1);
  const spread =
    percents.length > 1
      ? Math.sqrt(
          percents.reduce((acc, p) => acc + (p - mean) ** 2, 0) / percents.length,
        )
      : 0;

  const high = scored.filter((c) => c.ai * 100 >= AI_AT);
  const low = scored.filter((c) => c.ai * 100 <= HUMAN_AT);
  const aiWordShare =
    high.reduce((acc, c) => acc + c.words, 0) / (words || 1);

  const verdict = decideVerdict({
    score,
    words,
    hasHigh: high.length > 0,
    hasLow: low.length > 0,
    aiWordShare,
  });

  // --- confidence, three honest ingredients -------------------------------
  // 1. How much text we had. Nothing below the floor, full weight around 600 words.
  const lengthFactor = clamp01((words - MIN_WORDS_TO_JUDGE) / 400);

  // 2. How much the windows agreed. With fewer than three there is no agreement to measure,
  //    so this contributes nothing either way rather than a free full mark.
  let agreementFactor = 0.5;
  if (percents.length >= 3) {
    const side = score >= 50;
    const withMajority = percents.filter((p) => p >= 50 === side).length;
    // A 50/50 split scores 0, unanimity scores 1.
    agreementFactor = clamp01((withMajority / percents.length - 0.5) * 2);
  }

  // 3. How far from the fence. Within a few points of 50 the reading means very little.
  const marginFactor = clamp01(Math.abs(score - 50) / 35);

  const raw =
    0.35 * lengthFactor + 0.35 * agreementFactor + 0.3 * marginFactor;

  let confidence = Math.round(
    MIN_CONFIDENCE + raw * (MAX_CONFIDENCE - MIN_CONFIDENCE),
  );
  // Too little text is too little text, whatever the model says.
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

function decideVerdict({
  score,
  words,
  hasHigh,
  hasLow,
  aiWordShare,
}: {
  score: number;
  words: number;
  hasHigh: boolean;
  hasLow: boolean;
  aiWordShare: number;
}): Verdict {
  if (words < MIN_WORDS_TO_JUDGE) return "too-short";

  // A real split is more useful to report than an average that lands in the middle and
  // describes neither half. Weighted by words, so one stray window in a long document
  // does not turn a clear reading into a shrug.
  if (hasHigh && hasLow && aiWordShare >= 0.2 && aiWordShare <= 0.8) return "mixed";

  if (score >= AI_AT) return "ai";
  if (score <= HUMAN_AT) return "human";
  return "unclear";
}

function bandFor(confidence: number): ConfidenceBand {
  if (confidence <= 50) return "low";
  if (confidence <= 68) return "moderate";
  return "reasonable";
}

export const VERDICT_LABEL: Record<Verdict, string> = {
  ai: "Likely AI-generated",
  human: "Likely human-written",
  mixed: "Mixed — parts read as AI",
  unclear: "Unclear",
  "too-short": "Too short to judge",
};

export const VERDICT_BLURB: Record<Verdict, string> = {
  ai: "The classifier put most of this text on the AI side, and the windows broadly agreed. That is evidence, not proof — read the flagged passages and decide for yourself.",
  human: "The classifier put most of this text on the human side. Worth knowing that lightly edited AI text lands here too, so a human reading is not the same as a human author.",
  mixed: "Some windows read as machine-written and others as human. That pattern shows up in AI drafts a person has rewritten in places, and in human drafts with a generated section pasted in.",
  unclear: "The score landed near the middle, where this classifier is close to guessing. Treat it as no answer rather than a soft yes.",
  "too-short": `Under ${MIN_WORDS_TO_JUDGE} words there is not enough text for a detector of this kind to say anything useful. The number below is shown for completeness — do not act on it.`,
};

export const CONFIDENCE_LABEL: Record<ConfidenceBand, string> = {
  low: "Low confidence",
  moderate: "Moderate confidence",
  reasonable: "Reasonable confidence",
};

/** Colour band for the dial and the chunk table. */
export function toneFor(percent: number): {
  text: string;
  bg: string;
  ring: string;
  border: string;
} {
  if (percent >= AI_AT) {
    return {
      text: "text-bad",
      bg: "bg-bad/10",
      ring: "var(--color-bad)",
      border: "border-bad/25",
    };
  }
  if (percent <= HUMAN_AT) {
    return {
      text: "text-good",
      bg: "bg-good/10",
      ring: "var(--color-good)",
      border: "border-good/25",
    };
  }
  return {
    text: "text-warn",
    bg: "bg-warn/10",
    ring: "var(--color-warn)",
    border: "border-warn/25",
  };
}
