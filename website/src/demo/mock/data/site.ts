import type {
  LinkRegion,
  LinkSuggestion,
  PillarSuggestion,
  SiteDiscovery,
  SiteDiscoveryPage,
  SiteIssueGroup,
  SiteIssueSummary,
  SitePage,
  SitePageIssue,
  SitePageKind,
  SitePageLlmExtraction,
  SiteProfile,
} from "@demo/lib/types";
import { ago, DAY, dayKey, hashString, HOUR, int, pick, seeded } from "../rand";

export const SITE_ID = "site_ledgerly";
export const ORIGIN = "https://ledgerly.app";

export const SITE: SiteProfile = {
  id: SITE_ID,
  createdAt: ago(41 * DAY),
  updatedAt: ago(2 * HOUR),
  domain: "ledgerly.app",
  name: "Ledgerly",
  country: "US",
  repoUrl: "https://github.com/ledgerly/website",
  summary:
    "Ledgerly is bookkeeping software for freelancers and small teams. The site sells a " +
    "monthly subscription with three tiers, documents the product in a public help centre, " +
    "publishes a weekly blog on invoicing, tax and cash flow for self-employed people, and " +
    "carries a set of comparison pages against QuickBooks, FreshBooks and Wave. The voice is " +
    "plain and slightly dry; it explains rather than sells.",
  socialLinks: [
    { platform: "linkedin", url: "https://www.linkedin.com/company/ledgerly", handle: "ledgerly" },
    { platform: "x", url: "https://x.com/ledgerlyapp", handle: "@ledgerlyapp" },
    { platform: "youtube", url: "https://www.youtube.com/@ledgerly", handle: "@ledgerly" },
  ],
  sitemapUrls: ["https://ledgerly.app/sitemap.xml"],
  sitemapUrlCount: 118,
  sitemapAtRoot: true,
  robotsTxt: "User-agent: *\nAllow: /\nDisallow: /app/\n\nSitemap: https://ledgerly.app/sitemap.xml\n",
  robotsStatus: 200,
  robotsFetchedAt: ago(2 * HOUR),
  llmsTxt: null,
  llmsStatus: 404,
  llmsFetchedAt: ago(2 * HOUR),
  crawlerAccess: {
    checkedAt: ago(2 * HOUR),
    url: "https://ledgerly.app/",
    baseline: { status: 200, bytes: 48211 },
    agents: [
      { agent: "Googlebot", status: 200, bytes: 48211, verdict: "allowed" },
      { agent: "GPTBot", status: 200, bytes: 48211, verdict: "allowed" },
      { agent: "ClaudeBot", status: 200, bytes: 48211, verdict: "allowed" },
      { agent: "PerplexityBot", status: 403, bytes: 1203, verdict: "blocked", reason: "Cloudflare bot rule" },
    ],
  },
  hostVariants: {
    checkedAt: ago(2 * HOUR),
    preferred: "https://ledgerly.app",
    sample: "https://ledgerly.app/pricing",
    variants: [
      { kind: "scheme", url: "http://ledgerly.app/pricing", target: "https://ledgerly.app/pricing", verdict: "redirects", status: 301, hops: 1, finalUrl: "https://ledgerly.app/pricing", canonical: null },
      { kind: "host", url: "https://www.ledgerly.app/pricing", target: "https://ledgerly.app/pricing", verdict: "redirects", status: 301, hops: 1, finalUrl: "https://ledgerly.app/pricing", canonical: null },
      { kind: "trailing-slash", url: "https://ledgerly.app/pricing/", target: "https://ledgerly.app/pricing", verdict: "duplicate", status: 200, hops: 0, finalUrl: "https://ledgerly.app/pricing/", canonical: "https://ledgerly.app/pricing" },
    ],
  },
  lastCrawledAt: ago(2 * HOUR),
  gscProperty: "sc-domain:ledgerly.app",
  gaProperty: "properties/384920111",
};

interface Seed {
  path: string;
  title: string;
  kind: SitePageKind;
  words?: number;
  depth?: number;
  format?: string;
  status?: number;
  inSitemap?: boolean;
  orphan?: boolean;
  noindex?: boolean;
  redirectTo?: string;
  meta?: string | null;
  keywords?: string[];
  ageDays?: number;
}

