import type {
  SocialListeningConfig,
  SocialListeningPost,
  SocialListeningQuery,
  SocialListeningReviewStatus,
  SocialListeningRun,
} from "@demo/lib/types";
import { ago, DAY, HOUR } from "../rand";
import { SITE_ID } from "./site";

export interface PlatformInfo {
  id: string;
  label: string;
  access: "direct" | "apify";
  available: boolean;
}

export const PLATFORMS: PlatformInfo[] = [
  { id: "hackernews", label: "Hacker News", access: "direct", available: true },
  { id: "stackexchange", label: "Stack Exchange", access: "direct", available: true },
  { id: "devto", label: "Dev.to", access: "direct", available: true },
  { id: "github", label: "GitHub Issues", access: "direct", available: true },
  { id: "reddit", label: "Reddit", access: "apify", available: true },
  { id: "x", label: "X (Twitter)", access: "apify", available: true },
  { id: "linkedin", label: "LinkedIn", access: "apify", available: true },
  { id: "bluesky", label: "Bluesky", access: "apify", available: true },
  { id: "facebook", label: "Facebook", access: "apify", available: true },
];

export const MAX_LINES = 30;

export const CONFIG: SocialListeningConfig = {
  id: "slc_1",
  createdAt: ago(24 * DAY),
  updatedAt: ago(3 * DAY),
  siteId: SITE_ID,
  platforms: ["reddit", "hackernews", "x", "linkedin"],
};

type Line = Omit<SocialListeningQuery, "found" | "kept" | "siteId" | "createdAt" | "updatedAt"> & { daysOld: number };

const LINES: Line[] = [
  { id: "slq_1", daysOld: 24, text: "freelancers asking which invoicing or bookkeeping app to use", enabled: true, source: "user", keywords: ["invoicing app freelancer", "bookkeeping software self-employed"], embedded: true },
  { id: "slq_2", daysOld: 24, text: "self-employed people unsure how much to set aside for quarterly taxes", enabled: true, source: "user", keywords: ["quarterly estimated taxes", "set aside for taxes freelance"], embedded: true },
  { id: "slq_3", daysOld: 18, text: "freelancers chasing clients who pay invoices late", enabled: true, source: "suggested", keywords: ["client paying late", "overdue invoice"], embedded: true },
  { id: "slq_4", daysOld: 12, text: "people fed up with QuickBooks or FreshBooks pricing for a one-person business", enabled: true, source: "suggested", keywords: ["quickbooks alternative", "freshbooks too expensive"], embedded: true },
  { id: "slq_5", daysOld: 9, text: "designers and developers mixing business expenses on a personal card", enabled: true, source: "user", keywords: ["track business expenses", "personal card business expenses"], embedded: true },
  { id: "slq_6", daysOld: 2, text: "small agencies whose accountant wants a cleaner export", enabled: false, source: "user", keywords: [], embedded: true },
];

export const QUERIES: Omit<SocialListeningQuery, "found" | "kept">[] = LINES.map(({ daysOld, ...q }) => ({
  ...q,
  siteId: SITE_ID,
  createdAt: ago(daysOld * DAY),
  updatedAt: ago(Math.max(1, daysOld - 1) * DAY),
}));

export const FOUND_BEFORE_GATE: Record<string, number> = {
  slq_1: 61,
  slq_2: 38,
  slq_3: 27,
  slq_4: 44,
  slq_5: 19,
  slq_6: 0,
};

