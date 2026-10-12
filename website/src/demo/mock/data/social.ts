import type {
  SocialListeningClass,
  SocialListeningConfig,
  SocialListeningPost,
  SocialListeningPostKind,
  SocialListeningPostStatus,
  SocialListeningQuery,
  SocialListeningRun,
  SocialListeningTarget,
} from "@demo/lib/types";
import { ago, DAY, HOUR } from "../rand";
import { SITE_ID } from "./site";

export const CONFIG: SocialListeningConfig = {
  id: "slc_1",
  createdAt: ago(30 * DAY),
  updatedAt: ago(3 * DAY),
  siteId: SITE_ID,
  platforms: ["reddit", "hackernews", "x", "linkedin"],
  resultsPerKeyword: 40,
  minRelevance: 0.55,
  minSimilarity: 0.42,
  maxAgeDays: 30,
  dropDeadPosts: true,
  schedule: "daily",
};

export const QUERIES: SocialListeningQuery[] = [
  { id: "q_1", createdAt: ago(30 * DAY), updatedAt: ago(30 * DAY), siteId: SITE_ID, text: "freelancers asking which bookkeeping or invoicing app to use", enabled: true, source: "user", keywords: ["bookkeeping app", "invoicing app", "accounting software freelancer"], negativeKeywords: ["enterprise", "payroll", "job"], embedded: true },
  { id: "q_2", createdAt: ago(30 * DAY), updatedAt: ago(30 * DAY), siteId: SITE_ID, text: "self-employed people confused about quarterly estimated taxes", enabled: true, source: "user", keywords: ["estimated taxes", "quarterly taxes", "1040-ES"], negativeKeywords: ["corporate"], embedded: true },
  { id: "q_3", createdAt: ago(20 * DAY), updatedAt: ago(20 * DAY), siteId: SITE_ID, text: "clients paying invoices late and what to do about it", enabled: true, source: "suggested", keywords: ["late invoice", "client hasn't paid", "payment reminder"], negativeKeywords: [], embedded: true },
  { id: "q_4", createdAt: ago(10 * DAY), updatedAt: ago(10 * DAY), siteId: SITE_ID, text: "people complaining that QuickBooks or FreshBooks is too expensive or too complex", enabled: true, source: "suggested", keywords: ["quickbooks too expensive", "quickbooks alternative", "freshbooks price"], negativeKeywords: ["quickbooks desktop"], embedded: true },
  { id: "q_5", createdAt: ago(5 * DAY), updatedAt: ago(5 * DAY), siteId: SITE_ID, text: "small cafés and shops doing their own books", enabled: false, source: "suggested", keywords: ["cafe bookkeeping"], negativeKeywords: [], embedded: false },
];

export const TARGETS: SocialListeningTarget[] = [
  { id: "t_1", createdAt: ago(30 * DAY), updatedAt: ago(30 * DAY), siteId: SITE_ID, kind: "brand", name: "Ledgerly", enabled: true, source: "profile" },
  { id: "t_2", createdAt: ago(30 * DAY), updatedAt: ago(30 * DAY), siteId: SITE_ID, kind: "competitor", name: "QuickBooks", enabled: true, source: "profile" },
  { id: "t_3", createdAt: ago(30 * DAY), updatedAt: ago(30 * DAY), siteId: SITE_ID, kind: "competitor", name: "FreshBooks", enabled: true, source: "profile" },
  { id: "t_4", createdAt: ago(30 * DAY), updatedAt: ago(30 * DAY), siteId: SITE_ID, kind: "competitor", name: "Wave", enabled: true, source: "suggested" },
  { id: "t_5", createdAt: ago(12 * DAY), updatedAt: ago(12 * DAY), siteId: SITE_ID, kind: "competitor", name: "Bonsai", enabled: false, source: "user" },
];

export const LAST_RUN: SocialListeningRun = {
  id: "slr_14",
  createdAt: ago(HOUR * 9),
  updatedAt: ago(HOUR * 9 - 6 * 60_000),
  siteId: SITE_ID,
  status: "done",
  startedAt: ago(HOUR * 9),
  finishedAt: ago(HOUR * 9 - 6 * 60_000),
  fetchedCount: 312,
  keptCount: 27,
  platformStats: {
    reddit: { fetched: 160, kept: 14 },
    hackernews: { fetched: 48, kept: 5 },
    x: { fetched: 84, kept: 6 },
    linkedin: { fetched: 20, kept: 2 },
  },
  error: null,
};

