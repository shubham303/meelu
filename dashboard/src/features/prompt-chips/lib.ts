export interface PromptChip {
  label: string;
  prompt: string;
  blurb?: string;
}

export function plainChips(labels: string[]): PromptChip[] {
  return labels.map((label) => ({ label, prompt: label }));
}
