import { plainChips, type PromptChip } from "./lib";

export const newPiece: PromptChip[] = plainChips([
  "Write a page for the website explaining one of our services",
  "Write a LinkedIn post about something we shipped this week",
  "Write an article answering a question customers ask us often",
]);

export const ask: PromptChip[] = plainChips([
  "Which channels have nothing scheduled this week?",
  "Where are the gaps in the next two weeks?",
  "How many posts went out per channel this month?",
  "Which drafts have a slot but never went out?",
]);

export const channelRules: PromptChip[] = plainChips([
  "Show me the current rules",
  "Make the voice more casual",
  "Reset to the shipped default",
]);
