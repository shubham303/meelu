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
  { id: "nt_3", createdAt: ago(18 * DAY), updatedAt: ago(18 * DAY), siteId: SITE_ID, kind: "feedback", note: "The LinkedIn post about the tax feature opened with a question. Don't — it reads as engagement bait. Open with the number." },
  { id: "nt_4", createdAt: ago(9 * DAY), updatedAt: ago(9 * DAY), siteId: SITE_ID, kind: "note", note: "Competitor pages must stay fair. If QuickBooks does something better (payroll, inventory, multi-entity) the page says so in the first screen." },
  { id: "nt_5", createdAt: ago(4 * DAY), updatedAt: ago(4 * DAY), siteId: SITE_ID, kind: "feedback", note: "Replies on Reddit: never link to ledgerly.app in the first reply. Answer the question; link only if they ask." },
  { id: "nt_6", createdAt: ago(2 * DAY), updatedAt: ago(2 * DAY), siteId: SITE_ID, kind: "note", note: "The mobile app ships in November. Say 'later this year' publicly, nothing more specific." },
];

export const KEYS: ApiKey[] = [
  { id: "key_1", createdAt: ago(40 * DAY), updatedAt: ago(40 * DAY), name: "Maya's MacBook", preview: "mlu_…4f9c", lastUsedAt: ago(20 * 60_000) },
];

export const CREDITS = {
  balance: { balanceMicros: 41_320_000, balanceUsd: 41.32 },
  ledger: [
    { id: "lg_1", kind: "charge", deltaUsd: -0.184, balanceAfterUsd: 41.32, note: "social_search · reddit + x, 4 queries", createdAt: ago(9 * HOUR) },
    { id: "lg_2", kind: "charge", deltaUsd: -0.62, balanceAfterUsd: 41.504, note: "prospect_sources · Freelancers leaving QuickBooks", createdAt: ago(2 * DAY) },
    { id: "lg_3", kind: "charge", deltaUsd: -0.031, balanceAfterUsd: 42.124, note: "seo_data · keyword volume, 12 terms", createdAt: ago(3 * DAY) },
    { id: "lg_4", kind: "charge", deltaUsd: -0.209, balanceAfterUsd: 42.155, note: "social_search · daily run", createdAt: ago(3 * DAY + 2 * HOUR) },
    { id: "lg_5", kind: "topup", deltaUsd: 50, balanceAfterUsd: 50, note: "Card ending 4242", createdAt: ago(20 * DAY) },
  ],
};

export function scopeFor(action: string) {
  const writes: Record<string, string[]> = {
    "content-piece": ["content_piece_save"],
    "content-draft": ["content_piece_save"],
    "content-channel-rules": ["content_channel_rules_save"],
    "profile-setup": ["profile_save"],
    "analyze-data": ["analytics_report_save"],
    "ask-site": ["site_link_suggestions_run", "site_summary_save"],
    "ask-leads": ["lead_stage_set", "lead_note_save"],
    "ask-social-listening": ["social_reply_draft_save"],
  };
  return {
    action,
    writes: writes[action] ?? [],
    mcpServers: { "meelu-analytics": { transport: "stdio" } },
    global: action === "profile-setup",
  };
}

export const STATS = {
  site: { pages: 0, needsReading: 0 },
  pages: { open: 0, verified: 3, rejected: 2 },
  analytics: { sources: 4, reports: 2 },
  content: { drafts: 0, blocked: 0 },
};
