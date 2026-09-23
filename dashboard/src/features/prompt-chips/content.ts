import { plainChips, type PromptChip } from "./lib";

export const newPiece: PromptChip[] = plainChips([
  "Write a page for the website explaining one of our services",
  "Write a LinkedIn post about something we shipped this week",
  "Write an article answering a question customers ask us often",
]);

export const ask: PromptChip[] = plainChips([
  "Which channels have no drafts yet?",
  "Which pieces are blocked, and why?",
  "How many pieces did we write per channel this month?",
  "Rewrite the latest LinkedIn draft for X",
]);

export const channelRules: PromptChip[] = plainChips([
  "Show me the current rules",
  "Make the voice more casual",
  "Reset to the shipped default",
]);
