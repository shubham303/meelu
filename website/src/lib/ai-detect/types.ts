export type Verdict =
  | "ai"
  | "human"
  | "mixed"
  | "unclear"
  | "too-short";

export type ConfidenceBand = "low" | "moderate" | "reasonable";

/** One ~100-word window of the submitted text, with its model score. */
export type Chunk = {
  index: number;
  text: string;
  words: number;
  /** Character offsets into the normalised text, for highlighting. */
  start: number;
  end: number;
};

export type ScoredChunk = Chunk & {
  /** Model probability that this window is AI-generated, 0–1. */
  ai: number;
};

/** One passage that made a surface signal count. Offsets are into the normalised text. */
export type SignalSpan = {
  /** Sentence number in the document, counted from one. */
  index: number;
  start: number;
  end: number;
  text: string;
  /** What in this sentence counted — the phrase matched, the opener, the length. */
  detail: string;
};

/** A transparent surface statistic. Descriptive only — it never feeds the score. */
export type Signal = {
  /** Stable key for the UI, since labels are prose. */
  id: string;
  label: string;
  value: string;
  note: string;
  /** Whether this reading leans the way AI text usually reads. */
  leaning: "ai" | "human" | "neutral";
  /** Plain sentence saying what the passages below have in common. Never an accusation. */
  trigger: string;
  /** The passages that counted, at most a dozen of them. */
  spans: SignalSpan[];
  /** How many passages counted in total, which can exceed spans.length. */
  totalSpans: number;
};

export type Analysis = {
  /** Weighted mean of the chunk scores, 0–100. */
  score: number;
  /** Median chunk score, 0–100 — reported alongside the mean when they disagree. */
  median: number;
  verdict: Verdict;
  /** 35–85. Deliberately capped: see MAX_CONFIDENCE. */
  confidence: number;
  confidenceBand: ConfidenceBand;
  words: number;
  chunks: ScoredChunk[];
  /** Chunks scoring above FLAG_AT, highest first — the passages worth reading again. */
  flagged: ScoredChunk[];
  /** How far apart the chunk scores are, 0–100. High means the text is uneven. */
  spread: number;
  /** The normalised text every offset in `chunks` and `signals` points into. */
  text: string;
  signals: Signal[];
};

export type LoadProgress = {
  /** 0–100 across every file the model needs. */
  percent: number;
  loadedBytes: number;
  totalBytes: number;
  /** What the engine is doing right now, in plain words. */
  message: string;
};
