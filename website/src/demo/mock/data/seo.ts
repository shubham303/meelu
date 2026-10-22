import type {
  BacklinkOpportunity,
  ClusterImportance,
  KeywordCluster,
  SearchIntent,
  TrackedKeyword,
} from "@/app/(demo)/demo/dashboard/seo/types";
import { ago, DAY, hashString, NOW, seeded } from "../rand";
import { ORIGIN } from "./site";

export const LEDGERLY_DOMAIN_RANK = 310;

export const LOCATION_CODES: Record<string, number> = {
  US: 2840,
  GB: 2826,
  CA: 2124,
  AU: 2036,
  IE: 2372,
  NZ: 2554,
  DE: 2276,
  IN: 2356,
};

export function countryOf(location: number): string | undefined {
  return Object.entries(LOCATION_CODES).find(([, code]) => code === location)?.[0];
}

const DOMAINS: Record<string, { brand: string; rank: number }> = {
  "quickbooks.intuit.com": { brand: "QuickBooks", rank: 712 },
  "freshbooks.com": { brand: "FreshBooks", rank: 561 },
  "waveapps.com": { brand: "Wave", rank: 524 },
  "xero.com": { brand: "Xero", rank: 618 },
  "zoho.com": { brand: "Zoho", rank: 702 },
  "hellobonsai.com": { brand: "Bonsai", rank: 452 },
  "bench.co": { brand: "Bench", rank: 471 },
  "invoicesimple.com": { brand: "Invoice Simple", rank: 423 },
  "invoice-generator.com": { brand: "Invoice Generator", rank: 386 },
  "canva.com": { brand: "Canva", rank: 764 },
  "create.microsoft.com": { brand: "Microsoft Create", rank: 902 },
  "smartsheet.com": { brand: "Smartsheet", rank: 603 },
  "squareup.com": { brand: "Square", rank: 694 },
  "paypal.com": { brand: "PayPal", rank: 806 },
  "stripe.com": { brand: "Stripe", rank: 724 },
  "irs.gov": { brand: "Internal Revenue Service", rank: 768 },
  "gov.uk": { brand: "GOV.UK", rank: 791 },
  "nerdwallet.com": { brand: "NerdWallet", rank: 688 },
  "turbotax.intuit.com": { brand: "TurboTax", rank: 681 },
  "hrblock.com": { brand: "H&R Block", rank: 633 },
  "investopedia.com": { brand: "Investopedia", rank: 742 },
  "keepertax.com": { brand: "Keeper", rank: 392 },
  "forbes.com": { brand: "Forbes Advisor", rank: 781 },
  "reddit.com": { brand: "Reddit", rank: 822 },
  "g2.com": { brand: "G2", rank: 701 },
  "capterra.com": { brand: "Capterra", rank: 689 },
  "fitsmallbusiness.com": { brand: "Fit Small Business", rank: 538 },
  "pcmag.com": { brand: "PCMag", rank: 719 },
  "business.org": { brand: "Business.org", rank: 476 },
  "upwork.com": { brand: "Upwork", rank: 703 },
  "shopify.com": { brand: "Shopify", rank: 763 },
  "etsy.com": { brand: "Etsy", rank: 779 },
  "everlance.com": { brand: "Everlance", rank: 408 },
  "mileiq.com": { brand: "MileIQ", rank: 447 },
  "expensify.com": { brand: "Expensify", rank: 559 },
  "dext.com": { brand: "Dext", rank: 418 },
  "healthcare.gov": { brand: "HealthCare.gov", rank: 702 },
  "gusto.com": { brand: "Gusto", rank: 597 },
  "rocketlawyer.com": { brand: "Rocket Lawyer", rank: 618 },
  "legaltemplates.net": { brand: "LegalTemplates", rank: 381 },
  "fundbox.com": { brand: "Fundbox", rank: 402 },
  "bluevine.com": { brand: "Bluevine", rank: 455 },
  "indy.fyi": { brand: "Indy", rank: 334 },
  "taxfoundation.org": { brand: "Tax Foundation", rank: 541 },
  "avalara.com": { brand: "Avalara", rank: 588 },
  "quaderno.io": { brand: "Quaderno", rank: 352 },
  "sage.com": { brand: "Sage", rank: 649 },
  "freeagent.com": { brand: "FreeAgent", rank: 487 },
  "crunch.co.uk": { brand: "Crunch", rank: 371 },
  "which.co.uk": { brand: "Which?", rank: 655 },
};