const BLOG: Array<[string, string, string, string[]]> = [
  ["how-to-invoice-as-a-freelancer", "How to invoice as a freelancer (with a template)", "how-to", ["freelance invoice", "invoice template", "net 30"]],
  ["quarterly-estimated-taxes-explained", "Quarterly estimated taxes, explained for the self-employed", "how-to", ["estimated taxes", "1040-ES", "self-employed tax"]],
  ["late-paying-clients", "What to do when a client pays late", "how-to", ["late payment", "payment reminder", "invoice overdue"]],
  ["cash-flow-forecast-small-business", "A cash flow forecast you will actually keep updated", "how-to", ["cash flow forecast", "small business cash flow"]],
  ["best-bookkeeping-software-freelancers", "The 7 best bookkeeping tools for freelancers in 2026", "listicle", ["bookkeeping software", "freelancer accounting"]],
  ["quickbooks-alternatives", "9 QuickBooks alternatives for very small businesses", "listicle", ["quickbooks alternative", "simple accounting software"]],
  ["separate-business-bank-account", "Why you need a separate business bank account (even as a sole trader)", "how-to", ["business bank account", "sole proprietor"]],
  ["receipt-tracking-without-losing-your-mind", "Receipt tracking without losing your mind", "how-to", ["receipt tracking", "expense receipts"]],
  ["deductible-expenses-freelancers", "42 deductible expenses freelancers forget to claim", "listicle", ["tax deductions", "freelance expenses"]],
  ["hourly-vs-project-pricing", "Hourly vs project pricing: what the numbers say", "comparison", ["hourly rate", "project pricing"]],
  ["case-study-marina-design", "How Marina Design cut month-end close from 3 days to 40 minutes", "case study", ["month-end close", "design studio bookkeeping"]],
  ["case-study-north-loop-coffee", "North Loop Coffee: two locations, one ledger", "case study", ["cafe bookkeeping", "multi-location"]],
  ["profit-first-for-freelancers", "Profit First for freelancers: a simpler version", "how-to", ["profit first", "freelance finances"]],
  ["what-is-accrual-accounting", "Cash vs accrual accounting for a one-person business", "comparison", ["accrual accounting", "cash basis"]],
  ["invoice-payment-terms", "Invoice payment terms that get you paid faster", "how-to", ["payment terms", "net 15", "due on receipt"]],
  ["mileage-log-app", "Do you really need a mileage log app?", "comparison", ["mileage log", "mileage deduction"]],
  ["freshbooks-vs-ledgerly", "FreshBooks vs Ledgerly: an honest comparison", "comparison", ["freshbooks vs", "freshbooks alternative"]],
  ["wave-shutting-down-features", "Wave is cutting free features. Here is what changed.", "how-to", ["wave accounting", "wave free plan"]],
  ["year-end-checklist-sole-traders", "The year-end bookkeeping checklist for sole traders", "listicle", ["year end checklist", "sole trader bookkeeping"]],
  ["retainers-vs-one-off-projects", "Retainers vs one-off projects for consultants", "comparison", ["retainer agreement", "consulting pricing"]],
  ["stripe-fees-bookkeeping", "How to book Stripe fees correctly", "how-to", ["stripe fees", "payment processing fees"]],
  ["paypal-vs-stripe-freelancers", "PayPal vs Stripe for freelancers", "comparison", ["paypal vs stripe"]],
  ["how-we-price-ledgerly", "Why Ledgerly costs $12 a month", "how-to", ["pricing transparency"]],
  ["bookkeeper-or-software", "Should you hire a bookkeeper or use software?", "comparison", ["hire a bookkeeper", "bookkeeping cost"]],
  ["1099-nec-guide", "The 1099-NEC, explained for people who send and receive them", "how-to", ["1099-nec", "contractor tax form"]],
  ["home-office-deduction", "The home office deduction without the fear", "how-to", ["home office deduction"]],
  ["invoice-numbering", "Invoice numbering systems that scale past invoice #12", "how-to", ["invoice number", "invoice numbering"]],
  ["recurring-invoices", "Recurring invoices: set up once, get paid monthly", "how-to", ["recurring invoice", "subscription billing"]],
  ["client-onboarding-questionnaire", "A client onboarding questionnaire for freelancers", "how-to", ["client onboarding"]],
  ["bank-reconciliation-basics", "Bank reconciliation in ten minutes a week", "how-to", ["bank reconciliation"]],
  ["chart-of-accounts-freelancer", "A chart of accounts for a freelancer (copy this)", "how-to", ["chart of accounts"]],
  ["sales-tax-digital-products", "Sales tax on digital products: the 2026 state map", "how-to", ["sales tax digital products"]],
  ["late-fee-invoice", "Should you charge a late fee? What 400 invoices told us", "how-to", ["late fee", "invoice late fee"]],
  ["deposit-before-starting", "Always take a deposit. Here is the wording.", "how-to", ["deposit invoice", "upfront payment"]],
  ["case-study-fieldnotes-consulting", "Fieldnotes Consulting: 14 clients, zero spreadsheets", "case study", ["consulting bookkeeping"]],
  ["xero-vs-ledgerly", "Xero vs Ledgerly for a one-person business", "comparison", ["xero alternative", "xero vs"]],
  ["scope-creep", "Scope creep: the invoice line that fixes it", "how-to", ["scope creep"]],
  ["freelance-emergency-fund", "How big should a freelancer's emergency fund be?", "how-to", ["emergency fund freelancer"]],
  ["multi-currency-invoicing", "Invoicing clients abroad without losing 4% to fees", "how-to", ["multi-currency invoice", "international clients"]],
  ["accounting-terms-glossary", "38 accounting terms in plain English", "listicle", ["accounting glossary"]],
  ["tax-season-2025-recap", "What we learned from tax season 2025", "how-to", ["tax season"]],
  ["tax-season-2024-recap", "What we learned from tax season 2024", "how-to", ["tax season"]],
];

const DOCS: Array<[string, string]> = [
  ["getting-started", "Getting started with Ledgerly"],
  ["connect-your-bank", "Connect your bank"],
  ["import-transactions-csv", "Import transactions from a CSV"],
  ["categorise-transactions", "Categorise transactions"],
  ["rules", "Rules: categorise automatically"],
  ["create-an-invoice", "Create an invoice"],
  ["recurring-invoices", "Recurring invoices"],
  ["online-payments", "Accept online payments"],
  ["payment-reminders", "Automatic payment reminders"],
  ["expenses", "Track expenses"],
  ["receipts", "Attach receipts"],
  ["mileage", "Log mileage"],
  ["reports-profit-and-loss", "Profit and loss report"],
  ["reports-cash-flow", "Cash flow report"],
  ["reports-tax-summary", "Tax summary report"],
  ["export-to-your-accountant", "Export for your accountant"],
  ["accountant-access", "Give your accountant access"],
  ["billing-and-plans", "Billing and plans"],
  ["cancel-subscription", "Cancel your subscription"],
  ["data-export", "Export all your data"],
  ["security", "How Ledgerly keeps your data safe"],
  ["api", "API reference"],
  ["webhooks", "Webhooks"],
  ["zapier", "Zapier integration"],
];

