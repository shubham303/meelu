import type { UserPrompt } from "@demo/features/user-prompts/api";
import { ago, DAY, HOUR } from "../rand";
import { SITE_ID } from "./site";

export const USER_PROMPTS: UserPrompt[] = [
  {
    id: "up_1",
    siteId: SITE_ID,
    surface: "seo",
    label: "Competitor pages vs QuickBooks",
    prompt: [
      "Look at the queries where a QuickBooks, FreshBooks or Wave comparison page ranks and ours does not.",
      "For each, say which of our pages is closest to the intent and whether it needs a new section or a page of its own.",
      "Keep it fair: if the competitor is better at something, say so.",
    ].join("\n"),
    createdAt: ago(19 * DAY),
    updatedAt: ago(19 * DAY),
  },
  {
    id: "up_2",
    siteId: SITE_ID,
    surface: "seo",
    label: "Tax season check-in",
    prompt: [
      "It is close to quarterly estimated tax deadlines. Read Search Console for the last 28 days against the 28 before.",
      "Which tax and invoicing queries are rising, and which of our pages catch them? Name any rising query we have no page for.",
    ].join("\n"),
    createdAt: ago(8 * DAY),
    updatedAt: ago(3 * DAY + 4 * HOUR),
  },
  {
    id: "up_3",
    siteId: SITE_ID,
    surface: "structure",
    label: "Help centre → pricing links",
    prompt: [
      "Find help centre articles that answer a question a buyer asks before paying (exports, multi-currency, receipts) but never link to /pricing.",
      "Suggest one link per article, with the sentence it would sit in.",
    ].join("\n"),
    createdAt: ago(12 * DAY),
    updatedAt: ago(12 * DAY),
  },
  {
    id: "up_4",
    siteId: SITE_ID,
    surface: "structure",
    label: "Orphaned blog posts",
    prompt: "List blog posts with fewer than two internal links pointing at them and suggest the best existing page to link from for each.",
    createdAt: ago(5 * DAY),
    updatedAt: ago(5 * DAY),
  },
];
