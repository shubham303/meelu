import type { AnalysisResult } from "./types";

import { DEFAULT_MAX_ROWS, parseCsv, toCsv } from "@/lib/csv/parse";
import type { ParsedCsv } from "@/lib/csv/parse";

/** Rows read from one review file. */
export const MAX_ROWS = DEFAULT_MAX_ROWS;

export { parseCsv };


const TEXT_HINTS = [
  "review",
  "review_text",
  "reviewtext",
  "review body",
  "body",
  "comment",
  "comments",
  "feedback",
  "text",
  "content",
  "message",
  "description",
  "opinion",
  "response",
  "answer",
  "verbatim",
  "note",
  "notes",
  "testimonial",
];

const RATING_HINTS = [
  "rating",
  "stars",
  "star",
  "score",
  "rate",
  "overall",
  "nps",
  "grade",
];

const NOT_TEXT = ["id", "date", "time", "url", "name", "email", "author", "user", "title"];

function normalizeHeader(header: string): string {
  return header.toLowerCase().replace(/[\s_-]+/g, " ").trim();
}

/**
 * Work out which column holds the review. Header names first, and if they are
 * unhelpful — plenty of exports ship "Column 3" — fall back to whichever column
 * holds the most prose, measured by average word count.
 */
export function detectTextColumn(parsed: ParsedCsv): number {
  const { headers, rows } = parsed;

  for (let i = 0; i < headers.length; i += 1) {
    const name = normalizeHeader(headers[i]);
    if (TEXT_HINTS.includes(name)) return i;
  }
  for (let i = 0; i < headers.length; i += 1) {
    const name = normalizeHeader(headers[i]);
    if (NOT_TEXT.some((bad) => name === bad)) continue;
    if (TEXT_HINTS.some((hint) => name.includes(hint))) return i;
  }

  const sample = rows.slice(0, 200);
  let best = 0;
  let bestWords = -1;
  for (let i = 0; i < headers.length; i += 1) {
    let words = 0;
    for (const dataRow of sample) {
      const cell = dataRow[i] ?? "";
      words += cell.trim().split(/\s+/).filter(Boolean).length;
    }
    const avg = sample.length === 0 ? 0 : words / sample.length;
    if (avg > bestWords) {
      bestWords = avg;
      best = i;
    }
  }
  return best;
}

/** Find a 1-5 or 1-10 rating column, if the export has one. */
export function detectRatingColumn(parsed: ParsedCsv, textColumn: number): number | null {
  const { headers, rows } = parsed;
  const sample = rows.slice(0, 200);

  const numericAndInRange = (index: number): boolean => {
    let numeric = 0;
    let seen = 0;
    for (const dataRow of sample) {
      const raw = (dataRow[index] ?? "").trim();
      if (raw === "") continue;
      seen += 1;
      const value = Number(raw.replace(/[^\d.]/g, ""));
      if (Number.isFinite(value) && value >= 0 && value <= 10) numeric += 1;
    }
    return seen > 0 && numeric / seen > 0.9;
  };

  for (let i = 0; i < headers.length; i += 1) {
    if (i === textColumn) continue;
    const name = normalizeHeader(headers[i]);
    if (RATING_HINTS.some((hint) => name === hint || name.includes(hint))) {
      if (numericAndInRange(i)) return i;
    }
  }
  return null;
}

/** Ratings out of 10 are squashed to the 1-5 scale so the buckets line up. */
export function normalizeRating(raw: string): number | null {
  const cleaned = raw.trim().replace(/[^\d.]/g, "");
  if (cleaned === "") return null;
  const value = Number(cleaned);
  if (!Number.isFinite(value) || value <= 0) return null;
  const scaled = value > 5 ? value / 2 : value;
  return Math.max(1, Math.min(5, Math.round(scaled)));
}


/** Every row with its label and score, ready to sort and filter in a spreadsheet. */
export function rowsCsv(result: AnalysisResult): string {
  const headers = ["Row", "Sentiment", "Score", "Positive", "Neutral", "Negative"];
  if (result.ratingColumn) headers.push("Rating", "Rating mismatch");
  headers.push("Top terms", "Review");

  return toCsv(
    headers,
    result.rows.map((row) => {
      const base: unknown[] = [
        row.line,
        row.scored.label,
        row.scored.compound,
        row.scored.positive,
        row.scored.neutral,
        row.scored.negative,
      ];
      if (result.ratingColumn) base.push(row.rating ?? "", row.mismatch ? "yes" : "");
      base.push(
        row.scored.hits
          .slice(0, 5)
          .map((hit) => hit.term)
          .join("; "),
        row.text,
      );
      return base;
    }),
  );
}

/** The counts, shares and driving terms — the thing you paste into a deck. */
export function summaryCsv(result: AnalysisResult): string {
  const { summary } = result;
  const rows: unknown[][] = [
    ["Reviews analysed", summary.total],
    ["Positive", summary.counts.positive, `${summary.share.positive}%`],
    ["Neutral", summary.counts.neutral, `${summary.share.neutral}%`],
    ["Negative", summary.counts.negative, `${summary.share.negative}%`],
    ["Net sentiment", `${summary.netSentiment} points`],
    ["Average score", summary.avgCompound],
    ["Rows skipped as empty", summary.skipped],
    [],
    ["Top positive terms", "Mentions"],
    ...summary.positiveTerms.map((term) => [term.term, term.count]),
    [],
    ["Top negative terms", "Mentions"],
    ...summary.negativeTerms.map((term) => [term.term, term.count]),
  ];

  if (summary.hasRatings) {
    rows.push(
      [],
      ["Rating", "Reviews", "Positive", "Neutral", "Negative", "Average score"],
      ...summary.ratings.map((bucket) => [
        `${bucket.rating} star`,
        bucket.total,
        bucket.positive,
        bucket.neutral,
        bucket.negative,
        bucket.avgCompound,
      ]),
    );
  }

  return toCsv(["Measure", "Value", "Share"], rows);
}

export function fileStem(name: string): string {
  const base = name.replace(/\.[^.]+$/, "").replace(/[^a-z0-9]+/gi, "-").toLowerCase();
  return `sentiment-${base || "reviews"}`;
}