const SEEDS: Seed[] = [
  { path: "/", title: "Ledgerly — Bookkeeping for freelancers and small teams", kind: "home", words: 640, depth: 0, meta: "Invoices, expenses and taxes in one calm place. Bookkeeping for freelancers and small teams, $12 a month.", keywords: ["bookkeeping software", "freelancer accounting", "small business bookkeeping"] },
  { path: "/pricing", title: "Pricing — Ledgerly", kind: "pricing", words: 480, depth: 1, meta: "Three plans, one price each. Solo $12, Team $29, Studio $59. No per-seat fees.", keywords: ["ledgerly pricing", "bookkeeping software price"] },
  { path: "/features/invoicing", title: "Invoicing that gets you paid", kind: "product", words: 910, depth: 1, keywords: ["invoicing software", "online invoices"] },
  { path: "/features/expenses", title: "Expense tracking with receipts attached", kind: "product", words: 760, depth: 1, keywords: ["expense tracking", "receipt scanning"] },
  { path: "/features/bank-feeds", title: "Bank feeds for 11,000 banks", kind: "product", words: 540, depth: 1, keywords: ["bank feed", "bank sync"] },
  { path: "/features/reports", title: "Reports your accountant will actually read", kind: "product", words: 620, depth: 1, keywords: ["profit and loss", "financial reports"] },
  { path: "/features/tax", title: "Tax estimates every quarter, no surprises", kind: "product", words: 700, depth: 1, keywords: ["quarterly tax estimate", "self-employed tax"] },
  { path: "/features/time-tracking", title: "Time tracking that turns into invoices", kind: "product", words: 410, depth: 2, keywords: ["time tracking invoice"] },
  { path: "/features/mileage", title: "Mileage tracking", kind: "product", words: 260, depth: 2, meta: null, keywords: ["mileage tracker"] },
  { path: "/features/multi-currency", title: "Multi-currency invoicing", kind: "product", words: 330, depth: 2, meta: null, keywords: ["multi-currency"] },
  { path: "/for/freelancers", title: "Ledgerly for freelancers", kind: "category", words: 820, depth: 1, keywords: ["freelancer bookkeeping"] },
  { path: "/for/consultants", title: "Ledgerly for consultants", kind: "category", words: 690, depth: 1, keywords: ["consultant bookkeeping"] },
  { path: "/for/designers", title: "Ledgerly for design studios", kind: "category", words: 580, depth: 2, keywords: ["design studio accounting"] },
  { path: "/for/developers", title: "Ledgerly for independent developers", kind: "category", words: 610, depth: 2, keywords: ["developer bookkeeping"] },
  { path: "/for/cafes", title: "Ledgerly for cafés and small shops", kind: "category", words: 450, depth: 3, keywords: ["cafe bookkeeping"] },
  { path: "/compare/quickbooks", title: "Ledgerly vs QuickBooks", kind: "product", words: 1450, depth: 2, format: "comparison", keywords: ["quickbooks alternative", "ledgerly vs quickbooks"] },
  { path: "/compare/freshbooks", title: "Ledgerly vs FreshBooks", kind: "product", words: 1320, depth: 2, format: "comparison", keywords: ["freshbooks alternative"] },
  { path: "/compare/wave", title: "Ledgerly vs Wave", kind: "product", words: 1180, depth: 2, format: "comparison", keywords: ["wave alternative"] },
  { path: "/compare/xero", title: "Ledgerly vs Xero", kind: "product", words: 990, depth: 3, format: "comparison", keywords: ["xero alternative"] },
  { path: "/compare/bonsai", title: "Ledgerly vs Bonsai", kind: "product", words: 720, depth: 3, format: "comparison", keywords: ["bonsai alternative"], orphan: true, ageDays: 300 },
  { path: "/templates", title: "Free templates", kind: "category", words: 380, depth: 1 },
  { path: "/templates/invoice", title: "Free invoice template (PDF, Word, Google Docs)", kind: "article", words: 1100, depth: 2, format: "how-to", keywords: ["invoice template", "free invoice template"] },
  { path: "/templates/receipt", title: "Free receipt template", kind: "article", words: 640, depth: 2, format: "how-to", keywords: ["receipt template"] },
  { path: "/templates/quote", title: "Free quote template", kind: "article", words: 590, depth: 2, format: "how-to", keywords: ["quote template", "estimate template"] },
  { path: "/templates/expense-report", title: "Expense report template", kind: "article", words: 520, depth: 2, format: "how-to", keywords: ["expense report template"] },
  { path: "/templates/profit-and-loss", title: "Profit and loss template for freelancers", kind: "article", words: 780, depth: 2, format: "how-to", keywords: ["profit and loss template"] },
  { path: "/templates/cash-flow", title: "Cash flow template (Google Sheets)", kind: "article", words: 700, depth: 2, format: "how-to", keywords: ["cash flow template"] },
  { path: "/templates/late-payment-reminder", title: "Late payment reminder email templates", kind: "article", words: 860, depth: 3, format: "how-to", keywords: ["payment reminder email"] },
  { path: "/tools/invoice-generator", title: "Free invoice generator", kind: "product", words: 300, depth: 1, keywords: ["invoice generator"] },
  { path: "/tools/tax-estimator", title: "Self-employed tax estimator", kind: "product", words: 420, depth: 2, keywords: ["self employed tax calculator"] },
  { path: "/tools/hourly-rate-calculator", title: "Freelance hourly rate calculator", kind: "product", words: 380, depth: 2, keywords: ["hourly rate calculator"] },
  { path: "/blog", title: "The Ledgerly blog", kind: "category", words: 210, depth: 1 },
  { path: "/docs", title: "Help centre", kind: "docs", words: 180, depth: 1 },
  { path: "/about", title: "About Ledgerly", kind: "about", words: 560, depth: 1 },
  { path: "/contact", title: "Contact", kind: "contact", words: 120, depth: 1 },
  { path: "/careers", title: "Careers", kind: "about", words: 340, depth: 2 },
  { path: "/changelog", title: "Changelog", kind: "other", words: 2400, depth: 2 },
  { path: "/security", title: "Security at Ledgerly", kind: "about", words: 720, depth: 2 },
  { path: "/privacy", title: "Privacy policy", kind: "legal", words: 2100, depth: 2 },
  { path: "/terms", title: "Terms of service", kind: "legal", words: 3200, depth: 2 },
  { path: "/cookies", title: "Cookie policy", kind: "legal", words: 480, depth: 3 },
  { path: "/dpa", title: "Data processing agreement", kind: "legal", words: 2600, depth: 4, orphan: true },
  { path: "/partners", title: "Partner with Ledgerly", kind: "other", words: 410, depth: 2 },
  { path: "/partners/accountants", title: "Ledgerly for accountants and bookkeepers", kind: "category", words: 680, depth: 3 },
  { path: "/press", title: "Press kit", kind: "other", words: 260, depth: 3, noindex: true },
  { path: "/webinars/quarterly-taxes-2026", title: "Webinar: quarterly taxes in 2026", kind: "other", words: 190, depth: 5, ageDays: 120 },
  { path: "/webinars/pricing-your-work", title: "Webinar: pricing your work", kind: "other", words: 170, depth: 5, ageDays: 200, orphan: true },
  { path: "/blog/page/2", title: "The Ledgerly blog — page 2", kind: "category", words: 200, depth: 2, inSitemap: false },
  { path: "/blog/page/3", title: "The Ledgerly blog — page 3", kind: "category", words: 200, depth: 3, inSitemap: false },
  { path: "/blog/2023-launch-post", title: "Introducing Ledgerly", kind: "article", words: 0, status: 404, inSitemap: true },
  { path: "/features/projects", title: "Projects", kind: "product", words: 0, status: 410, inSitemap: true },
  { path: "/old-pricing", title: "Pricing", kind: "pricing", words: 0, status: 301, redirectTo: "https://ledgerly.app/pricing", inSitemap: true },
  { path: "/blog/tag/taxes", title: "Posts tagged taxes", kind: "category", words: 160, depth: 2, inSitemap: false, noindex: true },
  { path: "/blog/tag/invoicing", title: "Posts tagged invoicing", kind: "category", words: 160, depth: 2, inSitemap: false, noindex: true },
  { path: "/status", title: "System status", kind: "other", words: 90, depth: 3, inSitemap: false },
  ...BLOG.map<Seed>(([slug, title, format, keywords], i) => ({
    path: `/blog/${slug}`,
    title,
    kind: "article",
    format,
    keywords,
    words: 900 + ((i * 137) % 1400),
    depth: i < 8 ? 2 : i < 24 ? 3 : 4,
    ageDays: 12 + i * 9,
  })),
  ...DOCS.map<Seed>(([slug, title], i) => ({
    path: `/docs/${slug}`,
    title: `${title} — Ledgerly help`,
    kind: "docs",
    words: 380 + ((i * 91) % 700),
    depth: 2,
    keywords: [title.toLowerCase()],
  })),
];