const THEMES: Record<string, string[]> = {
  invoice: ["invoicesimple.com", "freshbooks.com", "invoice-generator.com", "canva.com", "create.microsoft.com", "quickbooks.intuit.com", "squareup.com", "smartsheet.com", "waveapps.com", "zoho.com", "paypal.com", "hellobonsai.com", "reddit.com"],
  tax: ["irs.gov", "nerdwallet.com", "turbotax.intuit.com", "hrblock.com", "investopedia.com", "keepertax.com", "forbes.com", "bench.co", "reddit.com", "quickbooks.intuit.com", "indy.fyi", "freshbooks.com"],
  software: ["nerdwallet.com", "forbes.com", "pcmag.com", "g2.com", "capterra.com", "fitsmallbusiness.com", "business.org", "freshbooks.com", "waveapps.com", "xero.com", "zoho.com", "reddit.com", "quickbooks.intuit.com", "hellobonsai.com"],
  cash: ["freshbooks.com", "quickbooks.intuit.com", "investopedia.com", "bench.co", "stripe.com", "xero.com", "forbes.com", "reddit.com", "nerdwallet.com", "gusto.com", "fundbox.com", "bluevine.com"],
  expenses: ["everlance.com", "mileiq.com", "expensify.com", "dext.com", "quickbooks.intuit.com", "irs.gov", "keepertax.com", "nerdwallet.com", "smartsheet.com", "reddit.com", "zoho.com", "canva.com"],
  legal: ["rocketlawyer.com", "legaltemplates.net", "hellobonsai.com", "upwork.com", "indy.fyi", "freshbooks.com", "forbes.com", "reddit.com", "nerdwallet.com", "canva.com"],
  commerce: ["shopify.com", "etsy.com", "avalara.com", "quaderno.io", "taxfoundation.org", "quickbooks.intuit.com", "bench.co", "reddit.com", "forbes.com", "stripe.com"],
  uk: ["gov.uk", "freeagent.com", "crunch.co.uk", "sage.com", "xero.com", "which.co.uk", "quickbooks.intuit.com", "freshbooks.com", "reddit.com", "zoho.com"],
};

interface ClusterSeed {
  main: string;
  keywords: string[];
  core?: string;
  seeds: string[];
  volume: number;
  theme: keyof typeof THEMES;
  ours?: { path: string; position: number };
  country?: string;
  rankedInSearch?: boolean;
  createdDaysAgo: number;
}

