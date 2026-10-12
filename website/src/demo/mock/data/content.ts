import type { ContentPiece, SiteChannel } from "@demo/lib/types";
import type { PieceIssue } from "@/app/demo/dashboard/content/types";
import { ago, DAY, HOUR } from "../rand";
import { pageId, SITE_ID } from "./site";

const LINKEDIN_RULES = [
  "Open with one concrete sentence that could only be written by someone who did the thing. No throat-clearing, no \"In today's fast-paced world\".",
  "The first two lines are all anyone sees before \"…more\". Earn the click there or nowhere.",
  "Short paragraphs, one idea each, blank line between. Walls of text lose.",
  "800–1,600 characters is the sweet spot. The limit is 3,000; needing it is usually a sign the post is two posts.",
  "Close with a real question or a clear takeaway — not \"Thoughts? 👇\".",
  "First person, past tense, specific. \"We cut onboarding from 6 steps to 2\" beats \"Streamlining onboarding is critical\".",
  "Numbers, names and dates wherever they're true. Vagueness reads as bluffing.",
  "Say the uncomfortable part. The posts that land admit a cost, a mistake, or a tradeoff.",
  "Avoid: Engagement bait: \"Agree?\", \"Who else?\", \"Save this for later\", follow-for-follow, fake polls.",
  "Avoid: The broetry format — one. line. per. paragraph. for. drama.",
  "Avoid: Emoji bullets and emoji section headers. At most one emoji, if any.",
  "Avoid: Hashtag stuffing. Three at the end, or none.",
  "Avoid: Anything that reads as if it were written by a language model: \"delve\", \"leverage\", \"in today's landscape\", \"game-changer\", \"unlock\", \"supercharge\".",
  "Avoid: External links in the body when it can be avoided — LinkedIn suppresses reach on them. Put the link in the first comment and say so.",
  "3,000 character hard limit.",
  "No markdown. Bold and italics do not render; asterisks show up literally.",
  "Never open a post with a question — a habit we are trying to break.",
];

const X_RULES = [
  "One idea per post. If it needs a second sentence to make sense, it is a thread.",
  "Lead with the claim, then the evidence. Nobody reads to the end for the point.",
  "Numbers beat adjectives. \"38% of invoices paid late\" beats \"lots of late invoices\".",
  "No hashtags unless it is an event tag. They read as spam.",
  "Links cost reach. Put the link in a reply and say \"link below\".",
  "280 character hard limit; a thread is many posts, each under the limit.",
];

const INSTAGRAM_RULES = [
  "The image does the work; the caption explains, sharpens or undercuts it. Write the caption to the picture.",
  "Say what the image is, for anyone who can't see it well. Then say why it's here.",
  "First line is the hook; the rest folds behind \"more\".",
  "Links in captions are dead text. Say \"link in bio\" only if the bio link actually goes there.",
  "Up to five hashtags, at the end, all relevant. No hashtag walls.",
  "A caption with no picture cannot post. Instagram takes the image first, the words second.",
];

const WEBSITE_RULES = [
  "Plain, slightly dry, explains rather than sells. The reader is a freelancer with twenty minutes.",
  "Lead with the answer. Background goes after, if at all.",
  "One H1, matching the title. H2s every 250–400 words; the H2 should make sense in a table of contents on its own.",
  "Short paragraphs. Bullet lists for steps, not for prose.",
  "Link to the product feature once where it is genuinely the answer, never in the first paragraph.",
  "Every number has a source or is ours. If it is ours, say how we counted.",
  "No \"in this article we will\". No \"conclusion\" heading.",
  "Meta description under 155 characters, written as a sentence, not a keyword list.",
];

function channel(key: string, label: string, enabled: boolean, rules: string[], composeUrl: string, characterLimit: number, requiresMedia: boolean, maxLinks: number | null, maxHashtags: number | null, maxMedia: number): SiteChannel {
  return {
    id: `ch_${key}`,
    createdAt: ago(41 * DAY),
    updatedAt: ago(9 * DAY),
    siteId: SITE_ID,
    channelKey: key,
    enabled,
    rules,
    label,
    composeUrl,
    characterLimit,
    requiresMedia,
    maxLinks,
    maxHashtags,
    maxMedia,
  };
}