const BODY_SNIPPETS: Record<SitePageKind, string> = {
  home: "Ledgerly keeps your invoices, expenses and tax estimates in one calm place. Connect a bank, send an invoice in under a minute, and see what you owe in tax before it is due.",
  product: "Every feature is built for a business of one to ten people. No modules to buy, no per-seat pricing, and nothing you have to learn before it is useful.",
  pricing: "Solo is $12 a month for one person and unlimited invoices. Team is $29 for up to five people. Studio is $59 and adds client portals and an accountant seat.",
  category: "Ledgerly fits the way you already work: retainers, project fees, deposits, late fees and the occasional refund, without a chart of accounts you have to design yourself.",
  article: "The short version: send the invoice the day the work ships, make the due date a real date, and remind on day one, not day thirty. Here is how we set that up.",
  docs: "This guide walks through the steps in the order most people need them. Each step links to the screen it refers to, and nothing here requires an accountant.",
  about: "Ledgerly is a team of nine in Portland and Lisbon. We started it because every bookkeeping tool assumed we had a finance department.",
  contact: "Email hello@ledgerly.app and a person answers within a working day. There is no phone line and no chatbot.",
  legal: "This document describes what data Ledgerly collects, why, and how long it is kept. It is written to be read.",
  other: "Updates, notes and things that did not fit anywhere else.",
};

function abs(path: string): string {
  return `${ORIGIN}${path}`;
}

function idFor(path: string): string {
  return `pg_${hashString(path).toString(36)}`;
}

const rng = seeded(7);

function inlinksFor(seed: Seed): number {
  if (seed.orphan) return 0;
  if (seed.status && seed.status >= 300) return seed.status === 301 ? 3 : 1;
  const base: Record<number, number> = { 0: 118, 1: 64, 2: 18, 3: 6, 4: 3, 5: 1 };
  return Math.max(1, Math.round((base[seed.depth ?? 2] ?? 4) * (0.6 + rng() * 0.9)));
}

const NAV_TARGETS = ["/", "/pricing", "/features/invoicing", "/features/expenses", "/blog", "/docs", "/about", "/contact", "/privacy", "/terms"];

