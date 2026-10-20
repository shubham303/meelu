import type { Lead, LeadBrief, LeadRun, LeadSource, LeadStatus } from "@demo/lib/types";
import { ago, DAY, HOUR } from "../rand";
import { SITE_ID } from "./site";

export const BRIEFS: LeadBrief[] = [
  {
    id: "lb_1",
    createdAt: ago(9 * DAY),
    updatedAt: ago(2 * DAY),
    siteId: SITE_ID,
    text: "Freelance designers and developers who say they are tired of chasing late invoices",
    enabled: true,
    source: "user",
    sources: ["posts", "linkedin"],
    plan: {
      keywords: ["client still hasn't paid invoice", "chasing late payments freelance", "net 30 never paid"],
      linkedin: { query: "freelance designer", titles: ["Freelance Designer", "Independent Developer"], locations: ["United States", "United Kingdom"] },
    },
    found: 214,
    kept: 23,
  },
  {
    id: "lb_2",
    createdAt: ago(9 * DAY),
    updatedAt: ago(9 * DAY),
    siteId: SITE_ID,
    text: "Solo consultants who are switching away from QuickBooks or FreshBooks",
    enabled: true,
    source: "suggested",
    sources: ["posts", "web"],
    plan: { keywords: ["leaving quickbooks", "freshbooks too expensive", "quickbooks alternative for consultants"] },
    found: 131,
    kept: 14,
  },
  {
    id: "lb_3",
    createdAt: ago(6 * DAY),
    updatedAt: ago(6 * DAY),
    siteId: SITE_ID,
    text: "Accountants who serve freelancers and look for a simple app to recommend to clients",
    enabled: false,
    source: "suggested",
    sources: ["linkedin", "web"],
    plan: {
      linkedin: { query: "accountant freelancers", titles: ["CPA", "Bookkeeper", "Accountant"], locations: ["United States"] },
    },
    found: 58,
    kept: 6,
  },
];

export interface LeadSeed {
  brief: string;
  source: LeadSource;
  platform: string;
  name: string;
  handle?: string;
  headline?: string;
  email?: string;
  website?: string;
  url: string;
  quote: string;
  hours: number;
  reason: string;
  angle: string;
}