const SEEDS: ClusterSeed[] = [
  { main: "invoice template", keywords: ["free invoice template", "invoice template word", "invoice template pdf", "simple invoice template", "blank invoice template", "invoice template google docs", "invoice format"], seeds: ["invoice"], volume: 49500, theme: "invoice", ours: { path: "/templates/invoice", position: 7 }, createdDaysAgo: 34 },
  { main: "invoice generator", keywords: ["free invoice generator", "invoice maker", "online invoice generator", "create invoice online", "invoice creator"], seeds: ["invoice"], volume: 40500, theme: "invoice", ours: { path: "/tools/invoice-generator", position: 13 }, createdDaysAgo: 34 },
  { main: "quarterly estimated taxes", keywords: ["estimated tax payments", "how to pay quarterly taxes", "estimated taxes self employed", "quarterly tax payments for self employed", "when are quarterly taxes due"], core: "estimated taxes", seeds: ["freelance taxes"], volume: 18100, theme: "tax", ours: { path: "/blog/quarterly-estimated-taxes-explained", position: 9 }, createdDaysAgo: 30 },
  { main: "1099-nec", keywords: ["1099 nec form", "what is a 1099-nec", "1099-nec explained", "1099 nec vs 1099 misc", "who gets a 1099-nec"], seeds: ["freelance taxes"], volume: 33100, theme: "tax", ours: { path: "/blog/1099-nec-guide", position: 14 }, createdDaysAgo: 30 },
  { main: "schedule c instructions", keywords: ["how to fill out schedule c", "schedule c form", "schedule c for freelancers", "schedule c expenses"], seeds: ["freelance taxes"], volume: 12100, theme: "tax", createdDaysAgo: 30 },
  { main: "freelance tax deductions", keywords: ["what can i deduct as a freelancer", "self employed tax deductions", "1099 deductions list", "tax write offs for freelancers", "freelancer tax write offs"], seeds: ["freelance taxes"], volume: 5400, theme: "tax", ours: { path: "/blog/deductible-expenses-freelancers", position: 11 }, createdDaysAgo: 30 },
  { main: "self employed health insurance deduction", keywords: ["health insurance deduction self employed", "can i deduct health insurance as a freelancer", "self employed health insurance tax"], seeds: ["freelance taxes"], volume: 1300, theme: "tax", createdDaysAgo: 30 },
  { main: "quickbooks alternative", keywords: ["quickbooks alternatives", "cheaper alternative to quickbooks", "quickbooks alternative for small business", "free quickbooks alternative", "apps like quickbooks"], core: "quickbooks alternative", seeds: ["quickbooks", "bookkeeping software"], volume: 6600, theme: "software", ours: { path: "/compare/quickbooks", position: 8 }, createdDaysAgo: 26 },
  { main: "freshbooks alternative", keywords: ["freshbooks alternatives", "cheaper than freshbooks", "freshbooks competitors", "apps like freshbooks"], seeds: ["bookkeeping software"], volume: 2400, theme: "software", ours: { path: "/compare/freshbooks", position: 6 }, createdDaysAgo: 26 },
  { main: "wave accounting alternative", keywords: ["wave alternative", "wave accounting alternatives", "wave vs freshbooks", "is wave still free"], seeds: ["bookkeeping software"], volume: 1300, theme: "software", ours: { path: "/compare/wave", position: 7 }, createdDaysAgo: 26 },
  { main: "best bookkeeping software for freelancers", keywords: ["bookkeeping software freelancers", "best accounting software for freelancers", "freelance accounting app", "accounting software for self employed"], seeds: ["bookkeeping software"], volume: 1600, theme: "software", ours: { path: "/blog/best-bookkeeping-software-freelancers", position: 16 }, createdDaysAgo: 26 },
  { main: "late payment reminder email", keywords: ["payment reminder email", "overdue invoice email", "friendly payment reminder template", "payment reminder template", "invoice reminder email"], seeds: ["late payments"], volume: 2900, theme: "invoice", ours: { path: "/templates/late-payment-reminder", position: 6 }, createdDaysAgo: 22 },
  { main: "invoice payment terms", keywords: ["payment terms on invoice", "net 30 payment terms", "net 30 meaning", "due on receipt meaning"], seeds: ["late payments"], volume: 3600, theme: "cash", ours: { path: "/blog/invoice-payment-terms", position: 12 }, createdDaysAgo: 22 },
  { main: "invoice factoring for freelancers", keywords: ["freelance invoice factoring", "get paid early on invoices", "invoice financing for freelancers"], seeds: ["late payments"], volume: 480, theme: "cash", createdDaysAgo: 22 },
  { main: "freelance hourly rate calculator", keywords: ["hourly rate calculator", "how much should i charge per hour freelance", "freelance rate calculator", "contractor rate calculator"], seeds: ["pricing freelance work"], volume: 1900, theme: "cash", ours: { path: "/tools/hourly-rate-calculator", position: 5 }, createdDaysAgo: 19 },
  { main: "how to record stripe fees", keywords: ["stripe fees accounting", "stripe fees bookkeeping", "how to categorize stripe fees", "stripe payout reconciliation"], seeds: ["payment processors"], volume: 880, theme: "cash", ours: { path: "/blog/stripe-fees-bookkeeping", position: 4 }, createdDaysAgo: 19 },
  { main: "profit and loss statement template", keywords: ["profit and loss template", "p&l template", "simple profit and loss statement", "self employed profit and loss statement"], seeds: ["bookkeeping templates"], volume: 8100, theme: "invoice", ours: { path: "/templates/profit-and-loss", position: 10 }, createdDaysAgo: 19 },
  { main: "chart of accounts for freelancers", keywords: ["freelancer chart of accounts", "chart of accounts for sole proprietor", "simple chart of accounts"], seeds: ["bookkeeping basics"], volume: 590, theme: "cash", ours: { path: "/blog/chart-of-accounts-freelancer", position: 9 }, createdDaysAgo: 19 },
  { main: "mileage log template", keywords: ["mileage log", "irs mileage log template", "mileage tracker spreadsheet", "printable mileage log"], seeds: ["bookkeeping templates"], volume: 6600, theme: "expenses", createdDaysAgo: 19 },
  { main: "receipt scanner app", keywords: ["receipt tracking app", "best receipt scanner app", "scan receipts for taxes", "receipt organizer app"], seeds: ["expense tracking"], volume: 9900, theme: "expenses", createdDaysAgo: 19 },
  { main: "freelance contract template", keywords: ["freelance contract", "freelance agreement template", "independent contractor agreement template", "freelance contract sample"], seeds: ["freelance clients"], volume: 4400, theme: "legal", createdDaysAgo: 17 },
  { main: "how to pay yourself as a sole proprietor", keywords: ["sole proprietor pay yourself", "owner's draw", "how do freelancers pay themselves", "owner draw vs salary"], seeds: ["bookkeeping basics"], volume: 1000, theme: "cash", createdDaysAgo: 17 },
  { main: "invoice template uk", keywords: ["uk invoice template", "sole trader invoice template", "vat invoice template", "invoice template uk free"], seeds: ["invoice"], volume: 2900, theme: "uk", ours: { path: "/templates/invoice", position: 9 }, country: "GB", createdDaysAgo: 15 },
  { main: "sales tax on digital products", keywords: ["sales tax digital products", "do i charge sales tax on digital downloads", "digital goods sales tax by state"], seeds: ["sales tax"], volume: 1600, theme: "commerce", ours: { path: "/blog/sales-tax-digital-products", position: 13 }, rankedInSearch: true, createdDaysAgo: 4 },
  { main: "recurring invoice software", keywords: ["recurring invoices", "automatic recurring invoices", "recurring billing for freelancers"], seeds: ["invoice"], volume: 720, theme: "invoice", ours: { path: "/blog/recurring-invoices", position: 12 }, rankedInSearch: true, createdDaysAgo: 4 },
  { main: "multi currency invoicing", keywords: ["multi currency invoice", "invoice in foreign currency", "invoicing international clients"], seeds: ["invoice"], volume: 390, theme: "invoice", ours: { path: "/blog/multi-currency-invoicing", position: 11 }, rankedInSearch: true, createdDaysAgo: 4 },
  { main: "invoice numbering system", keywords: ["invoice numbering", "how to number invoices", "invoice number format"], seeds: ["invoice"], volume: 880, theme: "invoice", ours: { path: "/blog/invoice-numbering", position: 13 }, rankedInSearch: true, createdDaysAgo: 4 },
  { main: "how to write off a laptop for business", keywords: ["can i write off a laptop", "deduct computer for business", "section 179 laptop"], seeds: ["freelance taxes"], volume: 1300, theme: "tax", createdDaysAgo: 2 },
  { main: "freelance bookkeeping checklist", keywords: ["bookkeeping checklist", "monthly bookkeeping checklist", "year end bookkeeping checklist"], seeds: ["bookkeeping basics"], volume: 320, theme: "cash", createdDaysAgo: 2 },
  { main: "self assessment for freelancers", keywords: ["self assessment tax return freelancer", "self assessment deadline", "how to do self assessment as a sole trader"], seeds: ["uk taxes"], volume: 2400, theme: "uk", country: "GB", createdDaysAgo: 2 },
];