export const PAGES: SitePage[] = SEEDS.map((seed, i) => {
  const url = abs(seed.path);
  const status = seed.status ?? 200;
  const ok = status === 200;
  const inlinks = inlinksFor(seed);
  const ageDays = seed.ageDays ?? 30 + ((i * 53) % 400);
  const changedDays = Math.min(ageDays, 1 + ((i * 29) % 90));
  const meta = seed.meta === null ? undefined : (seed.meta ?? `${seed.title.replace(/ — .*$/, "")}. ${BODY_SNIPPETS[seed.kind].split(". ")[0]}.`);
  const outLinks = ok
    ? NAV_TARGETS.filter((t) => t !== seed.path).map((t) => ({
        url: abs(t),
        anchor: SEEDS.find((s) => s.path === t)?.title.replace(/ — .*$/, "") ?? t,
        region: (t === "/privacy" || t === "/terms" ? "footer" : "nav") as LinkRegion,
        count: 1,
      }))
    : [];
  const linkScore = seed.orphan ? 0 : Math.min(100, Math.round((Math.log(inlinks + 1) / Math.log(120)) * 100));
  return {
    id: idFor(seed.path),
    createdAt: ago(41 * DAY),
    updatedAt: ago(2 * HOUR),
    siteId: SITE_ID,
    url,
    status,
    contentHash: hashString(seed.title).toString(16),
    lastCrawledAt: ago(2 * HOUR + i * 900),
    inlinks,
    inboundAnchors: inlinks > 0 ? [{ from: abs("/"), anchor: seed.title.replace(/ — .*$/, "") }, ...(inlinks > 5 ? [{ from: abs("/blog"), anchor: "Read more" }] : [])] : [],
    title: ok ? seed.title : undefined,
    titlePixels: ok ? Math.round(seed.title.length * 8.6) : undefined,
    metaDescription: ok ? meta : undefined,
    h1: ok ? [seed.title.replace(/ — .*$/, "")] : [],
    headings: ok ? [{ level: 1, text: seed.title.replace(/ — .*$/, ""), ordinal: 0 }, { level: 2, text: "What you get", ordinal: 1 }, { level: 2, text: "How it works", ordinal: 2 }] : [],
    bodyText: ok ? BODY_SNIPPETS[seed.kind] : undefined,
    outLinks,
    externalLinks: [],
    canonical: ok ? url : undefined,
    robotsDirectives: seed.noindex ? "noindex, follow" : undefined,
    blockedByRobots: false,
    hasViewport: ok,
    socialMeta: (ok ? { "og:title": seed.title, "og:type": "website", "og:image": `${ORIGIN}/og/${seed.kind}.png`, "twitter:card": "summary_large_image" } : {}) as Record<string, string>,
    socialMetaCount: ok ? 4 : 0,
    schemaTypes: seed.kind === "article" ? ["Article", "BreadcrumbList"] : seed.kind === "home" ? ["Organization", "WebSite"] : seed.kind === "docs" ? ["TechArticle"] : [],
    schemaNodes: [],
    lang: ok ? "en" : undefined,
    hreflang: {},
    kind: seed.kind,
    format: seed.format,
    inSitemap: seed.inSitemap ?? true,
    depth: seed.orphan ? undefined : seed.depth,
    redirectTo: seed.redirectTo,
    redirectFinal: seed.redirectTo,
    redirectHops: seed.redirectTo ? 1 : undefined,
    contentType: ok ? "text/html; charset=utf-8" : undefined,
    images: ok ? [{ src: `${ORIGIN}/img/${seed.path.replace(/\W+/g, "-") || "home"}.png`, alt: i % 7 === 3 ? undefined : seed.title, width: 1200, height: 630 }] : [],
    publishedAt: seed.kind === "article" ? ago(ageDays * DAY) : undefined,
    modifiedAt: seed.kind === "article" ? ago(changedDays * DAY) : undefined,
    wordCount: ok ? seed.words : undefined,
    externalLinkDensity: 0,
    mixedContent: false,
    keywords: seed.keywords,
    contentChangedAt: ok ? ago(changedDays * DAY) : undefined,
    indexState: !ok ? "excluded" : seed.noindex ? "excluded" : seed.orphan ? "discovered" : i % 11 === 5 ? "crawled-not-indexed" : "indexed",
    coverageState: ok ? (seed.noindex ? "Excluded by noindex tag" : "Submitted and indexed") : "Not found (404)",
    googleCanonical: ok ? url : undefined,
    indexCheckedAt: ago(3 * DAY),
    linkScore,
    editorialInlinks: Math.max(0, inlinks - 2),
    editorialScore: Math.max(0, linkScore - 8),
    embedState: ok ? "embedded" : undefined,
    shallow: !ok,
    shallowReason: status === 404 || status === 410 ? "gone" : status === 301 ? "redirect" : undefined,
    stage: ok ? "indexed" : "crawled",
  };
});

export const PAGE_BY_ID = new Map(PAGES.map((p) => [p.id, p]));
export const PAGE_BY_PATH = new Map(PAGES.map((p) => [new URL(p.url).pathname, p]));

export function pageId(path: string): string {
  return idFor(path);
}

export const EXTRACTIONS = new Map<string, SitePageLlmExtraction>(
  PAGES.filter((p) => p.status === 200).map((p) => {
    const type =
      p.kind === "pricing" || p.kind === "product" ? "money"
      : p.kind === "category" || p.kind === "home" ? "hub"
      : p.kind === "article" ? "informational"
      : p.kind === "docs" ? "support"
      : p.kind === "about" || p.kind === "contact" ? "company"
      : p.kind === "legal" ? "legal"
      : "utility";
    return [
      p.id,
      {
        id: `ex_${p.id}`,
        createdAt: ago(90 * 60_000),
        updatedAt: ago(90 * 60_000),
        siteId: SITE_ID,
        pageId: p.id,
        pageType: type,
        confidence: 0.78 + (hashString(p.id) % 20) / 100,
        extractedFromHash: p.contentHash,
        model: "typesafe/jev-decision-v2",
        extractedAt: ago(90 * 60_000),
      },
    ];
  }),
);

const live = PAGES.filter((p) => p.status === 200);
const gone = PAGES.filter((p) => p.status === 404 || p.status === 410);
const orphans = live.filter((p) => p.inlinks === 0);
const deep = live.filter((p) => (p.depth ?? 0) >= 4);

function disc(p: SitePage): SiteDiscoveryPage {
  return { id: p.id, url: p.url, title: p.title, kind: p.kind, inlinks: p.inlinks, depth: p.depth, inSitemap: p.inSitemap };
}

export const DISCOVERY: SiteDiscovery = {
  live: live.length,
  homeFound: true,
  orphans: orphans.length,
  unreachable: 1,
  deep: deep.length,
  deepFrom: 4,
  byDepth: [...[0, 1, 2, 3, 4, 5].map((d) => ({ depth: d, n: live.filter((p) => p.depth === d).length })), { depth: undefined, n: orphans.length }],
  orphanPages: orphans.map(disc),
  unreachablePages: [disc(PAGE_BY_PATH.get("/blog/tag/taxes")!)],
  deepPages: deep.map(disc),
};

