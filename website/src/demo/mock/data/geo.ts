import type { GeoAiAnswer, GeoCheck, GeoIntent, GeoPage, GeoPointStatus, GeoQuery, GeoVerdict } from "@demo/lib/types";
import { ago, DAY, HOUR } from "../rand";
import { ORIGIN, PAGE_BY_PATH, pageId, SITE_ID } from "./site";

interface PageSeed {
  path: string;
  coverage: number;
  points: Array<[GeoPointStatus, string?]>;
}

interface AnswerSeed {
  platform: GeoAiAnswer["platform"];
  citedUs: boolean;
  covers: string[];
  misses: string[];
  text: string;
  citations: Array<[string, string]>;
  shown?: boolean;
}

export interface GeoSeed {
  id: string;
  text: string;
  source: "user" | "suggested";
  checkedDaysAgo: number | null;
  intent: GeoIntent;
  verdict: GeoVerdict;
  points: string[];
  pages: PageSeed[];
  position?: number;
  answers: AnswerSeed[];
  pageAdds: string[];
  suggestion: string;
}

const CITE = {
  nerdwallet: ["https://www.nerdwallet.com/article/small-business/best-invoicing-software", "Best Invoicing Software of 2026 — NerdWallet"],
  irs: ["https://www.irs.gov/businesses/small-businesses-self-employed/estimated-taxes", "Estimated Taxes | Internal Revenue Service"],
  reddit: ["https://www.reddit.com/r/freelance/comments/1f2c9ab/", "r/freelance — what do you use for invoicing?"],
  freshbooks: ["https://www.freshbooks.com/hub/invoicing/late-payment", "How to Ask for Payment Politely — FreshBooks"],
  forbes: ["https://www.forbes.com/advisor/business/software/best-accounting-software-freelancers/", "Best Accounting Software for Freelancers — Forbes Advisor"],
  quickbooks: ["https://quickbooks.intuit.com/r/invoicing/late-fee/", "How to Charge a Late Fee — QuickBooks"],
  ledgerlyTaxes: [`${ORIGIN}/blog/quarterly-estimated-taxes-explained`, "Quarterly estimated taxes, explained — Ledgerly"],
  ledgerlyCompare: [`${ORIGIN}/compare/quickbooks`, "Ledgerly vs QuickBooks — Ledgerly"],
  ledgerlyLate: [`${ORIGIN}/blog/late-paying-clients`, "What to do about late-paying clients — Ledgerly"],
  wise: ["https://wise.com/us/blog/invoice-in-foreign-currency", "How to invoice in a foreign currency — Wise"],
} as const;

