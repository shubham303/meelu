import { plainChips, type PromptChip } from "./lib";

export const ask: PromptChip[] = [
  ...plainChips([
    "What does this data actually contain?",
    "What changed over time, and what's driving it?",
    "Which columns move the outcome the most?",
  ]),
  {
    label: "Build a report and keep it",
    prompt:
      "Build one dashboard from this session's data — KPI cards for the headline numbers first, then the charts that carry the argument — and save it as a report on this session.",
  },
];
