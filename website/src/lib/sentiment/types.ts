import type { ParsedCsv } from "@/lib/csv/parse";

export type { ParsedCsv };

export type Label = "positive" | "negative" | "neutral";

export const LABELS: Label[] = ["positive", "neutral", "negative"];

/** One lexicon word or phrase that moved the score, with its final weight. */
export interface TermHit {
  term: string;
  /** The word's raw valence before negation, boosting and contrast. */
  valence: number;
  /** What it actually contributed once the rules had been applied. */
  weight: number;
}

export interface Scored {
  /** -1 (most negative) to +1 (most positive). */
  compound: number;
  positive: number;
  negative: number;
  neutral: number;
  label: Label;
  hits: TermHit[];
}

export interface AnalyzedRow {
  /** 1-based row number as it appears in the file, so people can find it. */
  line: number;
  text: string;
  scored: Scored;
  /** Normalised to 1-5 where a rating column was found. */
  rating: number | null;
  /** A 4 or 5 star review whose words are negative, or the reverse. */
  mismatch: boolean;
}

export interface TermCount {
  term: string;
  count: number;
  /** Mean weight across its appearances, so ordering reflects force not just frequency. */
  impact: number;
}

export interface RatingBucket {
  rating: number;
  total: number;
  positive: number;
  neutral: number;
  negative: number;
  avgCompound: number;
}

export interface Summary {
  total: number;
  /** Rows that were empty or had nothing scoreable. */
  skipped: number;
  counts: Record<Label, number>;
  share: Record<Label, number>;
  avgCompound: number;
  /** Net promoter-ish: positive share minus negative share, in points. */
  netSentiment: number;
  positiveTerms: TermCount[];
  negativeTerms: TermCount[];
  ratings: RatingBucket[];
  mismatches: AnalyzedRow[];
  hasRatings: boolean;
}

export interface AnalysisResult {
  rows: AnalyzedRow[];
  summary: Summary;
  textColumn: string;
  ratingColumn: string | null;
  parsed: ParsedCsv;
  /** Milliseconds spent scoring, shown because the speed is the selling point. */
  elapsedMs: number;
}