export const SEEDS: GeoSeed[] = [
  {
    id: "gq_1",
    text: "What is the best invoicing app for a freelancer who bills 5–10 clients a month?",
    source: "user",
    checkedDaysAgo: 2,
    intent: "commercial",
    verdict: "partial",
    points: [
      "Names specific apps and who each suits",
      "Compares price at 5–10 clients a month",
      "Covers recurring invoices and reminders",
      "Mentions bank feeds or payment links",
      "Says when a spreadsheet is enough",
    ],
    pages: [
      {
        path: "/blog/best-bookkeeping-software-freelancers",
        coverage: 0.6,
        points: [
          ["answers", "We compared Ledgerly, Wave, FreshBooks and QuickBooks Self-Employed on the four things freelancers ask about most."],
          ["missing"],
          ["answers", "Recurring invoices and automatic reminders are included on every plan."],
          ["partly", "Ledgerly connects to your bank so payments match invoices on their own."],
          ["missing"],
        ],
      },
      { path: "/for/freelancers", coverage: 0.4, points: [["partly"], ["missing"], ["answers"], ["answers"], ["missing"]] },
    ],
    position: 7.4,
    answers: [
      {
        platform: "chat_gpt",
        citedUs: false,
        covers: ["Names specific apps", "Compares price", "Covers reminders"],
        misses: ["Says when a spreadsheet is enough"],
        text: "For a freelancer billing 5–10 clients a month, the most common picks are:\n\n• FreshBooks — polished, strong on time tracking, but the per-client tiers add up.\n• Wave — free invoicing, paid payments; good if you rarely need support.\n• Bonsai — bundles contracts and proposals.\n• Ledgerly — flat price, bank feeds and reminders included.\n\nAt this volume, price per month and automatic reminders matter more than advanced accounting.",
        citations: [[...CITE.nerdwallet], [...CITE.forbes], [...CITE.reddit]],
      },
      {
        platform: "claude",
        citedUs: false,
        covers: ["Names specific apps", "Covers reminders", "Says when a spreadsheet is enough"],
        misses: ["Compares price"],
        text: "If you bill under ten clients, start by asking whether you need software at all: a template and a reminder calendar can work. Once you want reminders and payment links, Wave, FreshBooks and Ledgerly are the usual choices…",
        citations: [[...CITE.forbes]],
      },
      {
        platform: "ai_overview",
        citedUs: false,
        covers: ["Names specific apps", "Compares price"],
        misses: ["Covers recurring invoices and reminders", "Says when a spreadsheet is enough"],
        text: "Popular invoicing apps for freelancers include FreshBooks, Wave, QuickBooks Self-Employed and Zoho Invoice. Pricing ranges from free to $30 per month…",
        citations: [[...CITE.nerdwallet], [...CITE.forbes]],
      },
    ],
    pageAdds: [
      "A side-by-side test of four apps on the same five invoices",
      "Screenshots of the reminder settings in each app",
    ],
    suggestion:
      "Your comparison post is the closest page, but no AI answer cites it. Every answer leads with price at this client count and two say when a spreadsheet is enough; your page does neither. Adding a price table at 5 and 10 clients and a short 'when you don't need an app' section would cover the two missing points. Whether to extend this post or write a new page is your call.",
  },
  {
    id: "gq_2",
    text: "How do I calculate quarterly estimated taxes as a freelancer?",
    source: "suggested",
    checkedDaysAgo: 3,
    intent: "informational",
    verdict: "covered",
    points: [
      "Explains the safe-harbour rule (100% / 110% of last year)",
      "Shows a worked example with numbers",
      "Lists the four due dates",
      "Mentions self-employment tax on top of income tax",
    ],
    pages: [
      {
        path: "/blog/quarterly-estimated-taxes-explained",
        coverage: 1,
        points: [
          ["answers", "Pay at least 100% of last year's tax — 110% if you earned over $150,000 — and you avoid the penalty."],
          ["answers", "Say you expect $80,000 in profit this year…"],
          ["answers", "April 15, June 15, September 15 and January 15."],
          ["answers", "Self-employment tax is 15.3% on 92.35% of your profit."],
        ],
      },
    ],
    position: 3.2,
    answers: [
      {
        platform: "chat_gpt",
        citedUs: true,
        covers: ["Safe-harbour rule", "Four due dates", "Self-employment tax"],
        misses: ["Worked example"],
        text: "To calculate quarterly estimated taxes, estimate your annual profit, add self-employment tax (15.3% on 92.35% of profit) to your income tax, then divide by four. To avoid penalties, pay at least 100% of last year's total tax (110% above $150k AGI)…",
        citations: [[...CITE.irs], [...CITE.ledgerlyTaxes]],
      },
      {
        platform: "claude",
        citedUs: true,
        covers: ["Safe-harbour rule", "Worked example", "Four due dates", "Self-employment tax"],
        misses: [],
        text: "Here's a simple method with an example. Suppose you expect $80,000 in profit…",
        citations: [[...CITE.ledgerlyTaxes], [...CITE.irs]],
      },
      {
        platform: "ai_overview",
        citedUs: false,
        covers: ["Four due dates", "Self-employment tax"],
        misses: ["Worked example"],
        text: "Freelancers generally must pay estimated tax if they expect to owe $1,000 or more. Payments are due April 15, June 15, September 15 and January 15…",
        citations: [[...CITE.irs]],
      },
    ],
    pageAdds: ["A downloadable worksheet", "The 2026 state-by-state due-date table"],
    suggestion:
      "Covered: the page answers every point and ranks around position 3. ChatGPT and Claude both cite it. No change suggested; check again after the January deadline when people ask about the fourth payment.",
  },
  {
    id: "gq_3",
    text: "Can I charge a client a late fee on an unpaid invoice?",
    source: "suggested",
    checkedDaysAgo: 1,
    intent: "informational",
    verdict: "low_rank",
    points: [
      "Says the fee must be agreed in the contract first",
      "Gives a typical rate (1–2% a month)",
      "Mentions state limits on interest",
      "Shows wording to put on the invoice",
    ],
    pages: [
      {
        path: "/blog/late-fee-invoice",
        coverage: 1,
        points: [
          ["answers", "A late fee only holds if your client agreed to it before the work started."],
          ["answers", "Most freelancers charge 1.5% a month on the overdue balance."],
          ["answers", "Several states cap interest; check yours before you set a rate."],
          ["answers", "Payment is due within 14 days. A fee of 1.5% per month applies to balances past due."],
        ],
      },
      { path: "/blog/late-paying-clients", coverage: 0.5, points: [["answers"], ["missing"], ["missing"], ["partly"]] },
    ],
    position: 14.6,
    answers: [
      {
        platform: "chat_gpt",
        citedUs: false,
        covers: ["Agreed in the contract", "Typical rate"],
        misses: ["State limits", "Invoice wording"],
        text: "Yes, if your contract says so. A common late fee is 1–2% per month on the unpaid balance…",
        citations: [[...CITE.quickbooks], [...CITE.freshbooks]],
      },
      {
        platform: "claude",
        citedUs: false,
        covers: ["Agreed in the contract", "Typical rate", "State limits"],
        misses: ["Invoice wording"],
        text: "Generally yes, provided the fee was agreed in advance…",
        citations: [[...CITE.quickbooks]],
      },
      {
        platform: "ai_overview",
        citedUs: false,
        shown: false,
        covers: [],
        misses: [],
        text: "",
        citations: [],
      },
    ],
    pageAdds: ["Ready-to-paste invoice wording", "A link to the late-payment reminder template"],
    suggestion:
      "Your page answers all four points, more completely than the pages AI answers cite, but it sits around position 15 in Search Console, so AI search rarely finds it. This is a ranking problem, not a content one: the SEO desk is where to look at links into the page.",
  },
  {
    id: "gq_4",
    text: "How do I invoice a client in another currency without losing money on fees?",
    source: "suggested",
    checkedDaysAgo: 4,
    intent: "informational",
    verdict: "no_page",
    points: [
      "Explains invoicing in the client's currency vs your own",
      "Compares conversion fees (bank, PayPal, Wise)",
      "Covers how to record the exchange rate for taxes",
      "Mentions multi-currency accounts",
    ],
    pages: [{ path: "/features/multi-currency", coverage: 0.25, points: [["partly"], ["missing"], ["missing"], ["partly"]] }],
    answers: [
      {
        platform: "chat_gpt",
        citedUs: false,
        covers: ["Client's currency vs your own", "Compares fees", "Multi-currency accounts"],
        misses: ["Exchange rate for taxes"],
        text: "You have two options: invoice in your own currency and let the client pay conversion, or invoice in theirs and convert yourself…",
        citations: [[...CITE.wise]],
      },
      {
        platform: "claude",
        citedUs: false,
        covers: ["Client's currency vs your own", "Exchange rate for taxes"],
        misses: ["Compares fees"],
        text: "Start by deciding who carries the currency risk…",
        citations: [[...CITE.wise]],
      },
      {
        platform: "ai_overview",
        citedUs: false,
        covers: ["Compares fees", "Multi-currency accounts"],
        misses: ["Exchange rate for taxes"],
        text: "To invoice internationally, consider a multi-currency account such as Wise or Payoneer…",
        citations: [[...CITE.wise]],
      },
    ],
    pageAdds: [],
    suggestion:
      "No page on the site answers this. The multi-currency feature page lists what the product does but not how to choose a currency or record the rate for taxes, which every AI answer treats as the core of the question. A guide on this question is the gap; you decide whether it is worth writing.",
  },
  {
    id: "gq_5",
    text: "Is Ledgerly a good QuickBooks alternative for consultants?",
    source: "user",
    checkedDaysAgo: 2,
    intent: "commercial",
    verdict: "covered",
    points: ["Says who should switch and who should not", "Compares price", "Covers moving data from QuickBooks", "Mentions accountant access"],
    pages: [
      {
        path: "/compare/quickbooks",
        coverage: 0.88,
        points: [
          ["answers", "If you run payroll for staff, stay on QuickBooks."],
          ["answers", "$12 a month, flat, against QuickBooks Simple Start at $35."],
          ["answers", "Import customers, invoices and items from a QuickBooks export in one step."],
          ["partly", "Invite your accountant for free."],
        ],
      },
    ],
    position: 4.1,
    answers: [
      {
        platform: "chat_gpt",
        citedUs: true,
        covers: ["Who should switch", "Compares price", "Moving data"],
        misses: [],
        text: "Ledgerly is aimed at freelancers and small consultancies who mainly need invoicing and expenses…",
        citations: [[...CITE.ledgerlyCompare], [...CITE.reddit]],
      },
      {
        platform: "claude",
        citedUs: true,
        covers: ["Who should switch", "Compares price"],
        misses: ["Accountant access"],
        text: "For a solo consultant, Ledgerly can replace QuickBooks if you don't need payroll…",
        citations: [[...CITE.ledgerlyCompare]],
      },
      {
        platform: "ai_overview",
        citedUs: true,
        covers: ["Compares price", "Moving data"],
        misses: ["Accountant access"],
        text: "Ledgerly is a flat-priced invoicing and bookkeeping app; it imports QuickBooks data…",
        citations: [[...CITE.ledgerlyCompare], [...CITE.forbes]],
      },
    ],
    pageAdds: ["An honest 'who should stay on QuickBooks' section"],
    suggestion: "Covered and cited by all three. One small gap: accountant access is mentioned in passing; a sentence on what your accountant can see would close it.",
  },
  {
    id: "gq_6",
    text: "What should I do when a client hasn't paid after 60 days?",
    source: "suggested",
    checkedDaysAgo: 5,
    intent: "informational",
    verdict: "partial",
    points: [
      "Gives a sequence of reminders with timing",
      "Includes a final-notice template",
      "Covers small-claims court or collections",
      "Says when to pause work",
    ],
    pages: [
      {
        path: "/blog/late-paying-clients",
        coverage: 0.5,
        points: [
          ["answers", "Send a friendly reminder three days after the due date, a firmer one at 14 days, and call at 30."],
          ["missing"],
          ["missing"],
          ["answers", "Stop work on anything new until the overdue invoice is paid."],
        ],
      },
      { path: "/templates/late-payment-reminder", coverage: 0.5, points: [["partly"], ["answers"], ["missing"], ["missing"]] },
    ],
    position: 6.3,
    answers: [
      {
        platform: "chat_gpt",
        citedUs: true,
        covers: ["Reminder sequence", "Small claims", "Pause work"],
        misses: ["Final-notice template"],
        text: "At 60 days, move from reminders to a formal final notice…",
        citations: [[...CITE.ledgerlyLate], [...CITE.freshbooks]],
      },
      {
        platform: "claude",
        citedUs: false,
        covers: ["Final-notice template", "Small claims"],
        misses: ["Pause work"],
        text: "Send a final notice that states the amount, the original due date and a deadline…",
        citations: [[...CITE.freshbooks]],
      },
      {
        platform: "ai_overview",
        citedUs: false,
        covers: ["Reminder sequence", "Small claims"],
        misses: ["Final-notice template"],
        text: "If an invoice remains unpaid after 60 days, consider a formal demand letter, small-claims court or a collection agency…",
        citations: [[...CITE.freshbooks], [...CITE.quickbooks]],
      },
    ],
    pageAdds: ["A real timeline from a Ledgerly customer"],
    suggestion:
      "Two of your pages split this question: the blog post has the timeline, the template page has the final notice, and neither mentions small claims. ChatGPT cites the post. Linking the two pages to each other, or adding the final-notice wording and a short small-claims section to the post, would cover it. Which to do is yours to decide.",
  },
  {
    id: "gq_7",
    text: "Which expenses can a freelance designer deduct?",
    source: "suggested",
    checkedDaysAgo: null,
    intent: "informational",
    verdict: "partial",
    points: [
      "Answers the question in the first paragraph",
      "Gives a concrete example",
      "Lists the common mistakes",
      "Links to a template or tool",
    ],
    pages: [
      {
        path: "/blog/deductible-expenses-freelancers",
        coverage: 0.5,
        points: [["answers", "Anything you buy only for your business is deductible."], ["answers"], ["missing"], ["missing"]],
      },
    ],
    position: 9.8,
    answers: [
      {
        platform: "chat_gpt",
        citedUs: false,
        covers: ["Answers up front", "Concrete example", "Common mistakes"],
        misses: ["Template or tool"],
        text: "Freelancers can typically deduct software, equipment, a home office share, travel and professional fees…",
        citations: [[...CITE.nerdwallet]],
      },
      {
        platform: "claude",
        citedUs: false,
        covers: ["Answers up front", "Common mistakes"],
        misses: ["Concrete example"],
        text: "The general rule: an expense must be ordinary and necessary for your work…",
        citations: [[...CITE.irs]],
      },
      {
        platform: "ai_overview",
        citedUs: false,
        covers: ["Answers up front"],
        misses: ["Common mistakes"],
        text: "Common deductions for self-employed designers include software subscriptions, hardware and a home office…",
        citations: [[...CITE.irs], [...CITE.forbes]],
      },
    ],
    pageAdds: ["A designer-specific list (fonts, stock, plugins)"],
    suggestion:
      "The closest page answers up front and gives an example, but no AI answer cites it, and every answer lists common mistakes that the page leaves out. A short mistakes section is the smallest change that covers the gap; you decide whether to make it.",
  },
  {
    id: "gq_8",
    text: "Should I charge hourly or per project as a freelance developer?",
    source: "user",
    checkedDaysAgo: null,
    intent: "informational",
    verdict: "covered",
    points: [
      "Explains when hourly pricing fits and when project pricing fits",
      "Shows how to turn an hourly rate into a project quote",
      "Covers scope creep and change requests",
      "Mentions retainers as a third option",
    ],
    pages: [
      {
        path: "/blog/hourly-vs-project-pricing",
        coverage: 0.88,
        points: [
          ["answers", "Bill hourly when the scope is unknown; quote per project once you have done the job three times."],
          ["answers", "Estimate the hours, add 25% for the unknowns, multiply by your rate and round up."],
          ["answers", "Write what is out of scope into the quote, and price change requests before you start them."],
          ["partly", "Some clients prefer a monthly retainer."],
        ],
      },
    ],
    position: 5.2,
    answers: [
      {
        platform: "chat_gpt",
        citedUs: true,
        covers: ["When each fits", "Hourly to project quote", "Scope creep"],
        misses: ["Retainers"],
        text: "Both work; the choice depends on how well you can predict the scope…",
        citations: [[`${ORIGIN}/blog/hourly-vs-project-pricing`, "Hourly vs project pricing — Ledgerly"], [...CITE.reddit]],
      },
      {
        platform: "claude",
        citedUs: false,
        covers: ["When each fits", "Retainers"],
        misses: ["Hourly to project quote"],
        text: "Hourly pricing protects you when scope is unclear; project pricing rewards you for getting faster…",
        citations: [[...CITE.forbes]],
      },
      {
        platform: "ai_overview",
        citedUs: true,
        covers: ["When each fits", "Scope creep"],
        misses: [],
        text: "Freelance developers often start hourly and move to project-based pricing as they gain experience…",
        citations: [[`${ORIGIN}/blog/hourly-vs-project-pricing`, "Hourly vs project pricing — Ledgerly"]],
      },
    ],
    pageAdds: ["The hourly rate calculator linked from the post"],
    suggestion:
      "Covered, and cited by ChatGPT and AI Overviews. Retainers get one sentence; Claude's answer treats them as a real third option. A short retainer section would close the gap if you think it matters to your readers.",
  },
];

