import type { ContentPiece, PieceCheck } from "@demo/lib/types";
import type { PieceIssue } from "@/app/demo/dashboard/content/types";
import { ago, DAY, HOUR } from "../rand";
import { pageId, SITE_ID } from "./site";

const MINUTE = 60_000;
const TITLE_MAX = 60;
const META_MIN = 70;
const META_MAX = 160;

export interface PageFieldsInput {
  title: string;
  h1: string;
  metaDescription: string;
  targetKeyword?: string | null;
  bodyMarkdown: string;
}

export function wordCount(markdown: string): number {
  return (markdown.match(/\S+/g) ?? []).length;
}

function firstParagraph(markdown: string): string {
  for (const block of markdown.split(/\n\s*\n/)) {
    const text = block.trim();
    if (text && !/^\s{0,3}#{1,6}\s/.test(text) && !/^\s*!\[/.test(text)) return text;
  }
  return "";
}

function contains(haystack: string, keyword: string): boolean {
  return haystack.toLowerCase().split(/\s+/).join(" ").includes(keyword);
}

function warn(code: string, message: string): PieceCheck {
  return { code, level: "warn", message };
}

export function runChecks(page: PageFieldsInput): PieceCheck[] {
  const checks: PieceCheck[] = [];
  if (page.title.length > TITLE_MAX) {
    checks.push(warn("title_length", `Search results cut titles past about ${TITLE_MAX} characters; this is ${page.title.length}.`));
  }
  if (!page.h1) checks.push(warn("h1_missing", "The page has no H1."));
  const meta = page.metaDescription;
  if (!meta) {
    checks.push(warn("meta_description_missing", "The page has no meta description."));
  } else if (meta.length < META_MIN || meta.length > META_MAX) {
    checks.push(warn("meta_description_length", `A meta description reads best at ${META_MIN}–${META_MAX} characters; this is ${meta.length}.`));
  }
  if (/^#\s+\S/m.test(page.bodyMarkdown)) {
    checks.push(warn("body_h1", "The body has its own H1. The page's H1 is its own field; start the body's headings at H2."));
  }
  const keyword = page.targetKeyword;
  if (keyword) {
    const places: Array<[string, string]> = [
      ["title", page.title],
      ["H1", page.h1],
      ["meta description", meta],
      ["first paragraph", firstParagraph(page.bodyMarkdown)],
    ];
    const missing = places.filter(([, text]) => !contains(text, keyword)).map(([name]) => name);
    if (missing.length) {
      checks.push(warn("keyword_placement", `The target keyword "${keyword}" is missing from the ${missing.join(", ")}.`));
    }
  }
  return checks;
}

const BODY = {
  pillar: `Invoicing for freelancers comes down to three habits: send the invoice the day the work ships, put a real date on it, and remind the client the day after that date passes. Everything else on this page is detail that makes those three habits easier.

We looked at 4,100 invoices sent through Ledgerly in the last twelve months. Invoices sent within 24 hours of delivery were paid a median of 9 days sooner than invoices sent a week later. Nothing else we measured came close.

## What an invoice must include

A client's finance team pays invoices that look like invoices. Leave something off and it goes back to you with a question, and the clock restarts.

- Your name or business name, address and tax number if you have one
- The client's legal name, not the name of the person you work with
- A unique invoice number (see [how to number invoices](/blog/invoice-numbering))
- The issue date and a due date written as a date
- What you did, in lines a stranger could check against the contract
- The total, the currency, and how to pay

## Choose payment terms you will enforce

Net 30 is a habit, not a law. For a new client, 14 days is normal and nobody will blink. For a large company with a fixed payment run, ask which day the run happens and set your due date the day before it.

Our guide to [invoice payment terms](/blog/invoice-payment-terms) covers deposits, milestones and what to write when a client asks for net 60.

## Send it the day the work ships

Every day between delivery and invoice is a day the client's accounts team does not know you exist. Make sending the invoice part of delivering the work: the same email, or the next one.

## Remind once, early, and kindly

The first reminder should go out the day after the due date. Not because the client is late — they may not have seen it — but because a reminder a day late reads as organised, and a reminder a month late reads as desperate.

If a client is properly late, [what to do about late-paying clients](/blog/late-paying-clients) walks through the second and third messages, and when a [late fee](/blog/late-fee-invoice) is worth adding.

## Recurring and multi-currency work

Retainers should be [recurring invoices](/blog/recurring-invoices) that go out on the same day every month without you touching them. If you bill clients abroad, invoice in their currency and record the payout in yours; [multi-currency invoicing](/blog/multi-currency-invoicing) explains how to handle the gap.

## Keep the records your accountant will ask for

Every invoice you send is income you will have to report. Keep the PDF, mark it paid on the day the money lands, and match it to the bank deposit. Ledgerly does that matching for you when your bank feed is connected, which is most of what [invoicing in Ledgerly](/features/invoicing) is for.`,

  freshbooks: `Ledgerly and FreshBooks both send invoices, track expenses and get you ready for tax season. The difference is who they are built for: FreshBooks grew into a small-business suite with payroll and team seats, while Ledgerly stays a one-person tool and charges like one.

## The short answer

Pick FreshBooks if you employ people or plan to this year. Pick Ledgerly if you work alone, bill a handful of clients and want your books done in ten minutes a week.

## Pricing

| | Ledgerly | FreshBooks Lite |
|---|---|---|
| Monthly price | $12 | $19 |
| Billable clients | Unlimited | 5 |
| Bank feeds | Included | Included |
| Payment reminders | Included | Included |
| Mileage tracking | Included | Plus plan only |

FreshBooks discounts the first months heavily, so compare the price you will pay in month seven, not month one.

## Invoicing

Both send branded invoices, accept card payments through Stripe and send reminders. FreshBooks lets a client log in to a portal and see every invoice; Ledgerly sends a plain link per invoice. If your clients are agencies that want a portal, that matters. If they are people, it does not.

## Expenses and receipts

Ledgerly matches a receipt photo to the bank transaction it belongs to, which is the part of bookkeeping most freelancers skip. FreshBooks does the same on its Plus plan.

## Taxes

Ledgerly shows a quarterly estimate based on what you actually earned. FreshBooks leaves estimates to your accountant. Neither files for you.

## Moving from FreshBooks

Export your clients and invoices as CSV from FreshBooks, then import both on the [Ledgerly import page](/docs/create-an-invoice). Open invoices keep their numbers, so nothing changes for your clients.`,

  reminders: `Automatic payment reminders let Ledgerly email a client when an invoice is due and again when it is overdue. You choose when each reminder goes, and you can switch them off for any one client.

## Turn reminders on

1. Open **Settings → Invoicing**.
2. Under **Payment reminders**, switch on **Send reminders**.
3. Pick when the first reminder goes: on the due date, or one, three or seven days after it.
4. Add up to two follow-ups if you want them.
5. Save.

Reminders apply to every invoice sent after you save. Invoices you sent before keep the setting they were sent with.

## Edit the wording

Each reminder uses a template you can change under **Settings → Email templates**. Keep the invoice number and the amount in the first line; that is what a finance inbox searches for.

## Turn reminders off for one client

Open the client, choose **Edit**, and untick **Send payment reminders**. Useful for a client who pays on a fixed run and finds reminders noisy.

## What the client sees

A short email from your business name with the invoice number, the amount due, the due date and a link to pay. Ledgerly's name does not appear unless you are on the free plan.

## Troubleshooting

If a reminder did not go out, check that the invoice was **sent** rather than downloaded, and that the client has an email address. Reminders never go to invoices marked paid, even partly.`,

  quarterly: `Quarterly estimated taxes are how freelancers pay income tax during the year when nobody withholds it from their pay. If you expect to owe $1,000 or more for the year, the IRS wants four payments instead of one in April.

## The 2027 due dates

| Covers income earned | Due |
|---|---|
| 1 January – 31 March | 15 April 2027 |
| 1 April – 31 May | 15 June 2027 |
| 1 June – 31 August | 15 September 2027 |
| 1 September – 31 December | 18 January 2028 |

The periods are uneven on purpose. When a date falls on a weekend or holiday, it moves to the next working day.

## How much to pay

The simplest safe route is the safe harbour rule: pay at least 100% of last year's total tax, split into four. If your adjusted gross income last year was over $150,000, make it 110%. Do that and you owe no penalty, however this year turns out.

If your income dropped this year, pay based on this year instead. It is more work, because you have to estimate, but it keeps the cash in your account.

## What happens if you miss one

You owe a penalty that works like interest, currently around 8% a year on the amount you were short, for the days you were short. It is not a disaster, but it is avoidable.

## Paying

Pay through IRS Direct Pay or EFTPS. Keep the confirmation number; you will need the total on your annual return.

## Where Ledgerly helps

Every quarter Ledgerly looks at your income and [deductible expenses](/blog/deductible-expenses-freelancers), applies your bracket and shows the number to pay. You still make the payment yourself. See [taxes in Ledgerly](/features/tax).`,

  lateFees: `# Late fees: what is allowed and what works

A late fee is only worth adding if it is in your contract before the work starts and on the invoice before it is overdue. Added afterwards, it reads as a threat, and most clients will simply not pay it.

## Is a late fee legal?

In most US states, yes, if the client agreed to it in advance. Many states cap the rate; 1.5% a month is common and safe almost everywhere. In the UK, the Late Payment of Commercial Debts Act lets you charge 8% above the Bank of England base rate on business-to-business invoices, even without a clause.

## Fixed fee or interest?

A fixed fee — $25, say — is easier to explain and easier to waive. Monthly interest scales with the invoice, which matters on a $9,000 project and looks petty on a $300 one.

## Does it get you paid faster?

Barely. In our data, invoices with a late-fee line were paid a median of two days sooner than those without. A reminder the day after the due date did more than four times as much.

## How to word it

Put one line under the total: "Payments received after 14 November 2026 incur a fee of 1.5% per month." Keep it plain and it does its job without sounding hostile.

If a client is already late, read [what to do about late-paying clients](/blog/late-paying-clients) before you reach for the fee.`,

  photographers: `Photographers bill in a way most accounting tools were not built for: a deposit to hold the date, a balance after the shoot, a print order three weeks later, and mileage to a venue two hours away.

## Deposits that hold the date

Send a deposit invoice from the booking itself. When the shoot is done, Ledgerly turns the rest into the balance invoice and shows the deposit already paid, so the client never sees the full amount twice.

## Mileage without a logbook

Turn on [mileage tracking](/features/mileage) and Ledgerly records drives to client locations from your phone. At tax time the total is already in your deductible expenses.

## Gear is an expense, not a mystery

Lenses, bodies and lighting go in as equipment, so your accountant can depreciate them properly instead of you guessing.`,

  mileage: `A mileage log is a record of every business drive: the date, where you went, why, and how far. The IRS asks for one if you claim vehicle costs, and "about 400 miles a month" is not a log.

## What to record

- Date of the drive
- Start and end point
- Business purpose
- Miles driven

TODO: add the template download and the 2027 standard rate once it is announced.`,
};

const UNSPLASH = {
  desk: {
    mediaUrl: "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80",
    mediaAlt: "A wooden desk with a laptop, a calculator and a stack of paper invoices",
    mediaWidth: 1200,
    mediaHeight: 800,
    mediaCreditName: "Kelly Sikkema",
    mediaCreditUrl: "https://unsplash.com/@kellysikkema",
  },
  camera: {
    mediaUrl: "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=1200&q=80",
    mediaAlt: "A photographer holding a mirrorless camera at a shoot",
    mediaWidth: 1200,
    mediaHeight: 800,
    mediaCreditName: "Alexander Andrews",
    mediaCreditUrl: "https://unsplash.com/@alex_andrews",
  },
};

interface Seed {
  id: string;
  title: string;
  h1: string;
  metaDescription: string;
  slug: string | null;
  targetKeyword: string | null;
  bodyMarkdown: string;
  createdBy: "agent" | "user";
  createdAt: string;
  updatedAt: string;
  sourcePageId?: string | null;
  media?: (typeof UNSPLASH)["desk"];
}

export function buildPiece(seed: Seed): ContentPiece {
  return {
    id: seed.id,
    siteId: SITE_ID,
    createdAt: seed.createdAt,
    updatedAt: seed.updatedAt,
    title: seed.title,
    h1: seed.h1,
    metaDescription: seed.metaDescription,
    slug: seed.slug,
    targetKeyword: seed.targetKeyword,
    bodyMarkdown: seed.bodyMarkdown,
    wordCount: wordCount(seed.bodyMarkdown),
    checks: runChecks(seed),
    createdBy: seed.createdBy,
    sourcePageId: seed.sourcePageId ?? null,
    mediaSource: seed.media ? "unsplash" : "none",
    mediaUrl: seed.media?.mediaUrl ?? null,
    mediaAlt: seed.media?.mediaAlt ?? null,
    mediaWidth: seed.media?.mediaWidth ?? null,
    mediaHeight: seed.media?.mediaHeight ?? null,
    mediaCreditName: seed.media?.mediaCreditName ?? null,
    mediaCreditUrl: seed.media?.mediaCreditUrl ?? null,
    mediaUploadId: null,
  };
}

export const PIECES: ContentPiece[] = [
  buildPiece({
    id: "pc_pillar",
    title: "Invoicing for freelancers: the complete guide",
    h1: "Invoicing for freelancers: how to get paid on time",
    metaDescription: "Invoicing for freelancers in three habits: send it the day the work ships, put a real date on it, and remind the day after. What 4,100 invoices showed.",
    slug: "/guides/invoicing-for-freelancers",
    targetKeyword: "invoicing for freelancers",
    bodyMarkdown: BODY.pillar,
    createdBy: "agent",
    createdAt: ago(3 * DAY),
    updatedAt: ago(38 * MINUTE),
    sourcePageId: pageId("/blog/how-to-invoice-as-a-freelancer"),
    media: UNSPLASH.desk,
  }),
  buildPiece({
    id: "pc_freshbooks",
    title: "Ledgerly vs FreshBooks: which is better for a one-person business in 2027?",
    h1: "Ledgerly vs FreshBooks",
    metaDescription: "Ledgerly vs FreshBooks for freelancers: pricing, invoicing, expenses and taxes compared, and which one fits a one-person business.",
    slug: "/compare/freshbooks",
    targetKeyword: "ledgerly vs freshbooks",
    bodyMarkdown: BODY.freshbooks,
    createdBy: "agent",
    createdAt: ago(5 * DAY),
    updatedAt: ago(4 * HOUR),
    sourcePageId: pageId("/compare/freshbooks"),
  }),
  buildPiece({
    id: "pc_reminders",
    title: "Set up automatic payment reminders | Ledgerly Help",
    h1: "Set up automatic payment reminders",
    metaDescription: "Turn on automatic payment reminders in Ledgerly, choose when they go out, edit the wording and switch them off for one client.",
    slug: "/docs/payment-reminders",
    targetKeyword: "automatic payment reminders",
    bodyMarkdown: BODY.reminders,
    createdBy: "user",
    createdAt: ago(9 * DAY),
    updatedAt: ago(DAY + 3 * HOUR),
    sourcePageId: pageId("/docs/payment-reminders"),
  }),
  buildPiece({
    id: "pc_quarterly",
    title: "Quarterly estimated taxes: 2027 due dates",
    h1: "Quarterly estimated taxes for freelancers: 2027 dates and how much to pay",
    metaDescription: "The 2027 quarterly estimated tax dates.",
    slug: "/blog/quarterly-estimated-taxes-2027",
    targetKeyword: "quarterly estimated taxes",
    bodyMarkdown: BODY.quarterly,
    createdBy: "agent",
    createdAt: ago(2 * DAY),
    updatedAt: ago(6 * HOUR),
    sourcePageId: pageId("/blog/quarterly-estimated-taxes-explained"),
  }),
  buildPiece({
    id: "pc_late_fees",
    title: "Late fees on invoices: what is legal and what works",
    h1: "Late fees on invoices",
    metaDescription: "Can a freelancer charge a late fee? What US and UK rules allow, fixed fee or interest, how to word it, and whether it actually gets you paid sooner.",
    slug: "/blog/late-fee-on-invoices",
    targetKeyword: "late fees on invoices",
    bodyMarkdown: BODY.lateFees,
    createdBy: "agent",
    createdAt: ago(6 * DAY),
    updatedAt: ago(2 * DAY),
    sourcePageId: pageId("/blog/late-fee-invoice"),
  }),
  buildPiece({
    id: "pc_photographers",
    title: "Bookkeeping for photographers | Ledgerly",
    h1: "Bookkeeping for photographers",
    metaDescription: "",
    slug: "/for/photographers",
    targetKeyword: "bookkeeping for photographers",
    bodyMarkdown: BODY.photographers,
    createdBy: "agent",
    createdAt: ago(DAY),
    updatedAt: ago(19 * HOUR),
    media: UNSPLASH.camera,
  }),
  buildPiece({
    id: "pc_mileage",
    title: "Mileage log template",
    h1: "",
    metaDescription: "",
    slug: null,
    targetKeyword: null,
    bodyMarkdown: BODY.mileage,
    createdBy: "user",
    createdAt: ago(12 * DAY),
    updatedAt: ago(11 * DAY),
  }),
];

let issueSeq = 0;
export function nextIssueId(): string {
  issueSeq += 1;
  return `cpi_${(1000 + issueSeq).toString(36)}`;
}

function issue(
  pieceId: string,
  runId: string,
  at: string,
  tool: string,
  code: string,
  title: string,
  rest: Partial<Pick<PieceIssue, "detail" | "anchorText" | "suggestion" | "state">> = {},
): PieceIssue {
  return {
    id: nextIssueId(),
    pieceId,
    tool,
    code,
    title,
    detail: rest.detail ?? null,
    anchorText: rest.anchorText ?? null,
    suggestion: rest.suggestion ?? null,
    state: rest.state ?? "open",
    runId,
    createdAt: at,
    updatedAt: rest.state && rest.state !== "open" ? ago(20 * MINUTE) : at,
  };
}

const PILLAR_RUN = ago(52 * MINUTE);
const FRESHBOOKS_RUN = ago(5 * HOUR);
const QUARTERLY_RUN = ago(7 * HOUR);
const LATE_RUN = ago(2 * DAY + HOUR);

export const ISSUES: PieceIssue[] = [
  issue("pc_pillar", "run_pillar_read", PILLAR_RUN, "readability", "long_sentence", "Long sentence, 35 words", {
    detail: "Over 25 words. Splitting it costs nothing.",
    anchorText: "Not because the client is late — they may not have seen it — but because a reminder a day late reads as organised, and a reminder a month late reads as desperate.",
  }),
  issue("pc_pillar", "run_pillar_read", PILLAR_RUN, "readability", "passive_voice", "Passive voice", {
    detail: "\"were paid\" hides who did the thing. Check it — this detection is a pattern match, not a parser.",
    anchorText: "Invoices sent within 24 hours of delivery were paid a median of 9 days sooner than invoices sent a week later.",
    state: "dismissed",
  }),
  issue("pc_pillar", "run_pillar_sim", PILLAR_RUN, "similarity", "similar_paragraph", "Paragraph overlaps 64% with Late-paying clients: what to do", {
    detail: "Shared wording: \"The first reminder should go out the day after the due date\". Found on Late-paying clients: what to do (https://ledgerly.app/blog/late-paying-clients). Rephrase the shared sentences or fold in a point that page does not make.",
    anchorText: "The first reminder should go out the day after the due date. Not because the client is late — they may not have seen it — but because a reminder a day late reads as organised, and a reminder a month late reads as desperate.",
  }),
  issue("pc_pillar", "run_pillar_sim", PILLAR_RUN, "similarity", "duplicate_paragraph", "83% of this paragraph already lives on Invoice payment terms", {
    detail: "Shared wording: \"For a new client, 14 days is normal and nobody will blink\". Found on Invoice payment terms (https://ledgerly.app/blog/invoice-payment-terms). Two pages saying the same thing split the ranking between them — rewrite this so it adds something, or link to that page instead.",
    anchorText: "Net 30 is a habit, not a law. For a new client, 14 days is normal and nobody will blink. For a large company with a fixed payment run, ask which day the run happens and set your due date the day before it.",
    state: "fixed",
  }),

  issue("pc_freshbooks", "run_fb_read", FRESHBOOKS_RUN, "readability", "complex_words", "3 long words in one sentence", {
    detail: "FreshBooks, discounts, heavily — most three-syllable words have a shorter twin. This sentence reads at grade 11.",
    anchorText: "FreshBooks discounts the first months heavily, so compare the price you will pay in month seven, not month one.",
    state: "dismissed",
  }),
  issue("pc_freshbooks", "run_fb_rules", FRESHBOOKS_RUN, "page_rules", "marketing_cadence", "Marketing cadence: \"in ten minutes a week\"", {
    detail: "Advertising copy reads as filler on an article. Plain and specific wins.",
    anchorText: "in ten minutes a week",
  }),
  issue("pc_freshbooks", "run_fb_ai", FRESHBOOKS_RUN, "ai_detector", "ai_mixed", "Mixed — 46% (medium confidence)", {
    detail: "Parts read as written by a person and parts as generated. Read the flagged passages back and rewrite the ones that sound like nobody in particular.",
  }),
  issue("pc_freshbooks", "run_fb_ai", FRESHBOOKS_RUN, "ai_detector", "ai_passage", "Passage reads 71% machine-written", {
    detail: "Window 2 of 5, 118 words. The classifier is right about four times in five, so read it back: if it is yours, break the rhythm — a shorter sentence, a concrete detail, an opinion.",
    anchorText: "Both send branded invoices, accept card payments through Stripe and send reminders. FreshBooks lets a client log in to a portal and see every invoice; Ledgerly sends a plain link per invoice.",
  }),

  issue("pc_quarterly", "run_q_read", QUARTERLY_RUN, "readability", "long_sentence", "Long sentence, 26 words", {
    detail: "Over 25 words. Splitting it costs nothing.",
    anchorText: "You owe a penalty that works like interest, currently around 8% a year on the amount you were short, for the days you were short.",
  }),
  issue("pc_quarterly", "run_q_sim", QUARTERLY_RUN, "similarity", "duplicate_paragraph", "88% of this paragraph already lives on Quarterly estimated taxes, explained", {
    detail: "Shared wording: \"pay at least 100% of last year's total tax, split into four\". Found on Quarterly estimated taxes, explained (https://ledgerly.app/blog/quarterly-estimated-taxes-explained). Two pages saying the same thing split the ranking between them — rewrite this so it adds something, or link to that page instead.",
    anchorText: "The simplest safe route is the safe harbour rule: pay at least 100% of last year's total tax, split into four. If your adjusted gross income last year was over $150,000, make it 110%. Do that and you owe no penalty, however this year turns out.",
  }),
  issue("pc_quarterly", "run_q_rules", QUARTERLY_RUN, "page_rules", "llm_tells", "Reads as machine-written: \"It is not a disaster, but it is avoidable\"", {
    detail: "These phrases are the tells readers have learned to skip. Say the specific thing instead.",
    anchorText: "It is not a disaster, but it is avoidable.",
    state: "fixed",
  }),

  issue("pc_late_fees", "run_lf_read", LATE_RUN, "readability", "long_sentence", "Long sentence, 26 words", {
    detail: "Over 25 words. Splitting it costs nothing.",
    anchorText: "A late fee is only worth adding if it is in your contract before the work starts and on the invoice before it is overdue.",
    state: "fixed",
  }),
  issue("pc_late_fees", "run_lf_rules", LATE_RUN, "page_rules", "wall_of_text", "A paragraph runs 236 characters", {
    detail: "Short paragraphs, one idea each. Break this one up.",
    anchorText: "In most US states, yes, if the client agreed to it in advance. Many states cap the rate; 1.5% a month is common and safe almost everywhere. In the UK, the Late Payment of Commercial Debts Act lets you charge 8% above the Bank of England base rate on business-to-business invoices, even without a clause.",
    state: "dismissed",
  }),
];
