export {
  compare,
  bandFor,
  MATCH_THRESHOLD,
  MIN_PASSAGE_WORDS,
  MIN_SENTENCE_WORDS,
  NEAR_THRESHOLD,
  SHINGLE_K,
  VERDICTS,
} from "./compare.js";
export { DEFAULT_MAX_WORDS, countWords, limitWords } from "./limits.js";
export {
  contentTokens,
  hash,
  intersectionSize,
  normalise,
  segments,
  shingles,
  splitSentences,
  tokenise,
} from "./text.js";
