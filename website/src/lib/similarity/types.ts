export type MatchKind = "exact" | "near" | "close";

export type Band = "original" | "partial" | "high";

export type SentenceRef = {
  index: number;
  text: string;
  /** Offsets into that side's text, so the passage can be highlighted in place. */
  start: number;
  end: number;
  words: number;
  /** False for fragments too short to judge — headings, list stubs, "Yes." */
  eligible: boolean;
};

export type SentenceMatch = {
  a: number;
  b: number;
  /** 0-100, the blended score the threshold is applied to. */
  score: number;
  /** 0-100, TF-IDF cosine on its own. */
  cosine: number;
  /** 0-100, share of content words in common. */
  overlap: number;
  kind: MatchKind;
};

export type SharedPassage = {
  text: string;
  words: number;
  aStart: number;
  aEnd: number;
  bStart: number;
  bEnd: number;
  /** Sentence each end of the passage starts in, for click-to-scroll. */
  aSentence: number;
  bSentence: number;
};

export type SideReport = {
  label: "A" | "B";
  chars: number;
  words: number;
  sentenceCount: number;
  sentences: SentenceRef[];
  /** Share of this side's words that sit in a sentence matched on the other. */
  coverage: number;
  /** Share of this side's five-word windows that appear verbatim on the other. */
  verbatim: number;
  /** The headline containment for this direction: the higher of the two above. */
  containment: number;
  matchedWords: number;
  judgedWords: number;
  unique: number[];
  truncated: boolean;
  /** The text the offsets above point into: line endings normalised, capped. */
  text: string;
};

export type SimilarityResult = {
  overall: number;
  band: Band;
  verdict: string;
  advice: string;
  a: SideReport;
  b: SideReport;
  /** Best partner in B for every sentence in A, highest score first. */
  matches: SentenceMatch[];
  /** The same pass run the other way, which is what B's containment is built on. */
  reverse: SentenceMatch[];
  passages: SharedPassage[];
  longestPassageWords: number;
  exactSentences: number;
  nearSentences: number;
  durationMs: number;
};