export const PAGE_STATS = {
  pages: PAGES.length,
  ok: live.length,
  errored: gone.length + 1,
  gone: gone.length,
  shallow: PAGES.filter((p) => p.shallow).length,
  notInSitemap: PAGES.filter((p) => !p.inSitemap).length,
  sitemapMissing: gone.length,
  notFound: gone.filter((p) => p.status === 404).length,
  blocked: 0,
  serverError: 0,
  unreachable: 0,
  orphans: orphans.length,
  byKind: (["home", "product", "pricing", "category", "article", "docs", "about", "contact", "legal", "other"] as const).map((kind) => ({ kind, n: PAGES.filter((p) => p.kind === kind).length })),
  byStage: [{ stage: "indexed", n: live.length }, { stage: "crawled", n: PAGES.length - live.length }],
  chunks: { total: 1412, embedded: 1412, failed: 0 },
  lastCrawledAt: ago(2 * HOUR),
  sitemapUrlCount: SITE.sitemapUrlCount ?? null,
};

type Sev = "p0" | "p1" | "p2" | "p3";
interface GroupSeed {
  scope: "site" | "pages";
  kind: SiteIssueGroup["kind"];
  issue: string;
  severity: Sev;
  issueType: SiteIssueGroup["issueType"];
  paths?: string[];
  state?: "open" | "rejected";
  reason?: string;
}

const noMeta = live.filter((p) => !p.metaDescription).map((p) => new URL(p.url).pathname);
const noAlt = live.filter((p) => p.images.some((im) => !im.alt)).map((p) => new URL(p.url).pathname);
const longTitle = live.filter((p) => (p.titlePixels ?? 0) > 580).map((p) => new URL(p.url).pathname);

const GROUP_SEEDS: GroupSeed[] = [
  { scope: "site", kind: "llms-missing", issue: "No llms.txt at the site root — AI assistants have nothing telling them what this site is or which pages matter.", severity: "p2", issueType: "static" },
  { scope: "site", kind: "ai-crawler-blocked-at-edge", issue: "PerplexityBot gets a 403 from the edge while Googlebot, GPTBot and ClaudeBot are let through. Answers about Ledgerly on Perplexity come from third parties instead.", severity: "p1", issueType: "static" },
  { scope: "site", kind: "trailing-slash-duplicate", issue: "/pricing and /pricing/ both serve 200. The canonical tag points at the slash-less version, so this is a duplicate rather than a split — but it costs crawl budget on every page.", severity: "p3", issueType: "static" },
  { scope: "pages", kind: "sitemap-dead-page", issue: "The sitemap lists pages that return 404 or 410.", severity: "p0", issueType: "static", paths: gone.map((p) => new URL(p.url).pathname) },
  { scope: "pages", kind: "sitemap-redirect", issue: "The sitemap lists a URL that redirects. List the destination instead.", severity: "p1", issueType: "static", paths: ["/old-pricing"] },
  { scope: "pages", kind: "orphan-page", issue: "In the sitemap, but nothing on the site links to it. Google can find it; a reader cannot.", severity: "p1", issueType: "static", paths: orphans.map((p) => new URL(p.url).pathname) },
  { scope: "pages", kind: "deep-page", issue: "More than four clicks from the home page. Pages this deep are crawled rarely and rank badly.", severity: "p2", issueType: "static", paths: deep.map((p) => new URL(p.url).pathname) },
  { scope: "pages", kind: "missing-meta-description", issue: "No meta description. Google writes its own snippet, usually worse.", severity: "p2", issueType: "static", paths: noMeta },
  { scope: "pages", kind: "image-missing-alt", issue: "Images without alt text.", severity: "p3", issueType: "static", paths: noAlt },
  { scope: "pages", kind: "title-too-long", issue: "Title wider than 580px gets truncated in results.", severity: "p3", issueType: "static", paths: longTitle },
  { scope: "pages", kind: "duplicate-title", issue: "Two pages share the same title, so they compete for the same query.", severity: "p2", issueType: "static", paths: ["/blog/tax-season-2025-recap", "/blog/tax-season-2024-recap"] },
  { scope: "pages", kind: "noindex-but-linked", issue: "Marked noindex but linked from indexable pages — link equity flows into a page Google discards.", severity: "p3", issueType: "static", paths: ["/press", "/blog/tag/taxes", "/blog/tag/invoicing"] },
  { scope: "pages", kind: "js-only-links", issue: "Links to these pages exist only after JavaScript runs. Crawlers that do not render never see them.", severity: "p1", issueType: "desktop", paths: ["/tools/tax-estimator", "/tools/hourly-rate-calculator", "/templates/late-payment-reminder"] },
  { scope: "pages", kind: "render-console-errors", issue: "The page logs errors to the console while rendering.", severity: "p3", issueType: "desktop", paths: ["/tools/invoice-generator", "/changelog"] },
  { scope: "pages", kind: "third-party-bloat", issue: "More than 40% of requests go to third parties.", severity: "p2", issueType: "desktop", paths: ["/", "/pricing", "/blog"] },
  { scope: "pages", kind: "mobile-small-tap-targets", issue: "Tap targets smaller than 48px on mobile.", severity: "p2", issueType: "mobile", paths: ["/pricing", "/compare/quickbooks", "/compare/freshbooks", "/templates"] },
  { scope: "pages", kind: "mobile-hidden-content", issue: "Content present on desktop is hidden on mobile. Google indexes the mobile version.", severity: "p1", issueType: "mobile", paths: ["/compare/quickbooks", "/compare/freshbooks", "/compare/wave"] },
  { scope: "pages", kind: "mobile-viewport-overflow", issue: "Content wider than the viewport on mobile — horizontal scroll.", severity: "p2", issueType: "mobile", paths: ["/changelog", "/docs/api"] },
  { scope: "site", kind: "home-missing-google-analytics", issue: "No analytics tag on the home page.", severity: "p3", issueType: "static", state: "rejected", reason: "We use a server-side pipeline on purpose." },
  { scope: "pages", kind: "url-stop-words", issue: "URL contains stop words.", severity: "p3", issueType: "static", state: "rejected", reason: "Matching the titles is more readable.", paths: ["/blog/what-is-accrual-accounting", "/blog/how-we-price-ledgerly"] },
];