function slug(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export function intentOf(keyword: string): SearchIntent {
  if (/\b(ledgerly|login|sign in)\b/.test(keyword)) return "navigational";
  if (/\b(alternative|alternatives|best|vs|software|app|apps|competitors)\b/.test(keyword)) return "commercial";
  if (/\b(template|generator|calculator|maker|log)\b/.test(keyword)) return "transactional";
  return "informational";
}

export function importanceOf(keyword: string): ClusterImportance {
  const intent = intentOf(keyword);
  if (intent === "transactional" || /\b(alternative|alternatives|software|app)\b/.test(keyword)) return "hot";
  if (intent === "commercial" || /\b(invoice|invoicing|bookkeeping|expense|receipt)\b/.test(keyword)) return "warm";
  return "cold";
}

function buildCluster(seed: ClusterSeed): KeywordCluster {
  const id = `kcl_${slug(seed.main).slice(0, 24)}`;
  const country = seed.country ?? "US";
  return {
    id,
    mainKeyword: seed.main,
    keywords: [seed.main, ...seed.keywords],
    coreKeyword: seed.core,
    seeds: seed.seeds,
    locationCode: LOCATION_CODES[country],
    languageCode: "en",
    country,
    volume: seed.volume,
    intent: intentOf(seed.main),
    importance: importanceOf(seed.main),
    isRanked: Boolean(seed.ours) || Boolean(seed.rankedInSearch),
    createdAt: ago(seed.createdDaysAgo * DAY),
    updatedAt: ago(seed.createdDaysAgo * DAY),
  };
}

export const CLUSTERS: KeywordCluster[] = SEEDS.map(buildCluster);

const DISCOVERED: Record<string, ClusterSeed[]> = {
  search_console: [
    { main: "late fee on invoice", keywords: ["how to add a late fee to an invoice", "late fee wording", "is it legal to charge a late fee"], seeds: ["search console"], volume: 1900, theme: "invoice", ours: { path: "/blog/late-fee-invoice", position: 15 }, createdDaysAgo: 0 },
    { main: "deposit invoice", keywords: ["how to ask for a deposit freelance", "deposit invoice template", "upfront payment freelance"], seeds: ["search console"], volume: 720, theme: "invoice", ours: { path: "/blog/deposit-before-starting", position: 13 }, createdDaysAgo: 0 },
    { main: "bank reconciliation", keywords: ["how to do a bank reconciliation", "bank reconciliation example", "reconcile bank statement small business"], seeds: ["search console"], volume: 14800, theme: "cash", ours: { path: "/blog/bank-reconciliation-basics", position: 21 }, createdDaysAgo: 0 },
    { main: "hourly vs project pricing", keywords: ["hourly vs fixed price freelance", "should i charge hourly or per project", "value based pricing freelance"], seeds: ["search console"], volume: 880, theme: "cash", ours: { path: "/blog/hourly-vs-project-pricing", position: 9 }, createdDaysAgo: 0 },
  ],
  ranked_keywords: [
    { main: "expense tracking app", keywords: ["best expense tracker for small business", "business expense app", "track expenses for taxes"], seeds: ["ranked keywords"], volume: 6600, theme: "expenses", ours: { path: "/features/expenses", position: 18 }, createdDaysAgo: 0 },
    { main: "cash flow forecast template", keywords: ["cash flow forecast", "12 month cash flow template", "small business cash flow projection"], seeds: ["ranked keywords"], volume: 3600, theme: "cash", ours: { path: "/templates/cash-flow", position: 12 }, createdDaysAgo: 0 },
    { main: "receipt template", keywords: ["free receipt template", "payment receipt template", "cash receipt template"], seeds: ["ranked keywords"], volume: 12100, theme: "invoice", ours: { path: "/templates/receipt", position: 17 }, createdDaysAgo: 0 },
  ],
  competitor_keywords: [
    { main: "time tracking for freelancers", keywords: ["freelance time tracker", "time tracking and invoicing", "billable hours tracker"], seeds: ["competitor keywords"], volume: 2400, theme: "software", createdDaysAgo: 0 },
    { main: "estimate vs quote", keywords: ["difference between estimate and quote", "quote vs invoice", "how to write a quote"], seeds: ["competitor keywords"], volume: 1600, theme: "invoice", createdDaysAgo: 0 },
    { main: "accounting for photographers", keywords: ["bookkeeping for photographers", "photography business expenses", "accounting software for photographers"], seeds: ["competitor keywords"], volume: 880, theme: "software", createdDaysAgo: 0 },
    { main: "client portal for freelancers", keywords: ["freelance client portal", "share invoices with clients", "client portal software"], seeds: ["competitor keywords"], volume: 590, theme: "software", createdDaysAgo: 0 },
  ],
};

function topicSeeds(topic: string): ClusterSeed[] {
  const t = topic.trim().toLowerCase();
  const rng = seeded(hashString(t));
  const vol = (lo: number, hi: number) => Math.round((lo + rng() * (hi - lo)) / 10) * 10;
  const theme = (Object.keys(THEMES).find((k) => t.includes(k)) ?? (/(tax|deduct|1099|irs)/.test(t) ? "tax" : /(invoice|bill|quote)/.test(t) ? "invoice" : "cash")) as keyof typeof THEMES;
  const base = { seeds: [t], theme, createdDaysAgo: 0 };
  return [
    { ...base, main: t, keywords: [`${t} for freelancers`, `${t} for small business`, `what is ${t}`], volume: vol(2400, 9900) },
    { ...base, main: `${t} template`, keywords: [`free ${t} template`, `${t} spreadsheet`, `${t} example`], volume: vol(700, 3600) },
    { ...base, main: `how to do ${t} as a freelancer`, keywords: [`${t} for self employed`, `${t} step by step`, `${t} tips`], volume: vol(200, 1300) },
    { ...base, main: `${t} software`, keywords: [`best ${t} software`, `${t} app`, `${t} tool for freelancers`], volume: vol(500, 2900) },
    { ...base, main: `${t} mistakes`, keywords: [`common ${t} mistakes`, `${t} checklist`], volume: vol(90, 480) },
  ];
}

export function discoverClusters(source: string, topic: string | null, existing: Set<string>): KeywordCluster[] {
  const bank = topic ? topicSeeds(topic) : (DISCOVERED[source] ?? DISCOVERED.competitor_keywords);
  return bank.filter((seed) => !existing.has(seed.main)).slice(0, 5).map(buildCluster);
}

interface CompetitorSeed {
  domain: string;
  addedDaysAgo: number;
  backlinks: number;
  fetchedDaysAgo?: number;
}

export const COMPETITOR_SEEDS: CompetitorSeed[] = [
  { domain: "freshbooks.com", addedDaysAgo: 30, backlinks: 1840, fetchedDaysAgo: 6 },
  { domain: "quickbooks.intuit.com", addedDaysAgo: 30, backlinks: 2960, fetchedDaysAgo: 6 },
  { domain: "waveapps.com", addedDaysAgo: 30, backlinks: 1310, fetchedDaysAgo: 6 },
  { domain: "xero.com", addedDaysAgo: 28, backlinks: 0 },
  { domain: "hellobonsai.com", addedDaysAgo: 28, backlinks: 720, fetchedDaysAgo: 5 },
  { domain: "zoho.com", addedDaysAgo: 21, backlinks: 0 },
  { domain: "bench.co", addedDaysAgo: 21, backlinks: 0 },
  { domain: "invoicesimple.com", addedDaysAgo: 14, backlinks: 0 },
  { domain: "indy.fyi", addedDaysAgo: 14, backlinks: 0 },
];

export function domainRankOf(domain: string): number | undefined {
  return DOMAINS[domain]?.rank;
}

interface OpportunitySeed {
  domain: string;
  linksTo: string[];
  rank: number;
  spam: number;
  dofollow: boolean;
  path: string;
  anchor: string;
}

const OPPORTUNITY_SEEDS: OpportunitySeed[] = [
  { domain: "fitsmallbusiness.com", linksTo: ["freshbooks.com", "quickbooks.intuit.com", "waveapps.com", "hellobonsai.com"], rank: 538, spam: 2, dofollow: true, path: "/best-invoicing-software/", anchor: "FreshBooks" },
  { domain: "business.org", linksTo: ["freshbooks.com", "quickbooks.intuit.com", "waveapps.com"], rank: 476, spam: 3, dofollow: true, path: "/finance/accounting/best-accounting-software-for-freelancers/", anchor: "Wave Accounting" },
  { domain: "freelancersunion.org", linksTo: ["freshbooks.com", "waveapps.com", "hellobonsai.com"], rank: 512, spam: 1, dofollow: true, path: "/resources/getting-paid/", anchor: "late payment letter" },
  { domain: "creativeboom.com", linksTo: ["freshbooks.com", "hellobonsai.com"], rank: 489, spam: 2, dofollow: true, path: "/tips/best-invoicing-apps-for-creatives/", anchor: "Bonsai" },
  { domain: "smallbiztrends.com", linksTo: ["waveapps.com", "quickbooks.intuit.com"], rank: 571, spam: 4, dofollow: false, path: "/wave-accounting-review.html", anchor: "Wave" },
  { domain: "indiehackers.com", linksTo: ["freshbooks.com", "waveapps.com"], rank: 602, spam: 3, dofollow: false, path: "/post/what-do-you-use-for-invoicing", anchor: "waveapps.com" },
  { domain: "thefreelancer.co", linksTo: ["hellobonsai.com", "freshbooks.com"], rank: 318, spam: 6, dofollow: true, path: "/tools/freelance-finance-stack/", anchor: "Bonsai invoicing" },
  { domain: "millo.co", linksTo: ["freshbooks.com", "quickbooks.intuit.com"], rank: 402, spam: 5, dofollow: true, path: "/freelance-accounting-software", anchor: "QuickBooks Self-Employed" },
  { domain: "sidehustlenation.com", linksTo: ["waveapps.com", "quickbooks.intuit.com"], rank: 455, spam: 4, dofollow: true, path: "/best-accounting-software-side-hustle/", anchor: "Wave" },
  { domain: "aiga.org", linksTo: ["freshbooks.com", "hellobonsai.com"], rank: 548, spam: 1, dofollow: true, path: "/resources/design-business-tools", anchor: "FreshBooks" },
  { domain: "contentfolks.com", linksTo: ["hellobonsai.com", "waveapps.com"], rank: 336, spam: 3, dofollow: true, path: "/freelance-writer-toolkit/", anchor: "Wave" },
  { domain: "accountingtoday.com", linksTo: ["waveapps.com", "quickbooks.intuit.com"], rank: 612, spam: 2, dofollow: true, path: "/news/wave-changes-free-tier", anchor: "Wave Financial" },
  { domain: "solopreneurhub.io", linksTo: ["freshbooks.com", "quickbooks.intuit.com", "waveapps.com", "hellobonsai.com"], rank: 142, spam: 38, dofollow: true, path: "/directory/finance/", anchor: "visit site" },
  { domain: "paymentsjournal.com", linksTo: ["quickbooks.intuit.com", "waveapps.com"], rank: 377, spam: 7, dofollow: false, path: "/smb-payments-roundup/", anchor: "QuickBooks" },
  { domain: "doola.com", linksTo: ["freshbooks.com", "waveapps.com"], rank: 431, spam: 4, dofollow: true, path: "/blog/bookkeeping-for-llcs/", anchor: "FreshBooks" },
  { domain: "dribbble.com", linksTo: ["hellobonsai.com"], rank: 791, spam: 1, dofollow: false, path: "/stories/freelance-finances", anchor: "Bonsai" },
];

export function opportunitiesFor(fetched: Set<string>, dismissed: Set<string>): BacklinkOpportunity[] {
  return OPPORTUNITY_SEEDS.filter((o) => !dismissed.has(o.domain))
    .map((o) => ({ ...o, linksTo: o.linksTo.filter((d) => fetched.has(d)) }))
    .filter((o) => o.linksTo.length > 0)
    .sort((a, c) => c.linksTo.length - a.linksTo.length || c.rank - a.rank)
    .map((o) => ({
      domain: o.domain,
      linksTo: o.linksTo,
      domainRank: o.rank,
      domainSpamScore: o.spam,
      backlinkSpamScore: Math.max(0, o.spam - 1),
      dofollow: o.dofollow,
      exampleUrl: `https://${o.domain}${o.path}`,
      exampleAnchor: o.anchor,
    }));
}

export function backlinkCountFor(domain: string): number {
  return 400 + (hashString(domain) % 2600);
}

function monthStarts(count: number): string[] {
  const now = new Date(NOW);
  const out: string[] = [];
  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - i, 1));
    out.push(d.toISOString().slice(0, 10));
  }
  return out;
}

