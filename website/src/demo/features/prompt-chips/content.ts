import { plainChips, type PromptChip } from "./lib";

export const newPiece: PromptChip[] = plainChips([
  "Write a page explaining one of our services",
  "Write an article answering a question customers ask us often",
  "Write the page one of the SEO suggestions asks for",
]);

export const ask: PromptChip[] = plainChips([
  "Which pieces still have page warnings, and why?",
  "Which pieces have no target keyword yet?",
  "Add better internal links to the latest piece",
]);
