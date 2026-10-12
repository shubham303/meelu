import { plainChips, type PromptChip } from "./lib";

export const newPiece: PromptChip[] = plainChips([
  "Write a page for the website explaining one of our services",
  "Write a landing page for our main product",
  "Write an article answering a question customers ask us often",
]);

export const ask: PromptChip[] = plainChips([
  "Which pages are blocked, and why?",
  "Which drafts still have open issues?",
  "Suggest internal links for the latest draft",
]);

export const channelRules: PromptChip[] = plainChips([
  "Show me the current rules",
  "Make the voice more casual",
  "Reset to the shipped default",
]);
