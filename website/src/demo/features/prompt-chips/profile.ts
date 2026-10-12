import type { PromptChip } from "./lib";

export const setup: PromptChip[] = [
  {
    label: "Set up my profile",
    prompt: [
      "Set up my profile from scratch.",
      "Read whatever is already stored in my profile, then interview me one question at a time — who I am, what I do, who I write for.",
      "Save it all in a single save_profile call once I have confirmed it, say in one sentence what you saved, and stop there.",
    ].join(" "),
  },
  {
    label: "Set my sign-off",
    prompt: [
      "I want to set the sign-off that ends anything written as me.",
      "Ask me for the exact lines — name, role, whatever follows — and read the block back so I can see the line breaks.",
      "Once I say yes, save only the sign-off with one save_profile call; it merges, so leave my other fields as they are.",
    ].join(" "),
  },
  {
    label: "Describe how I want to sound",
    prompt: [
      "I want to describe my writing voice.",
      "Ask what I sound like at my best and what I never want to sound like — tone, sentence length, words to avoid — then turn my answers into a short description I would recognise as me.",
      "Save only the voice with one save_profile call after I approve the wording, then stop.",
    ].join(" "),
  },
  {
    label: "Read back what you have",
    prompt: [
      "Read back the profile you already hold for me, field by field, as it is stored — the sign-off as a block so I can see the line breaks.",
      "Say plainly which fields are still empty.",
      "Write nothing unless I ask you to change something.",
    ].join(" "),
  },
];