const SEEDS: LeadSeed[] = [
  {
    brief: "lb_1",
    source: "posts",
    platform: "reddit",
    name: "Priya N.",
    handle: "pixelpriya",
    headline: "Brand designer, 6 years freelance",
    url: "https://www.reddit.com/r/freelance/comments/1g8x2kq/",
    quote: "Third client this quarter on 60+ days. I spend Friday afternoons writing polite 'just following up' emails instead of designing.",
    hours: 5,
    reason: "Describes the exact problem in her own words this week and asks how others automate reminders.",
    angle: "Ask which reminder wording she has tried; share the three-day-after-due nudge that works for most freelancers.",
  },
  {
    brief: "lb_1",
    source: "linkedin",
    platform: "linkedin",
    name: "Marcus Webb",
    headline: "Independent iOS developer · ex-Spotify",
    url: "https://www.linkedin.com/in/marcuswebb-dev/",
    quote: "Posted: 'Freelancing tip nobody tells you: your invoicing system is part of your product.' 48 reactions.",
    hours: 30,
    reason: "Went freelance four months ago and posts weekly about the business side; recent post is about invoicing.",
    angle: "Comment on his invoicing post first; he is building in public and replies to people who add something.",
  },
  {
    brief: "lb_1",
    source: "posts",
    platform: "x",
    name: "Lena Okafor",
    handle: "lenamakes",
    headline: "Webflow developer for SaaS startups",
    website: "https://lenaokafor.design",
    url: "https://x.com/lenamakes/status/1847722015533",
    quote: "Hot take: 'net 30' is a polite way of saying 'net whenever we feel like it'. Switching every client to due-on-receipt.",
    hours: 11,
    reason: "Changing her payment terms right now, so the moment to look at how she invoices is this week.",
    angle: "Ask how clients reacted to due-on-receipt; mention deposits as the other half of the fix.",
  },
  {
    brief: "lb_2",
    source: "posts",
    platform: "reddit",
    name: "Daniel Ruiz",
    handle: "druiz_strategy",
    headline: "Operations consultant, solo",
    url: "https://www.reddit.com/r/smallbusiness/comments/1g7rq0c/",
    quote: "QuickBooks just went up again. I send maybe 8 invoices a month. What are other one-person consultancies using?",
    hours: 19,
    reason: "Asking for an alternative by name, sends a small number of invoices — the plan Ledgerly fits best.",
    angle: "Answer his question honestly with two or three options; he asked for a list, not a pitch.",
  },
  {
    brief: "lb_2",
    source: "web",
    platform: "web",
    name: "Hollis & Grey Advisory",
    email: "hello@hollisgrey.co",
    website: "https://hollisgrey.co",
    url: "https://hollisgrey.co/blog/our-tool-stack-2026",
    quote: "We are reviewing our finance stack this quarter — FreshBooks has served us, but the per-client pricing no longer makes sense.",
    hours: 52,
    reason: "Two-partner consultancy publicly reviewing its finance tools this quarter; email printed on the contact page.",
    angle: "Reference their tool-stack post and offer the FreshBooks import, nothing more.",
  },
  {
    brief: "lb_1",
    source: "posts",
    platform: "bluesky",
    name: "Tomás Varga",
    handle: "tomasv.bsky.social",
    headline: "Motion designer",
    url: "https://bsky.app/profile/tomasv.bsky.social/post/3l6xk2",
    quote: "Spent 40 minutes reconciling which invoices were actually paid. There has to be a better way than a spreadsheet.",
    hours: 7,
    reason: "Tracks invoices in a spreadsheet and says it is costing him time — a clear, current pain.",
    angle: "Share a quick way to see paid vs unpaid at a glance; ask what his spreadsheet tracks today.",
  },
  {
    brief: "lb_2",
    source: "posts",
    platform: "hackernews",
    name: "kvogel",
    handle: "kvogel",
    headline: "Fractional CTO",
    url: "https://news.ycombinator.com/item?id=41890233",
    quote: "Ask HN: What do solo consultants use for invoicing that isn't QuickBooks?",
    hours: 26,
    reason: "Started an Ask HN on the exact question; 63 comments so far and still active.",
    angle: "Reply in the thread with a real comparison; disclose that you work on Ledgerly.",
  },
  {
    brief: "lb_1",
    source: "linkedin",
    platform: "linkedin",
    name: "Aisha Rahman",
    headline: "Freelance UX researcher · London",
    url: "https://www.linkedin.com/in/aisharahman-ux/",
    quote: "Shared: 'The admin side of freelancing nobody warns you about' — late payments listed first.",
    hours: 70,
    reason: "Writes about freelance admin pain; invoices UK and US clients, so multi-currency matters to her.",
    angle: "Ask how she handles GBP and USD invoices today — that is where most tools fall short.",
  },
  {
    brief: "lb_1",
    source: "posts",
    platform: "devto",
    name: "Jonah Park",
    handle: "jonahcodes",
    headline: "Freelance full-stack developer",
    url: "https://dev.to/jonahcodes/i-built-my-own-invoicing-script-and-regret-it-2k4f",
    quote: "I built my own invoicing script in a weekend. Two years later it is the most fragile code I maintain.",
    hours: 40,
    reason: "Wrote a whole post on why his home-made invoicing tool is a burden; the comments ask what to use instead.",
    angle: "Thank him for the honest post; ask what he would need to retire the script.",
  },
  {
    brief: "lb_2",
    source: "web",
    platform: "web",
    name: "Brightline Consulting",
    email: "ops@brightline-consulting.com",
    website: "https://brightline-consulting.com",
    url: "https://brightline-consulting.com/careers/ops-manager",
    quote: "Job post: 'Help us move off QuickBooks Online to a simpler invoicing setup in your first 90 days.'",
    hours: 96,
    reason: "Hiring someone whose first project is replacing QuickBooks — a dated but concrete buying signal.",
    angle: "Write to the ops address with a one-line offer to help with the migration checklist.",
  },
];

const POOL_SEEDS: LeadSeed[] = [
  {
    brief: "lb_1",
    source: "posts",
    platform: "reddit",
    name: "Sam Ortega",
    handle: "samortega_ill",
    headline: "Freelance illustrator",
    url: "https://www.reddit.com/r/Illustration/comments/1g9a1bz/",
    quote: "Client says the invoice 'got lost'. Second time. How do you all make invoices impossible to lose?",
    hours: 1,
    reason: "Posted an hour ago about a lost invoice, the second time with the same client.",
    angle: "Suggest read receipts on invoices and a reminder that goes out on its own.",
  },
  {
    brief: "lb_2",
    source: "posts",
    platform: "x",
    name: "Rina Patel",
    handle: "rinapatelco",
    headline: "Marketing consultant",
    url: "https://x.com/rinapatelco/status/1847901122031",
    quote: "Finally cancelling FreshBooks. Any recs for something simpler? I invoice 5 clients a month.",
    hours: 2,
    reason: "Cancelling FreshBooks today and asking for recommendations; five clients a month.",
    angle: "Reply with two honest options and the one question that decides between them.",
  },
  {
    brief: "lb_1",
    source: "linkedin",
    platform: "linkedin",
    name: "Owen Mitchell",
    headline: "Independent Shopify developer",
    url: "https://www.linkedin.com/in/owenmitchell-shopify/",
    quote: "Posted: 'Started charging a 50% deposit. Late payments dropped to zero.' 112 reactions.",
    hours: 3,
    reason: "Shares what fixed late payments for him; his audience is other freelance developers.",
    angle: "Add a useful comment about deposits on recurring work; connect afterwards.",
  },
];

