import { detectRatingColumn, detectTextColumn, normalizeRating, parseCsv } from "./csv";
import { score } from "./score";
import type {
  AnalysisResult,
  AnalyzedRow,
  Label,
  ParsedCsv,
  RatingBucket,
  Summary,
  TermCount,
} from "./types";

/** Terms this common carry no signal worth reporting even when they score. */
const BORING_TERMS = new Set(["ok", "okay", "yes", "no", "please", "thanks", "thank"]);

export interface AnalyzeOptions {
  /** Override the sniffed text column when the guess is wrong. */
  textColumn?: number;
  /** Override the rating column, or pass null to ignore ratings entirely. */
  ratingColumn?: number | null;
  /** Called with progress between 0 and 1 so a big file can show a bar. */
  onProgress?: (fraction: number) => void;
}

function emptySummary(): Summary {
  return {
    total: 0,
    skipped: 0,
    counts: { positive: 0, neutral: 0, negative: 0 },
    share: { positive: 0, neutral: 0, negative: 0 },
    avgCompound: 0,
    netSentiment: 0,
    positiveTerms: [],
    negativeTerms: [],
    ratings: [],
    mismatches: [],
    hasRatings: false,
  };
}

function topTerms(counts: Map<string, { count: number; total: number }>, limit: number): TermCount[] {
  return [...counts.entries()]
    .filter(([term]) => !BORING_TERMS.has(term))
    .map(([term, stat]) => ({
      term,
      count: stat.count,
      impact: Number((stat.total / stat.count).toFixed(2)),
    }))
    .sort((a, b) => b.count - a.count || Math.abs(b.impact) - Math.abs(a.impact))
    .slice(0, limit);
}

/**
 * Score every row of an already-parsed CSV.
 *
 * `explain` is on for every row because the terms behind a score are what make
 * the result actionable — "negative" tells you nothing, "negative, driven by
 * 'delayed' and 'refund' across 340 reviews" tells you what to go and fix.
 */
export function analyzeParsed(
  parsed: ParsedCsv,
  options: AnalyzeOptions = {},
): Omit<AnalysisResult, "parsed" | "elapsedMs"> {
  const textColumn = options.textColumn ?? detectTextColumn(parsed);
  const ratingColumn =
    options.ratingColumn === undefined
      ? detectRatingColumn(parsed, textColumn)
      : options.ratingColumn;

  const rows: AnalyzedRow[] = [];
  const summary = emptySummary();
  const positiveCounts = new Map<string, { count: number; total: number }>();
  const negativeCounts = new Map<string, { count: number; total: number }>();
  const ratingBuckets = new Map<number, RatingBucket>();

  let compoundTotal = 0;
  const step = Math.max(1, Math.floor(parsed.rows.length / 100));

  for (let i = 0; i < parsed.rows.length; i += 1) {
    const dataRow = parsed.rows[i];
    const text = (dataRow[textColumn] ?? "").trim();

    if (options.onProgress && i % step === 0) options.onProgress(i / parsed.rows.length);

    if (text === "") {
      summary.skipped += 1;
      continue;
    }

    const scored = score(text, { explain: true });
    const rating =
      ratingColumn === null || ratingColumn === undefined
        ? null
        : normalizeRating(dataRow[ratingColumn] ?? "");

    // A five-star review that reads as a complaint is usually a mis-click, a
    // sarcastic reviewer, or a support case someone closed too early. Either
    // way it is the most interesting row in the file.
    const mismatch =
      rating !== null &&
      ((rating >= 4 && scored.label === "negative") || (rating <= 2 && scored.label === "positive"));

    const row: AnalyzedRow = { line: i + 2, text, scored, rating, mismatch };
    rows.push(row);

    summary.total += 1;
    summary.counts[scored.label] += 1;
    compoundTotal += scored.compound;

    for (const hit of scored.hits) {
      const target = hit.weight > 0 ? positiveCounts : negativeCounts;
      const existing = target.get(hit.term);
      if (existing) {
        existing.count += 1;
        existing.total += hit.weight;
      } else {
        target.set(hit.term, { count: 1, total: hit.weight });
      }
    }

    if (rating !== null) {
      const bucket = ratingBuckets.get(rating) ?? {
        rating,
        total: 0,
        positive: 0,
        neutral: 0,
        negative: 0,
        avgCompound: 0,
      };
      bucket.total += 1;
      bucket[scored.label] += 1;
      bucket.avgCompound += scored.compound;
      ratingBuckets.set(rating, bucket);
    }

    if (mismatch) summary.mismatches.push(row);
  }

  const total = summary.total || 1;
  for (const label of ["positive", "neutral", "negative"] as Label[]) {
    summary.share[label] = Number(((summary.counts[label] / total) * 100).toFixed(1));
  }
  summary.avgCompound = Number((compoundTotal / total).toFixed(4));
  summary.netSentiment = Number((summary.share.positive - summary.share.negative).toFixed(1));
  summary.positiveTerms = topTerms(positiveCounts, 20);
  summary.negativeTerms = topTerms(negativeCounts, 20);
  summary.hasRatings = ratingBuckets.size > 0;
  summary.ratings = [...ratingBuckets.values()]
    .map((bucket) => ({
      ...bucket,
      avgCompound: Number((bucket.avgCompound / bucket.total).toFixed(4)),
    }))
    .sort((a, b) => b.rating - a.rating);

  // Worst first: the point of the list is triage.
  summary.mismatches.sort((a, b) => a.scored.compound - b.scored.compound);
  summary.mismatches = summary.mismatches.slice(0, 50);

  options.onProgress?.(1);

  return {
    rows,
    summary,
    textColumn: parsed.headers[textColumn] ?? `Column ${textColumn + 1}`,
    ratingColumn:
      ratingColumn === null || ratingColumn === undefined
        ? null
        : (parsed.headers[ratingColumn] ?? `Column ${ratingColumn + 1}`),
  };
}

/** Parse and score a CSV file's contents in one go. */
export function analyzeCsv(input: string, options: AnalyzeOptions = {}): AnalysisResult {
  const started = performance.now();
  const parsed = parseCsv(input);
  const analysis = analyzeParsed(parsed, options);
  return {
    ...analysis,
    parsed,
    elapsedMs: Math.round(performance.now() - started),
  };
}

/** Score a single pasted review, for the try-it-without-a-file path. */
export function analyzeText(text: string) {
  return score(text, { explain: true });
}
