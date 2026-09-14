import { plainChips, type PromptChip } from "./lib";

export function project(prospectsWithoutADraft: number): PromptChip[] {
  return plainChips([
    ...(prospectsWithoutADraft > 0 ? [`Draft the emails (${prospectsWithoutADraft})`] : []),
    "How is this project doing?",
    "Who's worth a follow-up right now?",
    "Delete the prospects with no email address",
    "Tighten the brief",
  ]);
}

export const projectEdit: PromptChip[] = plainChips([
  "Tighten the prospect profile",
  "Make the tone more casual",
  "Rewrite the prompt so a campaign can execute it",
]);

export const prospectEdit: PromptChip[] = plainChips([
  "They replied — set status and note what they said",
  "Fix their contact details",
  "Rewrite the fit reason",
  "This one was a bad fit — remove them",
]);