export const MONTHS = monthStarts(12);

interface TrackSeed {
  keyword: string;
  path?: string;
  from: number;
  to?: number;
  previous?: number;
  months: number;
  volume: number;
  demand?: TrackedKeyword["demand"];
}

function trackedRow(t: TrackSeed): TrackedKeyword {
  const rng = seeded(hashString(t.keyword));
  const history: Array<number | null> = MONTHS.map((_, i) => {
    const age = MONTHS.length - 1 - i;
    if (age >= t.months) return null;
    if (t.to === undefined) {
      return age === 0 ? null : rng() < 0.6 ? null : 22 + Math.floor(rng() * 8);
    }
    const progress = t.months <= 1 ? 1 : 1 - age / (t.months - 1);
    const value = t.from + (t.to - t.from) * progress + (age === 0 ? 0 : Math.round((rng() - 0.5) * 3));
    return value > 30 ? null : Math.max(1, Math.round(value));
  });
  const position = t.to;
  const previous = t.previous ?? (t.to === undefined ? undefined : t.to);
  const change = position !== undefined && previous !== undefined ? previous - position : undefined;
  return {
    keyword: t.keyword,
    position,
    previousPosition: previous,
    change: change || undefined,
    url: t.path && position !== undefined ? `${ORIGIN}${t.path}` : undefined,
    history,
    volume: t.volume,
    demand: t.demand,
  };
}