export const CHANNELS: SiteChannel[] = [
  channel("website", "Website", true, WEBSITE_RULES, "https://ledgerly.app/admin/posts/new", 100000, false, null, null, 20),
  channel("linkedin", "LinkedIn", true, LINKEDIN_RULES, "https://www.linkedin.com/feed/?shareActive=true", 3000, false, 1, 3, 9),
  channel("twitter", "X", true, X_RULES, "https://x.com/compose/post", 280, false, 1, 2, 4),
  channel("instagram", "Instagram", true, INSTAGRAM_RULES, "https://www.instagram.com/", 2200, true, 0, 5, 10),
  channel("threads", "Threads", false, ["One thought, plainly. Threads rewards replies, so end where a reply is easy."], "https://www.threads.net/", 500, false, 1, 1, 10),
  channel("bluesky", "Bluesky", false, ["Short, wry, no hashtags. Bluesky reads like early Twitter."], "https://bsky.app/", 300, false, 1, 2, 4),
  channel("facebook", "Facebook", false, ["Longer is fine. Pictures do most of the work."], "https://www.facebook.com/", 63206, false, 1, 2, 10),
  channel("tiktok", "TikTok", false, ["The caption is a hook for the video, not a summary of it."], "https://www.tiktok.com/upload", 2200, true, 0, 4, 1),
  channel("pinterest", "Pinterest", false, ["Title like a search result; description like alt text."], "https://www.pinterest.com/pin-builder/", 500, true, 1, 3, 1),
  channel("telegram", "Telegram", false, ["Plain text, one link, no hashtags."], "https://web.telegram.org/", 4096, false, 2, 0, 10),
  channel("google_business", "Google Business", false, ["Local, factual, current. Opening hours beat slogans."], "https://business.google.com/", 1500, false, 1, 0, 10),
];

const PIECE_BODIES: Record<string, string> = {
  invoicing_guide: `## The short version

Send the invoice the day the work ships. Make the due date a real date, not "net 30". Remind on day one after it, not day thirty.

That is the whole method. The rest of this piece is why each part matters and how to set it up so you never think about it again.

## Send it the day the work ships

Every day between delivery and invoice is a day the client's finance team does not know you exist. We looked at 4,100 invoices sent through Ledgerly last year: invoices sent within 24 hours of delivery were paid a median of 9 days sooner than invoices sent a week later.

## Make the due date a date

"Net 30" means "thirty days from whenever they decide to open this". A date on the invoice — 14 October — is something a person can put in a calendar and a bookkeeper can sort by.

## Remind once, early, and kindly

The first reminder should go out the day after the due date. Not because the client is late — they may not have seen it — but because a reminder a day late reads as organised, and a reminder a month late reads as desperate.

Ledgerly sends that reminder for you if you turn it on. Most people do not, which is the point of this paragraph.`,
  linkedin_late: `We looked at 4,100 invoices sent through Ledgerly last year to answer one question: what actually gets a freelancer paid faster?

Not the payment terms. Not the late fee. Not the polite tone.

The single biggest factor was how quickly the invoice went out after the work was delivered. Same-day invoices were paid a median of 9 days sooner than invoices sent a week later.

Nine days. For doing the boring part on the day instead of on Friday.

We built the reminder feature because people asked for it. But if we had to pick one thing to tell every new customer, it would be this: invoice before you close the laptop.

What is the thing you keep putting off until Friday?`,
  x_late: `4,100 invoices, one finding: same-day invoicing gets you paid a median of 9 days sooner than invoicing a week later.

Not the terms. Not the late fee. Just sending it.`,
  ig_receipts: `The receipt drawer, before and after.

Left: eleven months of paper, a coffee ring, and one receipt from a café that closed in 2023.

Right: the same receipts, attached to the transactions they belong to, in the time it took the coffee to go cold.

If your drawer looks like the left, the fix is thirty seconds per receipt, done on the day. Not a Sunday. Never a Sunday.

#bookkeeping #freelancelife #receipts`,
  quarterly_taxes: `## Why estimated taxes exist

If nobody withholds tax from your income, the IRS wants it in four instalments through the year rather than one payment in April. Miss the instalments and you owe a penalty even if you pay in full at the end.

## When they are due

15 April, 15 June, 15 September and 15 January. The gaps are uneven; that is not a typo.

## How much to pay

The safe harbour rule: pay at least 100% of last year's tax (110% if you earned over $150k) split into four, and you cannot be penalised however this year turns out.

## What Ledgerly does with this

Every quarter it looks at your actual income and expenses, applies your bracket, and shows the number. You still write the cheque.`,
  wave_x_thread: `Wave cut its free plan this month. If you are on it, here is what changed and what it costs now. A thread.`,
  ig_blocked: `Month-end, done by 9:14am on the first.

Three clients invoiced, two reconciliations, one coffee.`,
};

function piece(id: string, title: string, channelKey: string, body: string, opts: Partial<ContentPiece> = {}): ContentPiece {
  const checks = opts.checks ?? [];
  return {
    id,
    createdAt: ago(6 * DAY),
    updatedAt: ago(3 * HOUR),
    siteId: SITE_ID,
    title,
    channelKey,
    status: checks.some((c) => c.level === "block") ? "blocked" : "draft",
    wordCount: body.split(/\s+/).filter(Boolean).length,
    checks,
    mediaSource: "none",
    mediaUrl: null,
    mediaAlt: null,
    mediaWidth: null,
    mediaHeight: null,
    mediaCreditName: null,
    mediaCreditUrl: null,
    mediaUploadId: null,
    parentPieceId: null,
    bodyMarkdown: body,
    createdBy: "agent",
    sourcePageId: null,
    ...opts,
  };
}