export const RUNS: SocialListeningRun[] = [
  {
    id: "slr_12",
    createdAt: ago(3 * DAY + 2 * HOUR),
    updatedAt: ago(3 * DAY + 2 * HOUR - 7 * 60_000),
    siteId: SITE_ID,
    status: "done",
    startedAt: ago(3 * DAY + 2 * HOUR),
    finishedAt: ago(3 * DAY + 2 * HOUR - 7 * 60_000),
    fetchedCount: 406,
    matchedCount: 38,
    keptCount: 13,
    platformStats: {
      reddit: { status: "done", keywords: 10, fromVendor: 198, fromDatabase: 31, candidates: 214, failedKeywords: [] },
      hackernews: { status: "done", keywords: 10, fromVendor: 64, fromDatabase: 9, candidates: 70, failedKeywords: [] },
      x: { status: "done", keywords: 10, fromVendor: 112, fromDatabase: 14, candidates: 120, failedKeywords: [] },
      linkedin: { status: "done", keywords: 10, fromVendor: 32, fromDatabase: 4, candidates: 34, failedKeywords: [] },
    },
    error: null,
  },
  {
    id: "slr_13",
    createdAt: ago(9 * HOUR),
    updatedAt: ago(9 * HOUR - 6 * 60_000),
    siteId: SITE_ID,
    status: "done",
    startedAt: ago(9 * HOUR),
    finishedAt: ago(9 * HOUR - 6 * 60_000),
    fetchedCount: 312,
    matchedCount: 29,
    keptCount: 11,
    platformStats: {
      reddit: { status: "done", keywords: 10, fromVendor: 141, fromDatabase: 22, candidates: 152, failedKeywords: [] },
      hackernews: { status: "done", keywords: 10, fromVendor: 47, fromDatabase: 6, candidates: 51, failedKeywords: [] },
      x: { status: "done", keywords: 10, fromVendor: 84, fromDatabase: 11, candidates: 90, failedKeywords: [] },
      linkedin: { status: "done", keywords: 10, fromVendor: 20, fromDatabase: 3, candidates: 22, failedKeywords: ["personal card business expenses"] },
    },
    error: null,
  },
];

export interface Seed {
  platform: "reddit" | "hackernews" | "x" | "linkedin";
  where: string;
  name?: string;
  title: string | null;
  text: string;
  hours: number;
  score: number;
  comments: number;
  views?: number;
  query: string;
  similarity: number;
  reason: string;
  angle: string;
  status: SocialListeningReviewStatus;
  reply?: string;
  touchedHours?: number;
}