type P = [
  platform: string,
  kind: SocialListeningPostKind,
  title: string | null,
  text: string,
  author: string,
  hoursAgo: number,
  score: number,
  comments: number,
  intent: string,
  sentiment: "positive" | "neutral" | "negative",
  classes: SocialListeningClass[],
  relevance: number,
  status: SocialListeningPostStatus,
  angle: string | null,
  queryId: string | null,
  targets: string[],
  subreddit: string | null,
];

const POSTS_SEED: P[] = [
  ["reddit", "topic", "What do you actually use for bookkeeping as a one-person business?", "I've tried QuickBooks (too much), Wave (free plan gutted), and a spreadsheet (fine until it isn't). I send maybe 8 invoices a month and need to track expenses and know roughly what I owe in tax. What are people using?", "u/quietfreelance", 5, 214, 87, "seeking_tool", "neutral", ["question"], 0.94, "needs_reply", "Answer the actual question first: for 8 invoices a month, the spreadsheet is fine until tax time, and that is the moment to switch. Mention the tax estimate as the thing a spreadsheet cannot do; mention Ledgerly once, at the end, as one option.", "q_1", [], "r/freelance"],
  ["hackernews", "topic", "Ask HN: How do you handle quarterly estimated taxes as a solo founder?", "First year with real income and I have no idea what to set aside. My accountant says 'about a third' which feels like a shrug.", "dmitryk", 11, 96, 142, "seeking_help", "neutral", ["question"], 0.91, "needs_reply", "Explain the safe-harbour rule plainly (100% of last year's tax, 110% over $150k). That is the answer they need; the tool is secondary.", "q_2", [], null],
  ["reddit", "topic", "Client is 47 days late on a $6k invoice. What now?", "Sent two polite reminders. They keep saying 'processing'. Contract says net 30. Do I add a late fee? Do I stop work?", "u/inkandpixels", 19, 178, 64, "seeking_help", "negative", ["question"], 0.89, "drafted", "Give the sequence: a firm reminder with a date, then a late fee if the contract allows it, then pausing work. Link the reminder templates only if they ask.", "q_3", [], "r/graphic_design"],
  ["x", "topic", null, "QuickBooks just told me my plan is going from $30 to $38/mo. I use it to send four invoices. Four.", "@ninaillustrates", 27, 340, 41, "complaining", "negative", ["complaint", "switch_opportunity"], 0.88, "needs_reply", "Do not pitch. Agree that $38 for four invoices is absurd and ask what else they need it to do. If they answer, the reply writes itself.", "q_4", ["QuickBooks"], null],
  ["reddit", "topic", "Wave removed the free receipt scanning. Alternatives?", "I was fine with Wave until they moved receipts behind the paywall. I don't mind paying but not $16 for receipts alone.", "u/mtl_dev", 33, 122, 58, "seeking_tool", "negative", ["switch_opportunity", "question"], 0.86, "needs_reply", "Wave's change is real and recent; say what changed. Then list two or three options including ours, with prices, so it reads as help not a pitch.", "q_4", ["Wave"], "r/smallbusiness"],
  ["linkedin", "topic", null, "Unpopular opinion: most freelancers don't need accounting software. They need an invoicing tool and a tax estimate. Everything else is for accountants.", "Marcus Bell", 41, 89, 33, "discussion", "neutral", ["question"], 0.83, "needs_reply", "Agree, and add the one thing missing from the take: the tax estimate only works if expenses are tracked, so 'invoicing plus tax' quietly needs expenses too.", "q_1", [], null],
  ["hackernews", "topic", "Show HN: I built a CLI to generate invoices from YAML", "Because every invoicing app wants $15/month for a PDF. Feedback welcome.", "tarquin", 52, 210, 118, "discussion", "positive", ["question"], 0.71, "skipped", null, "q_1", [], null],
  ["reddit", "topic", "How much should I set aside for taxes as a first-year freelancer (US)?", "Made about $70k so far. Haven't paid anything. Am I in trouble?", "u/newlyfree", 60, 67, 39, "seeking_help", "negative", ["question"], 0.85, "replied", "Reply already sent: safe harbour, the January deadline, and a plain note that they are probably fine but should pay Q4.", "q_2", [], "r/personalfinance"],
  ["x", "topic", null, "Anyone else's clients treat 'net 30' as 'net whenever'? Asking for my rent.", "@copybyhannah", 70, 512, 96, "complaining", "negative", ["complaint"], 0.8, "needs_reply", "Light touch. Share the same-day-invoice finding (9 days sooner) as a stat, no link.", "q_3", [], null],
  ["reddit", "topic", "Recommend a FreshBooks alternative that isn't QuickBooks", "FreshBooks is fine but the price keeps climbing and I've never used projects or time tracking.", "u/atlas_photo", 88, 54, 27, "seeking_tool", "neutral", ["switch_opportunity", "question"], 0.87, "needs_reply", "List three, ours included, one line each. Be honest about what ours lacks (payroll, inventory).", "q_4", ["FreshBooks"], "r/freelance"],
  ["reddit", "topic", "Best way to track expenses when half of them are on a personal card?", "I know, I know. Separate accounts. But in the meantime?", "u/somewhat_organised", 100, 41, 22, "seeking_help", "neutral", ["question"], 0.74, "skipped", null, "q_1", [], "r/smallbusiness"],
  ["reddit", "brand", "Tried Ledgerly for a month — honest review", "Switched from QuickBooks. The invoicing is genuinely nicer and the tax estimate thing is the reason I'm staying. Bank feed for my credit union took a week to connect though, and there's no mobile app yet.", "u/quietfreelance", 8, 143, 52, "recommending", "positive", ["praise", "feature_request"], 0.97, "needs_reply", "Thank them, confirm the mobile app is being built (say when), and explain the credit union delay honestly.", null, ["Ledgerly"], "r/freelance"],
  ["x", "brand", null, "Ledgerly's quarterly tax estimate just told me I owe $2,100 less than I'd set aside. First time software has ever given me money back.", "@devonwrites", 22, 421, 18, "praising", "positive", ["praise"], 0.96, "replied", null, null, ["Ledgerly"], null],
  ["x", "brand", null, "@ledgerlyapp is there a way to send an invoice in two currencies? Client in Berlin, me in Toronto.", "@sofiaillustra", 30, 12, 4, "seeking_help", "neutral", ["question", "feature_request"], 0.95, "needs_reply", "Yes — the multi-currency page explains it. Answer in one line and link to the doc.", null, ["Ledgerly"], null],
  ["hackernews", "brand", null, "We moved a nine-person agency onto Ledgerly last quarter. It's clearly built for smaller than us but the accountant export is the best I've seen.", "hrafn", 55, 38, 9, "recommending", "positive", ["praise"], 0.93, "needs_reply", "Thank them; ask what would make it fit a nine-person team, since that is exactly the edge of the product.", null, ["Ledgerly"], null],
  ["reddit", "brand", "Ledgerly bank feed keeps disconnecting", "Third time this month. Anyone else? Chase, US.", "u/bkln_dev", 61, 19, 11, "complaining", "negative", ["complaint"], 0.94, "needs_reply", "This is a known Chase issue from the aggregator change on the 3rd. Say so, give the fix, and ask them to DM if it recurs.", null, ["Ledgerly"], "r/ledgerly"],
  ["linkedin", "brand", null, "Recommended Ledgerly to three freelancer clients this month. The accountant seat is the thing that sold me — I can see their books without asking for a login.", "Aisha Rahman", 78, 64, 14, "recommending", "positive", ["praise"], 0.92, "drafted", "Thank her and mention the partner programme once.", null, ["Ledgerly"], null],
  ["x", "brand", null, "ledgerly has no dark mode in 2026?? my eyes", "@nightowlcodes", 90, 88, 12, "complaining", "negative", ["feature_request"], 0.9, "skipped", null, null, ["Ledgerly"], null],
  ["reddit", "competitor", "QuickBooks price increase thread (again)", "Simple Start going to $38. What's everyone doing? I'm one person.", "u/tired_of_intuit", 6, 389, 211, "complaining", "negative", ["complaint", "switch_opportunity"], 0.9, "needs_reply", "High-traffic thread. One honest reply listing alternatives including ours, with the caveat that none of them do payroll.", "q_4", ["QuickBooks"], "r/smallbusiness"],
  ["x", "competitor", null, "FreshBooks support took 4 days to answer a question about a duplicated invoice. Four days.", "@jbrooksdesign", 14, 156, 23, "complaining", "negative", ["complaint"], 0.82, "needs_reply", "Do not pile on. Sympathise, offer nothing unless asked.", "q_4", ["FreshBooks"], null],
  ["reddit", "competitor", "Wave alternatives now that the free plan is gutted", "Receipts, bank feed, and now invoicing limits. It was good while it lasted.", "u/mtl_dev", 34, 201, 97, "seeking_tool", "negative", ["switch_opportunity", "question"], 0.88, "drafted", "List alternatives with prices. Ours is $12; say so plainly.", "q_4", ["Wave"], "r/smallbusiness"],
  ["hackernews", "competitor", null, "QuickBooks is the Salesforce of bookkeeping: everyone hates it and everyone's accountant insists on it.", "pjm", 48, 74, 51, "discussion", "negative", ["complaint"], 0.79, "needs_reply", "The accountant lock-in is real. The angle is the accountant export — mention that accountants can read our export without a QuickBooks licence.", "q_4", ["QuickBooks"], null],
  ["linkedin", "competitor", null, "Honest question for bookkeepers: do you still recommend QuickBooks to sole traders, or has the price finally crossed the line?", "Ben Carter", 66, 112, 68, "discussion", "neutral", ["question"], 0.84, "needs_reply", "A bookkeeper asking bookkeepers. Reply as a vendor only if there is something useful to add — the accountant seat, perhaps.", "q_4", ["QuickBooks"], null],
  ["reddit", "competitor", "FreshBooks vs Wave vs QuickBooks for a photographer", "Deposits and final invoices are 90% of what I do.", "u/atlas_photo", 92, 45, 31, "seeking_tool", "neutral", ["question", "switch_opportunity"], 0.86, "needs_reply", "Deposits are a feature we do well. Answer the comparison honestly and mention ours as a fourth.", "q_4", ["FreshBooks", "Wave", "QuickBooks"], "r/photography"],
  ["x", "competitor", null, "Wave's new pricing page is a masterclass in hiding what you actually get for free.", "@finlit_sam", 110, 233, 40, "complaining", "negative", ["complaint"], 0.77, "skipped", null, "q_4", ["Wave"], null],
  ["reddit", "topic", "Invoice numbering — do you restart each year?", "INV-2026-001 or just keep counting?", "u/spreadsheet_sam", 130, 33, 29, "discussion", "neutral", ["question"], 0.68, "needs_reply", "Keep counting; sequential numbers matter for audits. Link the numbering post if asked.", "q_1", [], "r/freelance"],
  ["hackernews", "topic", "Ask HN: Solo devs, how do you handle 1099s from many clients?", "Eleven clients, eleven forms, one shoebox.", "mgold", 150, 58, 44, "seeking_help", "neutral", ["question"], 0.81, "needs_reply", "The 1099 guide answers this directly. Summarise the two rules and link.", "q_2", [], null],
];

