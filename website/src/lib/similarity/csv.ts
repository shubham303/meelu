import type { SimilarityResult } from "./types";

function cell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function toCsv(headers: string[], rows: unknown[][]): string {
  return [headers, ...rows].map((row) => row.map(cell).join(",")).join("\r\n");
}

const KIND_LABEL = {
  exact: "Exact",
  near: "Near-exact",
  close: "Close",
} as const;

/** One row per matched sentence pair, highest score first. */
export function matchesCsv(result: SimilarityResult): string {
  const a = new Map(result.a.sentences.map((s) => [s.index, s]));
  const b = new Map(result.b.sentences.map((s) => [s.index, s]));
  return toCsv(
    [
      "Match type",
      "Score %",
      "TF-IDF cosine %",
      "Word overlap %",
      "Sentence in A",
      "Words in A",
      "Sentence in B",
      "Words in B",
    ],
    result.matches.map((match) => {
      const left = a.get(match.a);
      const right = b.get(match.b);
      return [
        KIND_LABEL[match.kind],
        match.score,
        match.cosine,
        match.overlap,
        left?.text ?? "",
        left?.words ?? 0,
        right?.text ?? "",
        right?.words ?? 0,
      ];
    }),
  );
}

export function fileStem(result: SimilarityResult): string {
  const date = new Date().toISOString().slice(0, 10);
  return `similarity-${result.overall}pc-${date}`;
}