const SEEDS: Seed[] = [
  {
    platform: "reddit", where: "freelance", name: "quietfreelance",
    title: "What do you actually use for bookkeeping as a one-person business?",
    text: "I've tried QuickBooks (way too much), Wave (free plan keeps shrinking) and a Google Sheet (fine until tax time, then a nightmare).\n\nI send maybe 8 invoices a month, have a handful of software subscriptions as expenses, and mostly want to know roughly what I'll owe in April. What are people using that isn't built for a 40-person company?",
    hours: 3, score: 214, comments: 87, query: "slq_1", similarity: 0.91, status: "to_reply",
    reason: "A solo freelancer asking outright which bookkeeping tool fits about eight invoices a month.",
    angle: "Answer the real question first: at 8 invoices a month a spreadsheet works until tax time. Name the tax estimate as the thing a sheet can't do, and mention Ledgerly once, near the end, as one option with its price.",
  },
  {
    platform: "hackernews", where: "dmitryk",
    title: "Ask HN: How do you handle quarterly estimated taxes as a solo founder?",
    text: "First year with real income from my SaaS and consulting on the side. My accountant says to put away \"about a third\", which feels like a shrug. How do you all actually work out the number each quarter, and do you automate it?",
    hours: 6, score: 96, comments: 142, query: "slq_2", similarity: 0.89, status: "to_reply",
    reason: "Asks how to work out quarterly estimated tax payments, which is the exact problem the tax estimate solves.",
    angle: "Explain the safe-harbour rule plainly (100% of last year's tax, 110% above $150k AGI). That is the answer they need; the tool is secondary and only worth a line.",
  },
  {
    platform: "x", where: "ninaillustrates", name: "Nina Park",
    title: null,
    text: "QuickBooks just emailed to say my plan goes from $30 to $38 a month. I use it to send four invoices. Four.",
    hours: 8, score: 340, comments: 41, views: 18900, query: "slq_4", similarity: 0.87, status: "to_reply",
    reason: "An illustrator unhappy with a QuickBooks price rise for a very small invoicing need.",
    angle: "Don't pitch. Agree that $38 for four invoices is a lot and ask what else she needs it to do. If she answers, the reply writes itself.",
  },
  {
    platform: "reddit", where: "smallbusiness", name: "mtl_dev",
    title: "Wave moved receipt scanning behind the paywall. Alternatives?",
    text: "I was happy on Wave for three years. Now receipts are Pro-only and the bank feed has been flaky since spring. I don't mind paying, but $16/month for receipts alone feels like a lot. What did other sole proprietors switch to?",
    hours: 11, score: 122, comments: 58, query: "slq_4", similarity: 0.86, status: "to_reply",
    reason: "A sole proprietor actively looking to switch tools after a pricing change.",
    angle: "Say exactly what Wave changed so it reads as informed. Then list two or three options with prices, ours included, so it reads as help rather than an ad.",
  },
  {
    platform: "reddit", where: "graphic_design", name: "inkandpixels",
    title: "Client is 47 days late on a $6k invoice. What now?",
    text: "Two polite reminders sent. They keep saying it's \"in processing\". Contract says net 30 and has a 1.5% monthly late fee clause I've never used. Do I add the fee? Stop work on the next phase? I don't want to burn the relationship but I also have rent.",
    hours: 14, score: 178, comments: 64, query: "slq_3", similarity: 0.88, status: "to_reply",
    reason: "A designer chasing a long-overdue invoice and asking what to do next.",
    angle: "Give a clear sequence: a firm reminder with a date in it, then the late fee the contract already allows, then pausing work. No product mention unless someone asks about reminders.",
  },
  {
    platform: "linkedin", where: "marcus-bell", name: "Marcus Bell",
    title: null,
    text: "Unpopular opinion: most freelancers don't need accounting software. They need an invoicing tool and a tax estimate. Everything else is for their accountant.\n\nChange my mind.",
    hours: 19, score: 89, comments: 33, query: "slq_1", similarity: 0.83, status: "to_reply",
    reason: "A popular take on what freelancers need from bookkeeping tools; the thread is full of tool recommendations.",
    angle: "Agree, then add the missing piece: the tax estimate is only right if expenses are tracked, so \"invoicing plus tax\" quietly needs expenses too.",
  },
  {
    platform: "x", where: "copybyhannah", name: "Hannah Ortiz",
    title: null,
    text: "Anyone else's clients treat \"net 30\" as \"net whenever\"? Asking for my rent.",
    hours: 22, score: 512, comments: 96, views: 31200, query: "slq_3", similarity: 0.81, status: "to_reply",
    reason: "A copywriter venting about late-paying clients, with a busy reply thread.",
    angle: "Keep it light. Share one useful fact (invoices sent the day the work ships get paid about 9 days sooner) with no link.",
  },
  {
    platform: "reddit", where: "freelance", name: "atlas_photo",
    title: "Recommend a FreshBooks alternative that isn't QuickBooks",
    text: "FreshBooks is fine but the price keeps climbing and I've never touched projects or time tracking. I need: invoices with deposits, expense tracking, and something my accountant can read at year end.",
    hours: 27, score: 54, comments: 27, query: "slq_4", similarity: 0.88, status: "to_reply",
    reason: "A photographer listing exactly what they need from a replacement for FreshBooks.",
    angle: "List three options, one line each, ours included. Be honest about what Ledgerly lacks (payroll, inventory) so the recommendation is believable.",
  },
  {
    platform: "hackernews", where: "mgold",
    title: "Ask HN: Solo devs, how do you keep track of 1099s from many clients?",
    text: "Eleven clients last year, eleven 1099-NECs, two of which had the wrong amount. Is there a sane way to reconcile these against what you actually invoiced?",
    hours: 33, score: 58, comments: 44, query: "slq_2", similarity: 0.82, status: "to_reply",
    reason: "A contractor asking how to reconcile 1099 forms against their own invoices.",
    angle: "Explain the reconciliation in two steps: total paid invoices per client by calendar year, then compare to each 1099. Mention that the wrong ones need a corrected form from the client.",
  },
  {
    platform: "reddit", where: "webdev", name: "somewhat_organised",
    title: "Best way to separate business expenses when half of them are on my personal card?",
    text: "I know, I know, open a business account. I'm doing that next month. But for the last 9 months of hosting, Figma, a laptop and a few conference tickets, what's the least painful way to pull them out for taxes?",
    hours: 40, score: 41, comments: 22, query: "slq_5", similarity: 0.84, status: "to_reply",
    reason: "A developer asking how to pull business expenses out of a personal card statement for taxes.",
    angle: "Give the practical method: export the statement as CSV, tag business lines, keep the receipts for anything over $75. Mention that Ledgerly imports a CSV statement only if they ask what to use.",
  },
  {
    platform: "x", where: "devonwrites", name: "Devon Price",
    title: null,
    text: "Every January I swear I'll track expenses as I go. Every April I'm in a spreadsheet at 1am. Freelancers who actually stay on top of it: what's the trick?",
    hours: 52, score: 147, comments: 58, views: 9400, query: "slq_5", similarity: 0.8, status: "to_reply",
    reason: "A freelance writer asking how others keep expense tracking up to date.",
    angle: "Share the habit, not the tool: ten minutes every Friday, receipts photographed the day they happen. The tool only helps if the habit exists.",
  },
  {
    platform: "linkedin", where: "ben-carter", name: "Ben Carter",
    title: null,
    text: "Honest question for other bookkeepers: do you still recommend QuickBooks to sole traders, or has the price finally crossed the line? I'm seeing more clients push back this year.",
    hours: 68, score: 112, comments: 68, query: "slq_4", similarity: 0.79, status: "to_reply",
    reason: "A bookkeeper asking peers which tool to recommend to sole traders now.",
    angle: "Reply only with something a bookkeeper would value: the free accountant seat, and that the year-end export opens in their own software.",
  },
  {
    platform: "reddit", where: "personalfinance", name: "newlyfree",
    title: "First year freelancing (US), made ~$70k, haven't paid any estimated tax. Am I in trouble?",
    text: "Left my job in February. Haven't paid anything quarterly. I've got about $15k sitting in savings. Is that enough? Should I pay something now before January?",
    hours: 80, score: 67, comments: 39, query: "slq_2", similarity: 0.86, status: "to_reply",
    reason: "A first-year freelancer worried about missed estimated tax payments.",
    angle: "Reassure, then be specific: pay the Q4 estimate by January 15, expect a small underpayment penalty, and use last year's W-2 tax as the safe-harbour number.",
  },

  {
    platform: "reddit", where: "freelance", name: "brightline_ux",
    title: "Is it unprofessional to send invoices as a Google Doc PDF?",
    text: "I've been exporting a Google Doc template to PDF for two years. A new client's AP team asked for an invoice number and a remittance address and now I feel like an amateur.",
    hours: 30, score: 88, comments: 51, query: "slq_1", similarity: 0.85, status: "drafted", touchedHours: 2,
    reason: "A UX designer whose client asked for a more formal invoice.",
    angle: "Reassure them a PDF is normal; list the five fields AP teams look for. Mention invoicing tools only as a way to stop doing it by hand.",
    reply: "Not unprofessional at all, PDF is what AP teams expect. What they care about is the fields: a unique invoice number, your legal name and address, their PO number if they gave you one, payment terms with a due date, and how to pay you.\n\nIf you're doing more than a few a month it's worth moving off the doc so the numbering never repeats, but the template itself is fine.",
  },
  {
    platform: "x", where: "sofiaillustra", name: "Sofia Lind",
    title: null,
    text: "Client in Berlin, me in Toronto. Do I invoice in EUR or CAD? And who eats the conversion fee?",
    hours: 46, score: 23, comments: 17, views: 2100, query: "slq_3", similarity: 0.8, status: "drafted", touchedHours: 5,
    reason: "An illustrator asking how to invoice a foreign client.",
    angle: "Answer the currency question directly and suggest putting the fee in the contract.",
    reply: "Invoice in the currency your contract says. If it says nothing, EUR is easier for them to pay and you take the conversion risk; CAD puts it on them. Either way add a line next time: \"bank and conversion fees are paid by the client\".",
  },
  {
    platform: "reddit", where: "Bookkeeping", name: "tired_of_intuit",
    title: "QuickBooks Simple Start going to $38. What are one-person shops moving to?",
    text: "Bookkeeper here, about a dozen sole-trader clients. Half of them are asking me what to switch to. Looking for something cheap that still gives me a clean year-end export.",
    hours: 58, score: 389, comments: 211, query: "slq_4", similarity: 0.9, status: "drafted", touchedHours: 20,
    reason: "A bookkeeper looking for a cheaper tool for sole-trader clients, with a large thread.",
    angle: "One honest reply: name a few options including ours, with prices, and be clear that none of them do payroll.",
    reply: "Disclosure: I work on Ledgerly, so weigh this accordingly.\n\nFor sole traders who mostly invoice and track expenses: Ledgerly ($12/mo, free accountant seat, year-end export opens in your software), Zoho Invoice (free tier, lighter on expenses) and Wave if their bank feed works. None of these do payroll, so anyone with staff should stay where they are.",
  },

  {
    platform: "reddit", where: "freelance", name: "spreadsheet_sam",
    title: "Invoice numbering: do you restart every year?",
    text: "INV-2026-001 or just keep counting from wherever I am? My accountant didn't have an opinion.",
    hours: 96, score: 33, comments: 29, query: "slq_1", similarity: 0.8, status: "replied", touchedHours: 70,
    reason: "A freelancer asking a practical invoicing question.",
    angle: "Either is fine as long as numbers never repeat or skip.",
    reply: "Either works. What matters is that numbers never repeat and never skip, because gaps are what auditors ask about. Year prefixes make it easier to see at a glance which tax year an invoice belongs to.",
  },
  {
    platform: "hackernews", where: "hrafn",
    title: null,
    text: "We moved a nine-person agency onto a freelancer-focused bookkeeping tool last quarter. Clearly built for smaller than us, but the accountant export was better than what QuickBooks gave us.",
    hours: 110, score: 38, comments: 9, query: "slq_6", similarity: 0.82, status: "replied", touchedHours: 90,
    reason: "An agency owner describing the accountant export as the reason to switch.",
    angle: "Thank them and ask what would make it fit a nine-person team.",
    reply: "Glad the export landed. Curious what you're missing at nine people: is it approvals, multiple users entering expenses, or something else?",
  },
  {
    platform: "x", where: "jbrooksdesign", name: "Jamie Brooks",
    title: null,
    text: "Took me 4 hours to figure out how much I owe for Q3 estimated taxes. There has to be a better way.",
    hours: 130, score: 156, comments: 23, views: 8800, query: "slq_2", similarity: 0.83, status: "replied", touchedHours: 120,
    reason: "A designer frustrated by working out quarterly estimated tax by hand.",
    angle: "Share the shortcut: safe harbour means you can pay a quarter of last year's tax and stop worrying.",
    reply: "Shortcut that saves most people the 4 hours: pay a quarter of last year's total tax each quarter (110% if you made over $150k). That's the safe harbour, so no penalty even if this year comes out higher.",
  },
  {
    platform: "linkedin", where: "aisha-rahman", name: "Aisha Rahman",
    title: null,
    text: "Moved three of my freelance clients off spreadsheets this month. The thing that sold them wasn't features, it was me being able to see their books without asking for a login.",
    hours: 150, score: 64, comments: 14, query: "slq_1", similarity: 0.81, status: "replied", touchedHours: 140,
    reason: "A bookkeeper describing how she moves freelance clients off spreadsheets.",
    angle: "Thank her and agree that accountant access is the real switching reason.",
    reply: "This matches what we hear from bookkeepers: the login dance is what makes clients give up. Thanks for sharing it.",
  },
  {
    platform: "reddit", where: "smallbusiness", name: "cafe_on_main",
    title: "Bookkeeping app for a café with two staff?",
    text: "Need payroll, tips, inventory for coffee beans and a POS integration.",
    hours: 44, score: 19, comments: 12, query: "slq_1", similarity: 0.8, status: "skipped", touchedHours: 30,
    reason: "Asks which bookkeeping app to use.",
    angle: "Payroll and inventory are outside what Ledgerly does.",
  },
  {
    platform: "hackernews", where: "tarquin",
    title: "Show HN: I built a CLI that generates invoices from YAML",
    text: "Because every invoicing app wants $15/month for a PDF. Feedback welcome.",
    hours: 75, score: 210, comments: 118, query: "slq_1", similarity: 0.8, status: "skipped", touchedHours: 60,
    reason: "Discussion about invoicing tools for freelancers.",
    angle: "A Show HN for a free tool; a vendor reply would read as an ad.",
  },
  {
    platform: "x", where: "finlit_sam", name: "Sam Okafor",
    title: null,
    text: "Wave's new pricing page is a masterclass in hiding what you actually get for free.",
    hours: 120, score: 233, comments: 40, views: 14200, query: "slq_4", similarity: 0.8, status: "skipped", touchedHours: 100,
    reason: "Complaint about a competitor's pricing.",
    angle: "Nothing to add that isn't piling on.",
  },
  {
    platform: "reddit", where: "tax", name: "cpa_throwaway_88",
    title: "Corporate estimated tax for an S-corp with 40 employees",
    text: "Client moved from C-corp to S-corp mid-year. How do we handle the 1120-W estimates for the stub period?",
    hours: 36, score: 12, comments: 7, query: "slq_2", similarity: 0.81, status: "rejected", touchedHours: 26,
    reason: "Mentions estimated tax payments.",
    angle: "Corporate tax for a 40-person company, not a freelancer.",
  },
  {
    platform: "linkedin", where: "acme-recruiting", name: "Acme Recruiting",
    title: null,
    text: "We're hiring! Freelance bookkeeper needed, 10 hrs/week, QuickBooks Online experience required. DM for details.",
    hours: 88, score: 8, comments: 2, query: "slq_4", similarity: 0.8, status: "rejected", touchedHours: 80,
    reason: "Mentions freelancers and QuickBooks.",
    angle: "A job post, not a conversation.",
  },
  {
    platform: "x", where: "latepay_bot", name: "Late Payment Tips",
    title: null,
    text: "5 tips to get your invoices paid faster 🧵 (1/5)",
    hours: 140, score: 4, comments: 0, views: 310, query: "slq_3", similarity: 0.8, status: "rejected", touchedHours: 130,
    reason: "About late invoices.",
    angle: "Content-marketing thread from an automated account.",
  },
];