function pageFrom(p: PageSeed, points: string[]): GeoPage {
  const page = PAGE_BY_PATH.get(p.path);
  return {
    pageId: page?.id ?? pageId(p.path),
    url: `${ORIGIN}${p.path}`,
    title: page?.title,
    coverage: p.coverage,
    points: points.map((point, i) => ({ point, status: p.points[i]?.[0] ?? "missing", evidence: p.points[i]?.[1] })),
  };
}

export function checkFrom(s: GeoSeed, startedAt: string, finishedAt: string): GeoCheck {
  const pages = s.pages.map((p) => pageFrom(p, s.points));
  const best = s.verdict === "no_page" ? undefined : pages[0];
  return {
    id: `gc_${s.id.slice(3)}_${Date.parse(startedAt).toString(36)}`,
    createdAt: startedAt,
    updatedAt: finishedAt,
    siteId: SITE_ID,
    queryId: s.id,
    status: "done",
    progress: { stage: "compare", pagesFound: pages.length, points: s.points.length, pagesJudged: pages.length, answersFetched: s.answers.length },
    startedAt,
    finishedAt,
    intent: s.intent,
    requiredPoints: s.points,
    verdict: s.verdict,
    pageId: best?.pageId,
    pageUrl: best?.url,
    position: best ? s.position : undefined,
    pages,
    aiAnswers: s.answers.map((a) => ({
      platform: a.platform,
      shown: a.shown !== false,
      text: a.text,
      citations: a.citations.map(([url, title]) => ({ url, title })),
      citedUs: a.citedUs,
      covers: a.covers,
      misses: a.misses,
    })),
    pageAdds: s.pageAdds,
    suggestion: s.suggestion,
    model: "deepseek/deepseek-v3.2",
  };
}