const TRACK_SEEDS: Record<string, TrackSeed[]> = {
  US: [
    { keyword: "ledgerly vs quickbooks", path: "/compare/quickbooks", from: 4, to: 1, previous: 1, months: 12, volume: 170, demand: "rising" },
    { keyword: "how to record stripe fees", path: "/blog/stripe-fees-bookkeeping", from: 14, to: 4, previous: 6, months: 9, volume: 880, demand: "steady" },
    { keyword: "freelance hourly rate calculator", path: "/tools/hourly-rate-calculator", from: 19, to: 5, previous: 5, months: 10, volume: 1900, demand: "steady" },
    { keyword: "late payment reminder email", path: "/templates/late-payment-reminder", from: 12, to: 6, previous: 8, months: 8, volume: 2900, demand: "steady" },
    { keyword: "freshbooks alternative", path: "/compare/freshbooks", from: 11, to: 6, previous: 5, months: 12, volume: 2400, demand: "rising" },
    { keyword: "invoice template", path: "/templates/invoice", from: 18, to: 7, previous: 9, months: 12, volume: 49500, demand: "steady" },
    { keyword: "wave accounting alternative", path: "/compare/wave", from: 15, to: 7, previous: 11, months: 6, volume: 1300, demand: "rising" },
    { keyword: "quickbooks alternative", path: "/compare/quickbooks", from: 13, to: 8, previous: 8, months: 12, volume: 6600, demand: "rising" },
    { keyword: "quarterly estimated taxes", path: "/blog/quarterly-estimated-taxes-explained", from: 6, to: 9, previous: 7, months: 12, volume: 18100, demand: "seasonal" },
    { keyword: "chart of accounts for freelancers", path: "/blog/chart-of-accounts-freelancer", from: 21, to: 9, previous: 10, months: 7, volume: 590, demand: "steady" },
    { keyword: "profit and loss statement template", path: "/templates/profit-and-loss", from: 16, to: 10, previous: 12, months: 9, volume: 8100, demand: "steady" },
    { keyword: "freelance tax deductions", path: "/blog/deductible-expenses-freelancers", from: 9, to: 11, previous: 10, months: 12, volume: 5400, demand: "seasonal" },
    { keyword: "invoice payment terms", path: "/blog/invoice-payment-terms", from: 17, to: 12, previous: 12, months: 5, volume: 3600, demand: "steady" },
    { keyword: "invoice generator", path: "/tools/invoice-generator", from: 25, to: 13, previous: 16, months: 11, volume: 40500, demand: "steady" },
    { keyword: "1099-nec", path: "/blog/1099-nec-guide", from: 12, to: 14, previous: 13, months: 12, volume: 33100, demand: "seasonal" },
    { keyword: "best bookkeeping software for freelancers", path: "/blog/best-bookkeeping-software-freelancers", from: 24, to: 16, previous: 19, months: 8, volume: 1600, demand: "rising" },
    { keyword: "home office deduction", path: "/blog/home-office-deduction", from: 17, to: 23, previous: 19, months: 12, volume: 22200, demand: "falling" },
    { keyword: "mileage log template", from: 0, months: 3, volume: 6600, demand: "seasonal" },
    { keyword: "receipt scanner app", from: 0, months: 4, volume: 9900, demand: "steady" },
    { keyword: "freelance contract template", from: 0, months: 2, volume: 4400 },
  ],
  GB: [
    { keyword: "invoice template uk", path: "/templates/invoice", from: 16, to: 9, previous: 11, months: 7, volume: 2900, demand: "steady" },
    { keyword: "freeagent alternative", path: "/compare/xero", from: 22, to: 12, previous: 12, months: 6, volume: 480, demand: "rising" },
    { keyword: "sole trader bookkeeping", path: "/for/freelancers", from: 19, to: 15, previous: 14, months: 6, volume: 1300, demand: "steady" },
    { keyword: "xero alternative", path: "/compare/xero", from: 20, to: 17, previous: 21, months: 5, volume: 1900, demand: "steady" },
    { keyword: "self assessment for freelancers", from: 0, months: 3, volume: 2400, demand: "seasonal" },
  ],
};

export function trackedFor(country: string): TrackedKeyword[] {
  return (TRACK_SEEDS[country] ?? []).map((t) => trackedRow(t));
}

export function newTrackedRow(keyword: string, cluster: KeywordCluster | undefined): TrackedKeyword {
  return {
    keyword,
    history: MONTHS.map(() => null),
    volume: cluster?.volume,
  };
}