export const POOL: Seed[] = [
  {
    platform: "reddit", where: "freelance", name: "loomandlathe",
    title: "Switching from FreshBooks: what did you lose?",
    text: "Thinking about leaving FreshBooks after the latest price change. For those who already switched, what did you miss that you didn't expect to? I mostly invoice and track mileage.",
    hours: 1, score: 31, comments: 14, query: "slq_4", similarity: 0.87, status: "to_reply",
    reason: "A freelancer planning to leave FreshBooks and asking what to watch for.",
    angle: "Be honest about the trade-offs: name what most cheaper tools drop (time tracking, proposals) and say Ledgerly tracks mileage as an expense.",
  },
  {
    platform: "hackernews", where: "kestrel_k",
    title: "Ask HN: What do you use to send invoices as a contractor?",
    text: "Billing two clients monthly, one in GBP. Currently writing them in Pages. Looking for something that remembers rates and does the currency maths.",
    hours: 2, score: 44, comments: 37, query: "slq_1", similarity: 0.9, status: "to_reply",
    reason: "A contractor asking what to use for monthly invoices in two currencies.",
    angle: "Answer with what matters for two clients: saved rates, recurring invoices and multi-currency. Name a couple of tools, ours included.",
  },
  {
    platform: "x", where: "maribuilds", name: "Mari Torres",
    title: null,
    text: "Client paid 62 days late and is now annoyed I added the late fee that's literally in the contract they signed. Am I wrong here?",
    hours: 1, score: 205, comments: 88, views: 11200, query: "slq_3", similarity: 0.85, status: "to_reply",
    reason: "A freelancer asking whether charging a contractual late fee was fair.",
    angle: "Back her up: the fee was agreed in writing. Suggest a calm one-line reply to the client that points at the clause.",
  },
  {
    platform: "linkedin", where: "priya-n", name: "Priya Nair",
    title: null,
    text: "Year two of freelancing and I still don't know how much to set aside each month for tax. 25%? 30%? Does anyone have a method that isn't a guess?",
    hours: 3, score: 72, comments: 41, query: "slq_2", similarity: 0.88, status: "to_reply",
    reason: "A second-year freelancer asking for a reliable way to set aside tax money.",
    angle: "Give a method: last year's effective rate plus self-employment tax, set aside from every payment. Mention the tax estimate as a way to do this automatically.",
  },
  {
    platform: "reddit", where: "webdev", name: "pixel_pusher_22",
    title: "How do you track client hardware purchases you bill back?",
    text: "Bought a test phone for a client project on my personal card, need to bill it back and also not double-count it as my expense. How do you all handle reimbursables?",
    hours: 2, score: 18, comments: 9, query: "slq_5", similarity: 0.83, status: "to_reply",
    reason: "A developer asking how to handle expenses billed back to a client.",
    angle: "Explain reimbursable expenses: record it as an expense and as a line on the invoice so the two cancel out at tax time.",
  },
];