export const QUERIES: GeoQuery[] = SEEDS.map((s, i) => {
  const created = ago((12 - i) * DAY);
  const latestCheck =
    s.checkedDaysAgo === null
      ? undefined
      : checkFrom(s, ago(s.checkedDaysAgo * DAY + HOUR), ago(s.checkedDaysAgo * DAY + HOUR - 4 * 60_000));
  return { id: s.id, createdAt: created, updatedAt: created, siteId: SITE_ID, text: s.text, source: s.source, enabled: true, latestCheck };
});

export const FALLBACK: Omit<GeoSeed, "id" | "text" | "source" | "checkedDaysAgo"> = {
  intent: "informational",
  verdict: "no_page",
  points: [
    "Answers the question in the first paragraph",
    "Gives a concrete example with numbers",
    "Lists the common mistakes",
    "Links to a template or tool",
  ],
  pages: [],
  answers: [
    {
      platform: "chat_gpt",
      citedUs: false,
      covers: ["Answers up front", "Concrete example", "Common mistakes"],
      misses: ["Template or tool"],
      text: "Here is a short answer, then the details…",
      citations: [[...CITE.nerdwallet], [...CITE.reddit]],
    },
    {
      platform: "claude",
      citedUs: false,
      covers: ["Answers up front", "Common mistakes"],
      misses: ["Concrete example"],
      text: "It depends on a few things; here is how to decide…",
      citations: [[...CITE.forbes]],
    },
    {
      platform: "ai_overview",
      citedUs: false,
      covers: ["Answers up front"],
      misses: ["Common mistakes"],
      text: "In short: yes, in most cases. Common considerations include…",
      citations: [[...CITE.nerdwallet]],
    },
  ],
  pageAdds: [],
  suggestion:
    "No page on the site answers this yet, and every AI answer cites a publisher or a forum thread instead. If the question matters to your customers, a page that answers it up front with an example would fill the gap. Whether to write it is your call.",
};
