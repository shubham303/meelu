import { plainChips, type PromptChip } from "./lib";

export const ask: PromptChip[] = [
  ...plainChips([
    "Where did clicks change in the last 28 days, and which pages drove it?",
    "Which queries gain impressions but lose clicks?",
    "Forecast organic clicks for the next 8 weeks.",
    "Which landing pages convert best from organic search?",
  ]),
];

export const SAVE_REPORT_PROMPT =
  "Save your last answer as a report: a short title that names the question, the numbers and charts behind it, and where the data came from.";