let seq = 0;

export function postFrom(s: Seed, runId: string, at?: number): SocialListeningPost {
  seq += 1;
  const n = seq;
  const slug = (s.title ?? s.text).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 48);
  const ext =
    s.platform === "reddit" ? `1h${(n * 7919).toString(36)}`
    : s.platform === "hackernews" ? String(41870000 + n * 1373)
    : s.platform === "x" ? `18462${String(10000000000000 + n * 99991)}`
    : `738${String(2000000000000000 + n * 104729)}`;
  const url =
    s.platform === "reddit" ? `https://www.reddit.com/r/${s.where}/comments/${ext}/${slug}/`
    : s.platform === "hackernews" ? `https://news.ycombinator.com/item?id=${ext}`
    : s.platform === "x" ? `https://x.com/${s.where}/status/${ext}`
    : `https://www.linkedin.com/posts/${s.where}_activity-${ext}`;
  const posted = at !== undefined ? new Date(at - s.hours * HOUR).toISOString() : ago(s.hours * HOUR);
  const touched = at !== undefined ? new Date(at).toISOString() : ago((s.touchedHours ?? Math.max(0.5, s.hours - 0.2)) * HOUR);
  return {
    id: `slp_${n}`,
    createdAt: touched,
    updatedAt: touched,
    siteId: SITE_ID,
    postId: `spost_${n}`,
    url,
    platform: s.platform,
    externalId: ext,
    title: s.title,
    text: s.text,
    authorHandle: s.platform === "linkedin" ? null : s.platform === "reddit" ? (s.name ?? null) : s.where,
    authorName: s.name ?? (s.platform === "hackernews" ? s.where : null),
    postedAt: posted,
    engagement: { score: s.score, comments: s.comments, views: s.views ?? null },
    context: { subreddit: s.platform === "reddit" ? s.where : null, tags: null },
    status: s.status,
    similarity: s.similarity,
    keepReason: s.reason,
    suggestedAngle: s.angle,
    replyText: s.reply ?? null,
    repliedAt: s.status === "replied" ? touched : null,
    queryId: s.query,
    runId,
  };
}

export const POSTS: SocialListeningPost[] = SEEDS.map((s) => postFrom(s, s.hours < 9 ? "slr_13" : "slr_12"));