export const ISSUE_GROUPS: SiteIssueGroup[] = GROUP_SEEDS.map((g) => ({
  scope: g.scope,
  kind: g.kind,
  issue: g.issue,
  severity: g.severity,
  pages: g.scope === "site" ? 0 : (g.paths?.length ?? 0),
  matched: g.scope === "site" ? 0 : (g.paths?.length ?? 0),
  examples: (g.paths ?? []).slice(0, 3).map(abs),
  state: g.state ?? "open",
  reason: g.reason ?? null,
  issueType: g.issueType,
}));

export const PAGE_ISSUES: SitePageIssue[] = GROUP_SEEDS.flatMap((g) =>
  (g.paths ?? []).map((path) => ({
    id: `pi_${hashString(g.kind + path).toString(36)}`,
    createdAt: ago(2 * HOUR),
    updatedAt: ago(2 * HOUR),
    siteId: SITE_ID,
    kind: g.kind,
    issue: g.issue,
    severity: g.severity,
    state: g.state ?? "open",
    issueType: g.issueType,
    pageId: idFor(path),
    matchedPages: g.paths?.length ?? 0,
    url: abs(path),
  })),
);

export function issueSummary(groups: SiteIssueGroup[]): SiteIssueSummary {
  const site = groups.filter((g) => g.scope === "site");
  const pages = groups.filter((g) => g.scope === "pages");
  return {
    site: { open: site.filter((g) => g.state === "open").length, rejected: site.filter((g) => g.state === "rejected").length },
    pages: { open: pages.filter((g) => g.state === "open").length, rejected: pages.filter((g) => g.state === "rejected").length },
    openSiteIssues: site.filter((g) => g.state === "open").map((g) => ({ kind: g.kind, issue: g.issue, severity: g.severity, issueType: g.issueType })),
    openPageIssues: pages.filter((g) => g.state === "open"),
  };
}

const LINK_SEEDS: Array<[string, string, LinkSuggestion["action"], LinkSuggestion["state"], string, string | null]> = [
  ["/blog/how-to-invoice-as-a-freelancer", "/templates/invoice", "create", "ready", "The paragraph that says \"use a template you trust\" never links to the template page. Link the phrase \"invoice template\" to /templates/invoice.", "Step 2: the invoice itself"],
  ["/blog/late-paying-clients", "/templates/late-payment-reminder", "create", "ready", "This post describes reminder emails in prose but the reminder templates page is one click away and unlinked. Link \"a firm second reminder\".", "The reminder sequence"],
  ["/blog/quickbooks-alternatives", "/compare/quickbooks", "create", "ready", "The Ledgerly entry in this list never points at the comparison page, which is where a reader deciding between the two should land.", "7. Ledgerly"],
  ["/blog/quarterly-estimated-taxes-explained", "/features/tax", "create", "ready", "The section on estimating what you owe is the product's core feature. Link \"estimate every quarter\" to /features/tax.", "Working out the number"],
  ["/blog/receipt-tracking-without-losing-your-mind", "/features/expenses", "create", "ready", "Link \"attach the receipt to the transaction\" to the expenses feature page.", "The one-touch rule"],
  ["/for/freelancers", "/blog/deductible-expenses-freelancers", "create", "ready", "This landing page mentions deductions in passing; the 42-deductions post is the strongest piece on the site for that intent.", "Tax time"],
  ["/blog/hourly-vs-project-pricing", "/tools/hourly-rate-calculator", "create", "ready", "The calculator exists exactly for the question this post raises and is not linked.", "Working backwards from a salary"],
  ["/blog/multi-currency-invoicing", "/features/multi-currency", "create", "ready", "Link \"invoice in the client's currency\" to the multi-currency feature page — it is currently three clicks deep with one inbound link.", "Invoice in their currency"],
  ["/docs/create-an-invoice", "/docs/payment-reminders", "create", "ready", "The last step says \"turn on reminders\" with no link. Reminders has its own doc.", "Send it"],
  ["/blog/case-study-marina-design", "/for/designers", "create", "ready", "The case study is for a design studio and never links to the design-studio landing page.", null],
  ["/compare/wave", "/blog/wave-shutting-down-features", "create", "ready", "The comparison predates Wave's plan changes. Link to the post that covers them so the page stays honest.", "Pricing"],
  ["/blog/bookkeeper-or-software", "/partners/accountants", "create", "ready", "Readers who decide on a bookkeeper should find the accountant programme. Link \"work with a bookkeeper who uses Ledgerly\".", "The hybrid option"],
  ["/blog/1099-nec-guide", "/blog/quarterly-estimated-taxes-explained", "create", "done", "Linked \"estimated payments\" to the quarterly-taxes post.", "If you receive one"],
  ["/blog/deposit-before-starting", "/templates/quote", "create", "done", "Linked \"send a quote first\" to the quote template.", null],
  ["/blog/invoice-numbering", "/docs/create-an-invoice", "create", "done", "Linked the numbering step to the invoice doc.", null],
  ["/blog/scope-creep", "/pricing", "create", "user_rejected", "Suggested linking \"a plan that fits\" to pricing.", null],
  ["/", "/blog/tax-season-2024-recap", "delete", "user_rejected", "The home page links to last year's tax recap in the footer.", null],
  ["/blog/accounting-terms-glossary", "/privacy", "create", "llm_rejected", "Glossary entry \"personal data\" could link to the privacy policy.", null],
  ["/blog/freelance-emergency-fund", "/features/bank-feeds", "create", "llm_rejected", "Link \"see your balance\" to bank feeds.", null],
  ["/blog/profit-first-for-freelancers", "/pricing", "create", "llm_rejected", "Link the pricing mention to /pricing.", null],
  ["/docs/zapier", "/docs/webhooks", "create", "llm_rejected", "Cross-link the two integration docs.", null],
  ["/blog/stripe-fees-bookkeeping", "/blog/paypal-vs-stripe-freelancers", "create", "stale", "Link Stripe fees post to the PayPal vs Stripe comparison.", null],
];