function leadFrom(s: LeadSeed, i: number, status: LeadStatus, runId: string, at = Date.now() - s.hours * HOUR): Lead {
  const when = new Date(at).toISOString();
  return {
    id: `ld_${i}`,
    createdAt: when,
    updatedAt: when,
    siteId: SITE_ID,
    briefId: s.brief,
    runId,
    source: s.source,
    platform: s.platform,
    name: s.name,
    handle: s.handle ?? null,
    headline: s.headline ?? null,
    profileUrl:
      s.source === "web"
        ? (s.website ?? null)
        : s.platform === "linkedin"
          ? s.url
          : s.handle
            ? s.platform === "reddit"
              ? `https://www.reddit.com/user/${s.handle}`
              : s.platform === "x"
                ? `https://x.com/${s.handle}`
                : null
            : null,
    email: s.email ?? null,
    emailSourceUrl: s.email ? `${s.website}/contact` : null,
    website: s.website ?? null,
    snippet: s.quote,
    evidence: [{ url: s.url, quote: s.quote, at: when }],
    reason: s.reason,
    angle: s.angle,
    status,
    contactedAt: null,
    discardedAt: null,
  };
}

const CONTACTED: LeadSeed[] = [
  {
    brief: "lb_1",
    source: "posts",
    platform: "reddit",
    name: "Georgia Lin",
    handle: "georgialin_photo",
    headline: "Wedding photographer",
    url: "https://www.reddit.com/r/WeddingPhotography/comments/1g2kq9x/",
    quote: "How do you collect the final balance before delivering the gallery?",
    hours: 6 * 24,
    reason: "Asked how to collect balances before delivery.",
    angle: "Shared the deposit-then-balance setup.",
  },
  {
    brief: "lb_2",
    source: "web",
    platform: "web",
    name: "Northwind Strategy",
    email: "team@northwindstrategy.com",
    website: "https://northwindstrategy.com",
    url: "https://northwindstrategy.com/notes/finance-stack",
    quote: "We are moving off QuickBooks in November.",
    hours: 8 * 24,
    reason: "Announced a QuickBooks migration date.",
    angle: "Offered the import checklist.",
  },
  {
    brief: "lb_1",
    source: "linkedin",
    platform: "linkedin",
    name: "Felix Andersson",
    headline: "Freelance product designer · Stockholm",
    url: "https://www.linkedin.com/in/felixandersson-design/",
    quote: "Posted about invoicing EU clients in three currencies.",
    hours: 5 * 24,
    reason: "Invoices in SEK, EUR and USD.",
    angle: "Asked about his currency setup.",
  },
];

const DISCARDED: LeadSeed[] = [
  {
    brief: "lb_2",
    source: "posts",
    platform: "x",
    name: "FinTools Weekly",
    handle: "fintoolsweekly",
    headline: "Newsletter about finance software",
    url: "https://x.com/fintoolsweekly/status/1846002211",
    quote: "Top 10 QuickBooks alternatives for 2026 (thread)",
    hours: 4 * 24,
    reason: "A listicle account, not a buyer.",
    angle: "",
  },
];

export const RUNS: LeadRun[] = [
  {
    id: "lr_2",
    createdAt: ago(5 * HOUR),
    updatedAt: ago(5 * HOUR - 6 * 60_000),
    siteId: SITE_ID,
    status: "done",
    startedAt: ago(5 * HOUR),
    finishedAt: ago(5 * HOUR - 6 * 60_000),
    foundCount: 186,
    shortlistedCount: 31,
    keptCount: 10,
    sourceStats: {
      "posts:reddit": { status: "done", candidates: 64, fromVendor: 41, fromStore: 23 },
      "posts:x": { status: "done", candidates: 38, fromVendor: 38, fromStore: 0 },
      "posts:hackernews": { status: "done", candidates: 12, fromVendor: 0, fromStore: 12 },
      "posts:bluesky": { status: "done", candidates: 9, fromVendor: 9, fromStore: 0 },
      "posts:devto": { status: "done", candidates: 7, fromVendor: 7, fromStore: 0 },
      linkedin: { status: "done", candidates: 41, people: 12 },
      web: { status: "done", candidates: 15 },
    },
    error: null,
  },
];

export const LEADS: Lead[] = [
  ...SEEDS.map((s, i) => leadFrom(s, i + 1, "new", "lr_2")),
  ...CONTACTED.map((s, i) => {
    const l = leadFrom(s, 50 + i, "contacted", "lr_1");
    l.contactedAt = ago((s.hours - 20) * HOUR);
    return l;
  }),
  ...DISCARDED.map((s, i) => {
    const l = leadFrom(s, 80 + i, "discarded", "lr_1");
    l.discardedAt = ago(3 * DAY);
    return l;
  }),
];

export const POOL: LeadSeed[] = POOL_SEEDS;

export function leadFromPool(s: LeadSeed, i: number, runId: string): Lead {
  return leadFrom(s, i, "new", runId, Date.now() - s.hours * HOUR);
}