export const POSTS: SocialListeningPost[] = POSTS_SEED.map(([platform, kind, title, text, author, hoursAgo, score, comments, intent, sentiment, classes, relevance, status, angle, queryId, targets, subreddit], i) => ({
  id: `sp_${i + 1}`,
  createdAt: ago(hoursAgo * HOUR),
  updatedAt: ago(Math.max(1, hoursAgo - 1) * HOUR),
  siteId: SITE_ID,
  url:
    platform === "reddit" ? `https://www.reddit.com/${subreddit}/comments/1k${(i + 10).toString(36)}q/${(title ?? "post").toLowerCase().replace(/[^a-z0-9]+/g, "_").slice(0, 40)}/`
    : platform === "hackernews" ? `https://news.ycombinator.com/item?id=${41300000 + i * 137}`
    : platform === "x" ? `https://x.com/${author.replace("@", "")}/status/${1839000000 + i * 9973}`
    : `https://www.linkedin.com/posts/${author.toLowerCase().replace(/\s+/g, "-")}_${1000 + i}`,
  platform,
  kind,
  title,
  text,
  authorHandle: author,
  authorName: author.replace(/^[@u/]+/, "").replace(/_/g, " "),
  postedAt: ago(hoursAgo * HOUR),
  engagement: { score, comments, views: platform === "x" ? score * 41 : null },
  context: { subreddit, tags: null },
  matchedTargets: targets,
  intent,
  sentiment,
  isQuestion: classes.includes("question"),
  classes,
  relevance,
  compositeScore: Math.round((relevance * 0.7 + Math.min(1, score / 400) * 0.3) * 100) / 100,
  keepReason: kind === "topic" ? "Matched a listening query above the relevance floor." : `Mentions ${targets.join(", ")}.`,
  suggestedAngle: angle,
  status,
  similarity: kind === "topic" ? Math.round(relevance * 0.9 * 100) / 100 : null,
  queryId,
  replyText: status === "drafted"
    ? (i === 2
      ? "47 days is past polite. Send one more reminder with a date in it — \"by Friday 26th\" — and say what happens after: the late fee your contract already allows, and work pausing. Most 'processing' clients pay the day they see a date."
      : "Thank you — that is exactly the reason the accountant seat exists. If any of those clients want the export walked through, we're happy to.")
    : status === "replied"
      ? (i === 7 ? "You're probably fine: pay at least 100% of last year's tax across the four dates and there is no penalty regardless of what you actually owe. Q4 is due 15 January." : "This made our week. Thank you.")
      : null,
  repliedAt: status === "replied" ? ago(Math.max(1, hoursAgo - 3) * HOUR) : null,
  runId: hoursAgo < 12 ? "slr_14" : "slr_13",
}));