export const PIECES: ContentPiece[] = [
  piece("pc_1", "How to get paid faster: what 4,100 invoices told us", "website", PIECE_BODIES.invoicing_guide, { createdAt: ago(2 * DAY), updatedAt: ago(40 * 60_000), sourcePageId: pageId("/blog/late-paying-clients") }),
  piece("pc_2", "Same-day invoicing gets you paid 9 days sooner", "linkedin", PIECE_BODIES.linkedin_late, { createdAt: ago(2 * DAY), updatedAt: ago(2 * HOUR), parentPieceId: "pc_1" }),
  piece("pc_3", "4,100 invoices, one finding", "twitter", PIECE_BODIES.x_late, { createdAt: ago(2 * DAY), updatedAt: ago(2 * HOUR), parentPieceId: "pc_1" }),
  piece("pc_4", "The receipt drawer, before and after", "instagram", PIECE_BODIES.ig_receipts, {
    createdAt: ago(4 * DAY),
    updatedAt: ago(DAY),
    mediaSource: "unsplash",
    mediaUrl: "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80",
    mediaAlt: "A wooden desk with a stack of paper receipts beside a laptop",
    mediaWidth: 1200,
    mediaHeight: 800,
    mediaCreditName: "Kelly Sikkema",
    mediaCreditUrl: "https://unsplash.com/@kellysikkema",
  }),
  piece("pc_5", "Quarterly estimated taxes: the 2026 dates and the safe-harbour rule", "website", PIECE_BODIES.quarterly_taxes, { createdAt: ago(8 * DAY), updatedAt: ago(5 * DAY), createdBy: "user" }),
  piece("pc_6", "Wave cut its free plan — what changed", "twitter", PIECE_BODIES.wave_x_thread, { createdAt: ago(9 * DAY), updatedAt: ago(9 * DAY) }),
  piece("pc_7", "Month-end, done by 9:14am", "instagram", PIECE_BODIES.ig_blocked, {
    createdAt: ago(DAY),
    updatedAt: ago(5 * HOUR),
    checks: [{ code: "media_required", level: "block", message: "Instagram needs a picture. Add one and this piece unblocks." }],
  }),
  piece("pc_8", "Nine people, two time zones, one ledger: how we run Ledgerly's own books", "linkedin", "We run Ledgerly's books in Ledgerly. Obviously. But the interesting part is what broke when the team went from four people to nine across Portland and Lisbon.\n\nThe short list: expense reimbursements in two currencies, a contractor in a third, and a CFO who is also the person writing this post.\n\nHere is what we changed.", { createdAt: ago(12 * DAY), updatedAt: ago(11 * DAY), createdBy: "user" }),
];

export const ISSUES: PieceIssue[] = [
  {
    id: "is_1", pieceId: "pc_1", tool: "seo", code: "meta_missing", title: "No meta description yet", detail: "The piece has a title but nothing for the snippet. Google will pick a sentence from the body.", anchorText: null, suggestion: "Send the invoice the day the work ships and remind the day after it is due — what 4,100 invoices told us about getting paid faster.", state: "open", runId: "run_1", createdAt: ago(35 * 60_000), updatedAt: ago(35 * 60_000),
  },
  {
    id: "is_2", pieceId: "pc_1", tool: "readability", code: "long_sentence", title: "One sentence runs to 41 words", detail: "Readers skim; a 41-word sentence in the second section will be skipped.", anchorText: "Not because the client is late — they may not have seen it — but because a reminder a day late reads as organised, and a reminder a month late reads as desperate.", suggestion: "Not because the client is late — they may not have seen it. A reminder a day late reads as organised. A reminder a month late reads as desperate.", state: "open", runId: "run_1", createdAt: ago(35 * 60_000), updatedAt: ago(35 * 60_000),
  },
  {
    id: "is_3", pieceId: "pc_1", tool: "similarity", code: "overlaps_page", title: "Overlaps an existing page", detail: "The section on reminders repeats /blog/late-paying-clients closely enough that the two may compete. Link to it instead, or fold the two together.", anchorText: "The first reminder should go out the day after the due date.", suggestion: null, state: "open", runId: "run_1", createdAt: ago(35 * 60_000), updatedAt: ago(35 * 60_000),
  },
  {
    id: "is_4", pieceId: "pc_1", tool: "ai_detector", code: "ai_likelihood", title: "Reads as human-written", detail: "Score 0.12 — well under the threshold. Nothing to do.", anchorText: null, suggestion: null, state: "fixed", runId: "run_1", createdAt: ago(35 * 60_000), updatedAt: ago(35 * 60_000),
  },
  {
    id: "is_5", pieceId: "pc_2", tool: "channel_rules", code: "closing_question", title: "Ends on a question — the LinkedIn rules ask for a takeaway or a real question", detail: "\"What is the thing you keep putting off until Friday?\" is close to engagement bait. Make it specific or replace it with the takeaway.", anchorText: "What is the thing you keep putting off until Friday?", suggestion: "Invoice before you close the laptop. That is the whole finding.", state: "open", runId: "run_2", createdAt: ago(2 * HOUR), updatedAt: ago(2 * HOUR),
  },
];

export function nextIssueId(): string {
  return `is_${Math.random().toString(36).slice(2, 8)}`;
}
