import type { ApiKey, Note, UserProfile } from "@demo/lib/types";
import { ago, DAY, HOUR } from "../rand";
import { SITE_ID } from "./site";

export const USER = {
  id: "usr_demo",
  email: "maya@ledgerly.app",
  name: "Maya Lindqvist",
  image: null,
};

export const PROFILE: UserProfile = {
  id: "usr_demo",
  createdAt: ago(41 * DAY),
  updatedAt: ago(6 * DAY),
  fullName: "Maya Lindqvist",
  role: "Co-founder, marketing",
  company: "Ledgerly",
  timezone: "America/Los_Angeles",
  signature: "Maya\nCo-founder, Ledgerly\nledgerly.app",
  bio: "I run marketing and half of support at Ledgerly. Before this I was a freelance designer for nine years, which is why the product exists.",
  writingVoice:
    "Plain, a little dry, first person. Short sentences. Specific numbers over adjectives. Never 'excited to announce'. Admit the tradeoff before someone else points it out.",
  linkedinUrl: "https://www.linkedin.com/in/mayalindqvist",
  xUrl: "https://x.com/mayalindqvist",
  websiteUrl: "https://ledgerly.app",
};

export const NOTES: Note[] = [
  { id: "nt_1", createdAt: ago(30 * DAY), updatedAt: ago(30 * DAY), siteId: SITE_ID, kind: "note", note: "We never say 'accounting software'. We say 'bookkeeping' — accounting is what the accountant does with our export." },
  { id: "nt_2", createdAt: ago(25 * DAY), updatedAt: ago(25 * DAY), siteId: SITE_ID, kind: "note", note: "Prices are always written as $12 / $29 / $59 a month, never 'from $12'. There is no annual discount and we do not pretend there is." },
  { id: "nt_3", createdAt: ago(18 * DAY), updatedAt: ago(18 * DAY), siteId: SITE_ID, kind: "feedback", note: "The draft for the quarterly tax page opened with a question. Don't — it reads as filler. Open with the deadline dates." },
  { id: "nt_4", createdAt: ago(14 * DAY), updatedAt: ago(14 * DAY), siteId: SITE_ID, kind: "note", note: "Competitor pages must stay fair. If QuickBooks does something better (payroll, inventory, multi-entity) the page says so in the first screen." },
  { id: "nt_5", createdAt: ago(11 * DAY), updatedAt: ago(11 * DAY), siteId: SITE_ID, kind: "note", note: "We do not target 'free invoice template' keywords. We tried; the traffic never converts and the pages compete with our own help centre." },
  { id: "nt_6", createdAt: ago(9 * DAY), updatedAt: ago(7 * DAY), siteId: SITE_ID, kind: "feedback", note: "Suggested /blog/self-employed-tax-deductions and /help/expense-categories as one pillar. They serve different people — keep them apart." },
  { id: "nt_7", createdAt: ago(6 * DAY), updatedAt: ago(6 * DAY), siteId: SITE_ID, kind: "note", note: "Spelling is US English across the site (organize, color) except the UK VAT pages, which use UK spelling." },
  { id: "nt_8", createdAt: ago(4 * DAY), updatedAt: ago(4 * DAY), siteId: SITE_ID, kind: "feedback", note: "Meta descriptions came back at 170+ characters again. Keep them under 155, and no trailing ellipsis." },
  { id: "nt_9", createdAt: ago(2 * DAY), updatedAt: ago(2 * DAY), siteId: SITE_ID, kind: "note", note: "The mobile app ships in November. Say 'later this year' on the site, nothing more specific." },
];

export const KEYS: ApiKey[] = [
  { id: "key_1", createdAt: ago(40 * DAY), updatedAt: ago(40 * DAY), name: "Maya's MacBook", preview: "emcp_7f3a…4f9c", lastUsedAt: ago(20 * 60_000) },
  { id: "key_2", createdAt: ago(13 * DAY), updatedAt: ago(13 * DAY), name: "Claude Desktop", preview: "emcp_b21e…09d7", lastUsedAt: ago(3 * DAY + 5 * HOUR) },
];