export const LINK_SUGGESTIONS: LinkSuggestion[] = LINK_SEEDS.map(([from, to, action, state, suggestion, heading], i) => ({
  id: `ls_${i + 1}`,
  createdAt: ago(3 * DAY + i * HOUR),
  updatedAt: ago(3 * DAY + i * HOUR),
  siteId: SITE_ID,
  jobId: "job_links_1",
  fromPageId: idFor(from),
  fromChunkId: heading ? `ch_${i}` : null,
  toPageId: idFor(to),
  action,
  state,
  suggestion,
  searchScore: 0.62 + ((i * 7) % 30) / 100,
  confidence: 0.7 + ((i * 11) % 28) / 100,
  score: 0.65 + ((i * 13) % 32) / 100,
  fromUrl: abs(from),
  toUrl: abs(to),
  fromChunkHeading: heading,
  fromChunkOrdinal: heading ? 2 + (i % 5) : null,
}));

function members(paths: string[]) {
  return paths.map((p) => ({ id: idFor(p), url: abs(p), title: PAGE_BY_PATH.get(p)?.title ?? null }));
}

export const PILLAR_SUGGESTIONS: PillarSuggestion[] = [
  {
    id: "ps_1", createdAt: ago(3 * DAY), updatedAt: ago(3 * DAY), siteId: SITE_ID, jobId: "job_links_1",
    action: "create", topic: "Getting paid: invoicing, reminders and late fees", memberPageIds: [], coveringPageId: null, coveringUrl: null,
    state: "ready",
    suggestion: "Nine posts cover invoicing, reminders, deposits and late fees, and none of them is the page a reader lands on first. A pillar at /guides/getting-paid that links all nine, with one paragraph per post, would give the cluster a head.",
    searchScore: 0.81, confidence: 0.86, score: 0.84,
    members: members(["/blog/how-to-invoice-as-a-freelancer", "/blog/late-paying-clients", "/blog/invoice-payment-terms", "/blog/late-fee-invoice", "/blog/deposit-before-starting", "/blog/invoice-numbering", "/blog/recurring-invoices", "/templates/invoice", "/templates/late-payment-reminder"]),
  },
  {
    id: "ps_2", createdAt: ago(3 * DAY), updatedAt: ago(3 * DAY), siteId: SITE_ID, jobId: "job_links_1",
    action: "expand", topic: "Self-employed tax", memberPageIds: [], coveringPageId: idFor("/features/tax"), coveringUrl: abs("/features/tax"),
    state: "ready",
    suggestion: "/features/tax already ranks for tax queries but links to none of the six tax posts. Add a \"Read next\" section linking them and it becomes the hub the posts are missing.",
    searchScore: 0.77, confidence: 0.8, score: 0.79,
    members: members(["/blog/quarterly-estimated-taxes-explained", "/blog/deductible-expenses-freelancers", "/blog/1099-nec-guide", "/blog/home-office-deduction", "/blog/sales-tax-digital-products", "/blog/year-end-checklist-sole-traders"]),
  },
  {
    id: "ps_3", createdAt: ago(3 * DAY), updatedAt: ago(3 * DAY), siteId: SITE_ID, jobId: "job_links_1",
    action: "create", topic: "Choosing bookkeeping software", memberPageIds: [], coveringPageId: null, coveringUrl: null,
    state: "ready",
    suggestion: "The four comparison pages and two listicles compete for \"quickbooks alternative\". One page that frames the decision and links to each comparison would stop them cannibalising each other.",
    searchScore: 0.74, confidence: 0.76, score: 0.75,
    members: members(["/compare/quickbooks", "/compare/freshbooks", "/compare/wave", "/compare/xero", "/blog/quickbooks-alternatives", "/blog/best-bookkeeping-software-freelancers"]),
  },
  {
    id: "ps_4", createdAt: ago(9 * DAY), updatedAt: ago(6 * DAY), siteId: SITE_ID, jobId: "job_links_0",
    action: "expand", topic: "Templates", memberPageIds: [], coveringPageId: idFor("/templates"), coveringUrl: abs("/templates"),
    state: "done",
    suggestion: "Added one-line descriptions and links to all seven templates on /templates.",
    searchScore: 0.7, confidence: 0.82, score: 0.76,
    members: members(["/templates/invoice", "/templates/receipt", "/templates/quote", "/templates/expense-report", "/templates/profit-and-loss", "/templates/cash-flow", "/templates/late-payment-reminder"]),
  },
];

export function crawlView() {
  return {
    jobId: null,
    state: "idle",
    active: false,
    trigger: "user",
    phase: null,
    fetched: 0,
    queued: 0,
    skipped: 0,
    discovered: 0,
    error: null,
    stopReason: null,
    cutoffDays: 7,
    lastCrawledAt: SITE.lastCrawledAt ?? null,
    pages: PAGES.length,
  };
}

export function renderStatus(device: "desktop" | "mobile") {
  return {
    siteId: SITE_ID,
    jobId: null,
    device,
    state: "idle",
    active: false,
    trigger: "user",
    scope: "sample" as const,
    userAgentProfile: "googlebot" as const,
    startedAt: ago(DAY),
    finishedAt: ago(DAY - 14 * 60_000),
    total: 40,
    rendered: 40,
    failed: 0,
    error: null,
    stopReason: null,
    renderedPages: 40,
    eligiblePages: live.length,
    pendingPages: live.length - 40,
    lastRenderedAt: ago(DAY - 14 * 60_000),
  };
}

export const SEARCH_CORPUS = PAGES.filter((p) => p.status === 200).map((p) => ({
  page: p,
  text: `${p.title} ${p.metaDescription ?? ""} ${(p.keywords ?? []).join(" ")} ${p.bodyText ?? ""}`.toLowerCase(),
}));

export function randomLike(seed: string): number {
  return seeded(hashString(seed))();
}

export { int, pick, dayKey };
