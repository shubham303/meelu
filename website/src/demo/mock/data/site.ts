import type {
  LinkRegion,
  LinkSuggestion,
  PillarMember,
  PillarSuggestion,
  SiteCrawlJob,
  SiteDiscovery,
  SiteDiscoveryPage,
  SiteExternalLink,
  SiteIssueKind,
  SiteIssueSeverity,
  SiteIssueState,
  SiteIssueType,
  SitePage,
  SitePageLink,
  SitePageLlmExtraction,
  SitePageType,
  SiteProfile,
  SiteRenderDevice,
  SiteShallowReason,
  SuggestionState,
} from "@demo/lib/types";
import { ago, DAY, hashString, HOUR } from "../rand";

export const SITE_ID = "site_ledgerly";
export const ORIGIN = "https://ledgerly.app";
export const LAST_CRAWLED_AT = ago(2 * HOUR);

interface Seed {
  path: string;
  title: string;
  type: SitePageType;
  words?: number;
  format?: string;
  status?: number;
  inSitemap?: boolean;
  noindex?: boolean;
  redirectTo?: string;
  meta?: string | null;
  lede?: string;
  ageDays?: number;
  changedDays?: number;
  shallow?: SiteShallowReason;
  author?: string;
  heavyImage?: boolean;
  noAlt?: boolean;
  pending?: boolean;
}

type Topic = "tax" | "invoice" | "expense" | "compare" | "cash" | "pricing" | null;

const BLOG: Array<[string, string, string, Topic, string]> = [
  ["how-to-invoice-as-a-freelancer", "How to invoice as a freelancer (with a template)", "how-to", "invoice", "Send the invoice the day the work ships, put a real date in the due field, and use an invoice template you trust so nothing gets left off."],
  ["quarterly-estimated-taxes-explained", "Quarterly estimated taxes, explained for the self-employed", "how-to", "tax", "If nobody withholds tax from your income, the IRS expects you to estimate it and pay four times a year. Here is how to work out the number without an accountant."],
  ["late-paying-clients", "What to do when a client pays late", "how-to", "invoice", "Most late payments are forgotten invoices, not refusals. A firm second reminder on day one past due recovers most of them."],
  ["cash-flow-forecast-small-business", "A cash flow forecast you will actually keep updated", "how-to", "cash", "A thirteen-week cash flow forecast fits on one screen and takes ten minutes a week. Anything bigger gets abandoned by March."],
  ["best-bookkeeping-software-freelancers", "The 7 best bookkeeping tools for freelancers in 2026", "listicle", "compare", "We tested seven bookkeeping tools on the jobs a freelancer actually does: invoicing, expenses, bank feeds and the quarterly tax estimate."],
  ["quickbooks-alternatives", "9 QuickBooks alternatives for very small businesses", "listicle", "compare", "QuickBooks is built for businesses with a bookkeeper. If you are the bookkeeper, one of these nine alternatives will cost less and ask less of you."],
  ["separate-business-bank-account", "Why you need a separate business bank account (even as a sole trader)", "how-to", "expense", "Mixing personal and business spending is the single biggest cause of a painful tax season. A separate account fixes it in an afternoon."],
  ["receipt-tracking-without-losing-your-mind", "Receipt tracking without losing your mind", "how-to", "expense", "Attach the receipt to the transaction the moment you pay. The one-touch rule beats any shoebox system."],
  ["deductible-expenses-freelancers", "42 deductible expenses freelancers forget to claim", "listicle", "tax", "Software subscriptions, a share of your phone bill, professional insurance and the home office deduction are the four freelancers miss most often."],
  ["hourly-vs-project-pricing", "Hourly vs project pricing: what the numbers say", "comparison", "invoice", "Across 400 freelance invoices, project pricing earned 23% more per hour worked, but only once the scope was written down."],
  ["case-study-marina-design", "How Marina Design cut month-end close from 3 days to 40 minutes", "case study", null, "Marina Design is a four-person design studio in Austin. Bank rules and recurring invoices took their month-end close from three days to forty minutes."],
  ["case-study-north-loop-coffee", "North Loop Coffee: two locations, one ledger", "case study", null, "North Loop Coffee runs two cafés in Minneapolis from one Ledgerly account, with a tag per location instead of two sets of books."],
  ["profit-first-for-freelancers", "Profit First for freelancers: a simpler version", "how-to", "cash", "Profit First asks for five bank accounts. Three are enough for a freelancer: income, tax and everything else."],
  ["what-is-accrual-accounting", "Cash vs accrual accounting for a one-person business", "comparison", "cash", "Cash basis records money when it moves. Accrual records it when it is earned. For a one-person business, cash basis is almost always the right choice."],
  ["invoice-payment-terms", "Invoice payment terms that get you paid faster", "how-to", "invoice", "Net 30 is a habit, not a rule. Due on receipt and net 15 get paid faster, and clients rarely push back."],
  ["mileage-log-app", "Do you really need a mileage log app?", "comparison", "expense", "If you drive more than a few hundred business miles a year, the standard mileage deduction is worth a log. A spreadsheet works; an app is less work."],
  ["freshbooks-vs-ledgerly", "FreshBooks vs Ledgerly: an honest comparison", "comparison", "compare", "FreshBooks has better time tracking. Ledgerly has better tax estimates and costs less. Which matters depends on how you bill."],
  ["wave-shutting-down-features", "Wave is cutting free features. Here is what changed.", "how-to", "compare", "Wave moved bank connections and receipt scanning to its paid plan this year. Here is what that means if you were on the free tier."],
  ["year-end-checklist-sole-traders", "The year-end bookkeeping checklist for sole traders", "listicle", "tax", "Reconcile every account, chase unpaid invoices, file the 1099s you owe and export a profit and loss report for your accountant."],
  ["retainers-vs-one-off-projects", "Retainers vs one-off projects for consultants", "comparison", "invoice", "Retainers smooth cash flow but cap upside. Most consultants we surveyed run one or two retainers and fill the rest with projects."],
  ["stripe-fees-bookkeeping", "How to book Stripe fees correctly", "how-to", "expense", "Record the gross payment as income and the Stripe fee as an expense. Booking only the net amount understates both."],
  ["paypal-vs-stripe-freelancers", "PayPal vs Stripe for freelancers", "comparison", "invoice", "Stripe is cheaper for card payments and cleaner for bookkeeping. PayPal wins when clients already have balances there.", ],
  ["how-we-price-ledgerly", "Why Ledgerly costs $12 a month", "how-to", "pricing", "Ledgerly has three plans and no per-seat fees. This is how we arrived at $12, and what we will never charge extra for."],
  ["bookkeeper-or-software", "Should you hire a bookkeeper or use software?", "comparison", "compare", "A bookkeeper costs $200 to $500 a month. Software costs $12. The hybrid option, software plus a bookkeeper once a year, suits most freelancers."],
  ["1099-nec-guide", "The 1099-NEC, explained for people who send and receive them", "how-to", "tax", "If you paid a contractor $600 or more in a year, you owe them a 1099-NEC by January 31. If you received one, the income still needs estimated payments."],
  ["home-office-deduction", "The home office deduction without the fear", "how-to", "tax", "The simplified method gives $5 per square foot up to 300 square feet, with no depreciation to track and nothing to recapture when you sell."],
  ["invoice-numbering", "Invoice numbering systems that scale past invoice #12", "how-to", "invoice", "Use a prefix per year and a running number: 2026-014. It sorts, it never collides and your accountant will thank you."],
  ["recurring-invoices", "Recurring invoices: set up once, get paid monthly", "how-to", "invoice", "A recurring invoice with automatic card payment turns a retainer into a deposit that just arrives."],
  ["client-onboarding-questionnaire", "A client onboarding questionnaire for freelancers", "how-to", null, "Twelve questions to ask before you start: who approves invoices, which PO number to quote and how they prefer to pay."],
  ["bank-reconciliation-basics", "Bank reconciliation in ten minutes a week", "how-to", "cash", "Match each bank transaction to an invoice, an expense or a transfer. Doing it weekly takes ten minutes; doing it yearly takes a weekend."],
  ["chart-of-accounts-freelancer", "A chart of accounts for a freelancer (copy this)", "how-to", "cash", "Twenty accounts cover almost every freelance business. More than that and the categories start overlapping."],
  ["sales-tax-digital-products", "Sales tax on digital products: the 2026 state map", "how-to", "tax", "Twenty-nine states now tax some digital products. The map shows which, and the thresholds that trigger registration."],
  ["late-fee-invoice", "Should you charge a late fee? What 400 invoices told us", "how-to", "invoice", "Invoices that mention a late fee get paid an average of six days sooner, even when the fee is never charged."],
  ["deposit-before-starting", "Always take a deposit. Here is the wording.", "how-to", "invoice", "A 30% deposit filters out clients who were never going to pay. Send a quote first, then the deposit invoice, then start."],
  ["case-study-fieldnotes-consulting", "Fieldnotes Consulting: 14 clients, zero spreadsheets", "case study", null, "Fieldnotes Consulting moved fourteen retainer clients off spreadsheets and onto recurring invoices in one afternoon."],
  ["xero-vs-ledgerly", "Xero vs Ledgerly for a one-person business", "comparison", "compare", "Xero is a full accounting system with an accountant ecosystem around it. Ledgerly is narrower and simpler, and costs less than half as much."],
  ["scope-creep", "Scope creep: the invoice line that fixes it", "how-to", "invoice", "Put an 'additional requests' line on every invoice, even when it is zero. Clients start asking before they add work."],
  ["freelance-emergency-fund", "How big should a freelancer's emergency fund be?", "how-to", "cash", "Six months of expenses is the usual advice. For freelancers with lumpy income, three months of expenses plus your next tax payment is a better target."],
  ["multi-currency-invoicing", "Invoicing clients abroad without losing 4% to fees", "how-to", "invoice", "Invoice in the client's currency, get paid into a local account and convert once a month. The fees drop from 4% to under 1%."],
  ["accounting-terms-glossary", "38 accounting terms in plain English", "listicle", null, "Accruals, liabilities, retained earnings and 35 more, each explained in two sentences without the jargon."],
  ["tax-season-2025-recap", "What we learned from tax season", "how-to", "tax", "This year's most common mistake was the same as last year's: estimated payments that ignored a big project paid in the fourth quarter."],
  ["tax-season-2024-recap", "What we learned from tax season", "how-to", "tax", "Most users who owed a penalty had skipped the third-quarter estimate. Reminders now go out two weeks before each due date."],
];

const STALE_POSTS: Record<string, number> = {
  "paypal-vs-stripe-freelancers": 620,
  "mileage-log-app": 540,
  "tax-season-2024-recap": 470,
  "accounting-terms-glossary": 690,
};

const DOCS: Array<[string, string, string]> = [
  ["getting-started", "Getting started with Ledgerly", "Create your account, connect a bank and send your first invoice. Most people are done in fifteen minutes."],
  ["connect-your-bank", "Connect your bank", "Ledgerly connects to more than 11,000 banks through Plaid. Transactions import daily and nothing is ever moved out of your account."],
  ["import-transactions-csv", "Import transactions from a CSV", "If your bank is not supported, export a CSV and drop it here. Ledgerly maps the date, amount and description columns for you."],
  ["categorise-transactions", "Categorise transactions", "Every imported transaction needs a category before it shows up in reports. Rules do most of this for you after the first month."],
  ["rules", "Rules: categorise automatically", "A rule matches a transaction by description or amount and sets its category, tag and client. Rules run on every import."],
  ["create-an-invoice", "Create an invoice", "Pick a client, add line items and send. Turn on reminders so Ledgerly chases the payment for you."],
  ["recurring-invoices", "Recurring invoices", "Set an invoice to repeat weekly, monthly or yearly. With card payments on file, the client is charged automatically."],
  ["online-payments", "Accept online payments", "Connect Stripe to let clients pay invoices by card or bank transfer. Fees are recorded as expenses automatically."],
  ["payment-reminders", "Automatic payment reminders", "Reminders go out on the due date and seven days after. You can edit the wording or switch them off per client."],
  ["expenses", "Track expenses", "Every outgoing bank transaction is an expense until you say otherwise. Add a receipt and a category and it is ready for tax time."],
  ["receipts", "Attach receipts", "Forward a receipt to your Ledgerly inbox or snap it in the mobile app. It is matched to the transaction by amount and date."],
  ["mileage", "Log mileage", "Log a trip with a start, an end and a purpose. Ledgerly applies the IRS standard rate and adds it to your deductions."],
  ["reports-profit-and-loss", "Profit and loss report", "Income minus expenses for any date range, grouped by category. Export it as PDF or CSV for your accountant."],
  ["reports-cash-flow", "Cash flow report", "Money in and money out by week, with the next thirteen weeks projected from your recurring invoices and bills."],
  ["reports-tax-summary", "Tax summary report", "Your estimated federal and state tax for the quarter, based on profit so far and the payments you have already made."],
  ["export-to-your-accountant", "Export for your accountant", "One zip with the profit and loss, the general ledger and every receipt, ready to send at year end."],
  ["accountant-access", "Give your accountant access", "Invite your accountant with a read-only seat. They see everything and can leave notes, but cannot change a transaction."],
  ["billing-and-plans", "Billing and plans", "Change plans at any time. Upgrades take effect immediately; downgrades at the end of the billing period."],
  ["cancel-subscription", "Cancel your subscription", "Cancel from Settings. Your data stays readable for twelve months so you can export it whenever you like."],
  ["data-export", "Export all your data", "Download every transaction, invoice, receipt and report as CSV and PDF in one archive."],
  ["security", "How Ledgerly keeps your data safe", "Data is encrypted at rest and in transit, bank credentials never touch our servers, and two-factor sign-in is on by default."],
  ["api", "API reference", "The Ledgerly REST API lets you create invoices, read transactions and subscribe to webhooks. Authentication is by API key."],
  ["webhooks", "Webhooks", "Subscribe to invoice.paid, invoice.overdue and transaction.imported events. Each delivery is signed and retried for 24 hours."],
  ["zapier", "Zapier integration", "Connect Ledgerly to 6,000 apps through Zapier. The most popular zap creates an invoice from a signed proposal."],
];

const PAGE_LEDES: Record<string, string> = {
  "/": "Ledgerly keeps your invoices, expenses and tax estimates in one calm place. Connect a bank, send an invoice in under a minute, and see what you owe in tax before it is due.",
  "/pricing": "Solo is $12 a month for one person and unlimited invoices. Team is $29 for up to five people. Studio is $59 and adds client portals and an accountant seat. No per-seat fees, ever.",
  "/features/invoicing": "Send a branded invoice in under a minute, take card payments through Stripe and let automatic reminders chase late payers for you.",
  "/features/expenses": "Every bank transaction lands as an expense with the receipt attached. Rules categorise the rest so tax time is a report, not a project.",
  "/features/bank-feeds": "Connect any of 11,000 banks. Transactions import every morning and match themselves to invoices and receipts.",
  "/features/reports": "Profit and loss, cash flow and a tax summary, each one page long and readable by someone who is not an accountant.",
  "/features/tax": "Ledgerly works out your quarterly estimated tax from profit so far, reminds you two weeks before each due date and records the payment when it leaves your account.",
  "/features/time-tracking": "Start a timer from the browser or your phone, then turn tracked hours into invoice lines with one click.",
  "/features/mileage": "Log trips and Ledgerly applies the standard mileage rate.",
  "/features/multi-currency": "Invoice in 38 currencies and see everything converted to dollars in your reports.",
  "/for/freelancers": "Ledgerly fits the way freelancers already work: deposits, retainers, late fees and the occasional refund, without a chart of accounts you have to design yourself. It even keeps track of deductions you would otherwise forget.",
  "/for/consultants": "Retainers, expenses billed back to clients and quarterly tax estimates, all in one place built for one-person consultancies.",
  "/for/designers": "Studios bill by project and by phase. Ledgerly handles deposits, milestone invoices and the software subscriptions that eat your margin.",
  "/for/developers": "Independent developers bill by the hour, by the sprint or on retainer. Ledgerly turns tracked time into invoices and keeps the tax estimate current.",
  "/for/cafes": "Two tills, three suppliers and a payroll provider. Ledgerly keeps them in one ledger with a tag per location.",
  "/compare/quickbooks": "QuickBooks is built for businesses with a bookkeeper on staff. Ledgerly is built for the person who is the bookkeeper, and costs a third as much.",
  "/compare/freshbooks": "FreshBooks has richer time tracking. Ledgerly has quarterly tax estimates, bank rules and a lower price. Here is the full comparison.",
  "/compare/wave": "Wave's free plan no longer includes bank connections. Ledgerly's Solo plan does, for $12 a month.",
  "/compare/xero": "Xero is a full accounting system. Ledgerly is the part of it a one-person business actually uses.",
  "/compare/bonsai": "Bonsai bundles proposals and contracts with invoicing. Ledgerly focuses on the books and integrates with your contract tool.",
  "/templates": "Free invoice, receipt, quote and report templates you can use without signing up.",
  "/templates/invoice": "A free invoice template in PDF, Word and Google Docs with every field the IRS and your client expect.",
  "/templates/receipt": "A simple receipt template for cash and card payments.",
  "/templates/quote": "Send a quote before you start. This template includes scope, price, validity and the deposit you need to begin.",
  "/templates/expense-report": "An expense report template for billing costs back to clients.",
  "/templates/profit-and-loss": "A profit and loss template for freelancers, with the categories the IRS Schedule C uses.",
  "/templates/cash-flow": "A thirteen-week cash flow template in Google Sheets.",
  "/templates/late-payment-reminder": "Three late payment reminder emails: friendly on the due date, firm a week later, final at thirty days.",
  "/tools/invoice-generator": "Fill in the fields and download a PDF invoice. No account needed.",
  "/tools/tax-estimator": "Estimate your self-employment tax and federal income tax for the year from your expected profit.",
  "/tools/hourly-rate-calculator": "Work backwards from the salary you want to the hourly rate you need to charge.",
  "/blog": "Practical notes on invoicing, tax and cash flow for people who run a business of one.",
  "/docs": "Guides for every part of Ledgerly, from connecting a bank to exporting your year for an accountant.",
  "/about": "Ledgerly is a team of nine in Portland and Lisbon. We started it because every bookkeeping tool assumed we had a finance department.",
  "/contact": "Email hello@ledgerly.app and a person answers within a working day.",
  "/careers": "We are hiring a senior product designer and a support lead. Fully remote within three hours of Lisbon or Portland.",
  "/changelog": "Every change we ship, newest first. This month: mileage export, faster bank sync and a new tax summary layout.",
  "/security": "Data is encrypted at rest and in transit, bank credentials never touch our servers, and we run an independent penetration test every year.",
  "/privacy": "This policy describes what data Ledgerly collects, why, and how long it is kept. It is written to be read.",
  "/terms": "The terms that govern your use of Ledgerly.",
  "/cookies": "The cookies Ledgerly sets and why.",
  "/dpa": "Our data processing agreement for customers in the EU and UK.",
  "/partners": "Accountants, bookkeepers and app developers who work with Ledgerly.",
  "/partners/accountants": "Get a free Studio seat for every client you bring to Ledgerly, plus a dashboard across all of them.",
  "/press": "Logos, screenshots and founder photos.",
  "/webinars/quarterly-taxes-2026": "A forty-minute walk through the 2026 quarterly estimated tax deadlines with a CPA.",
  "/webinars/pricing-your-work": "A recorded session on project pricing and deposits.",
  "/blog/page/2": "Older posts.",
  "/blog/page/3": "Older posts.",
  "/blog/tag/taxes": "Every post about taxes.",
  "/blog/tag/invoicing": "Every post about invoicing.",
};

const SEEDS: Seed[] = [
  { path: "/", title: "Ledgerly — Bookkeeping for freelancers and small teams", type: "hub", words: 640, meta: "Invoices, expenses and taxes in one calm place. Bookkeeping for freelancers and small teams, $12 a month." },
  { path: "/pricing", title: "Pricing — Ledgerly", type: "money", words: 480, meta: "Three plans, one price each. Solo $12, Team $29, Studio $59. No per-seat fees." },
  { path: "/features/invoicing", title: "Invoicing that gets you paid — Ledgerly", type: "money", words: 910, meta: "Send invoices in under a minute, take card payments and let automatic reminders chase late payers." },
  { path: "/features/expenses", title: "Expense tracking with receipts attached — Ledgerly", type: "money", words: 760, meta: "Every bank transaction lands as an expense with its receipt attached. Categorised by rules, ready for tax time." },
  { path: "/features/bank-feeds", title: "Bank feeds for 11,000 banks — Ledgerly", type: "money", words: 540 },
  { path: "/features/reports", title: "Reports your accountant will actually read — Ledgerly", type: "money", words: 620 },
  { path: "/features/tax", title: "Quarterly tax estimates, no surprises — Ledgerly", type: "money", words: 700, meta: "Ledgerly estimates your quarterly tax from profit so far and reminds you two weeks before each due date." },
  { path: "/features/time-tracking", title: "Time tracking that turns into invoices — Ledgerly", type: "money", words: 410 },
  { path: "/features/mileage", title: "Mileage tracking — Ledgerly", type: "money", words: 260, meta: null },
  { path: "/features/multi-currency", title: "Multi-currency invoicing — Ledgerly", type: "money", words: 330, meta: null },
  { path: "/for/freelancers", title: "Ledgerly for freelancers", type: "hub", words: 820 },
  { path: "/for/consultants", title: "Ledgerly for consultants", type: "hub", words: 690 },
  { path: "/for/designers", title: "Ledgerly for design studios", type: "hub", words: 580 },
  { path: "/for/developers", title: "Ledgerly for independent developers", type: "hub", words: 610 },
  { path: "/for/cafes", title: "Ledgerly for cafés and small shops", type: "hub", words: 450, noAlt: true },
  { path: "/compare/quickbooks", title: "Ledgerly vs QuickBooks: which suits a one-person business?", type: "money", words: 1450, format: "comparison", heavyImage: true },
  { path: "/compare/freshbooks", title: "Ledgerly vs FreshBooks", type: "money", words: 1320, format: "comparison" },
  { path: "/compare/wave", title: "Ledgerly vs Wave", type: "money", words: 1180, format: "comparison" },
  { path: "/compare/xero", title: "Ledgerly vs Xero", type: "money", words: 990, format: "comparison" },
  { path: "/compare/bonsai", title: "Ledgerly vs Bonsai", type: "money", words: 720, format: "comparison", ageDays: 300, changedDays: 300 },
  { path: "/templates", title: "Free bookkeeping templates — Ledgerly", type: "hub", words: 380 },
  { path: "/templates/invoice", title: "Free invoice template (PDF, Word, Google Docs)", type: "informational", words: 1100, format: "how-to", heavyImage: true },
  { path: "/templates/receipt", title: "Free receipt template", type: "informational", words: 640, format: "how-to", noAlt: true },
  { path: "/templates/quote", title: "Free quote template", type: "informational", words: 590, format: "how-to" },
  { path: "/templates/expense-report", title: "Expense report template", type: "informational", words: 520, format: "how-to", noAlt: true },
  { path: "/templates/profit-and-loss", title: "Profit and loss template for freelancers", type: "informational", words: 780, format: "how-to" },
  { path: "/templates/cash-flow", title: "Cash flow template (Google Sheets)", type: "informational", words: 700, format: "how-to" },
  { path: "/templates/late-payment-reminder", title: "Late payment reminder email templates", type: "informational", words: 860, format: "how-to" },
  { path: "/tools/invoice-generator", title: "Free invoice generator — Ledgerly", type: "utility", words: 290 },
  { path: "/tools/tax-estimator", title: "Self-employed tax estimator — Ledgerly", type: "utility", words: 420 },
  { path: "/tools/hourly-rate-calculator", title: "Freelance hourly rate calculator — Ledgerly", type: "utility", words: 380 },
  { path: "/blog", title: "The Ledgerly blog", type: "hub", words: 210 },
  { path: "/docs", title: "Ledgerly help centre", type: "hub", words: 180 },
  { path: "/about", title: "About Ledgerly", type: "company", words: 560 },
  { path: "/contact", title: "Contact Ledgerly", type: "company", words: 120, shallow: "thin" },
  { path: "/careers", title: "Careers at Ledgerly", type: "company", words: 340 },
  { path: "/changelog", title: "Changelog — Ledgerly", type: "utility", words: 2400 },
  { path: "/security", title: "Security at Ledgerly", type: "company", words: 720 },
  { path: "/privacy", title: "Privacy policy — Ledgerly", type: "legal", words: 2100, shallow: "legal" },
  { path: "/terms", title: "Terms of service — Ledgerly", type: "legal", words: 3200, shallow: "legal" },
  { path: "/cookies", title: "Cookie policy — Ledgerly", type: "legal", words: 480, shallow: "legal" },
  { path: "/dpa", title: "Data processing agreement — Ledgerly", type: "legal", words: 2600, shallow: "legal" },
  { path: "/partners", title: "Partner with Ledgerly", type: "company", words: 410 },
  { path: "/partners/accountants", title: "Ledgerly for accountants and bookkeepers", type: "money", words: 680 },
  { path: "/partners/portal", title: "Partner portal", type: "utility", status: 403, inSitemap: false, shallow: "blocked" },
  { path: "/press", title: "Press kit — Ledgerly", type: "company", words: 260, noindex: true },
  { path: "/webinars/quarterly-taxes-2026", title: "Webinar: quarterly taxes in 2026", type: "informational", words: 190, ageDays: 120, changedDays: 120 },
  { path: "/webinars/pricing-your-work", title: "Webinar: pricing your work", type: "informational", words: 170, ageDays: 200, changedDays: 200 },
  { path: "/blog/page/2", title: "The Ledgerly blog — page 2", type: "hub", words: 200, inSitemap: false, shallow: "pagination" },
  { path: "/blog/page/3", title: "The Ledgerly blog — page 3", type: "hub", words: 200, inSitemap: false, shallow: "pagination" },
  { path: "/blog/2023-launch-post", title: "Introducing Ledgerly", type: "informational", status: 404, shallow: "gone" },
  { path: "/features/projects", title: "Projects", type: "money", status: 410, shallow: "gone" },
  { path: "/old-pricing", title: "Pricing", type: "money", status: 301, redirectTo: `${ORIGIN}/pricing`, shallow: "redirect" },
  { path: "/blog/tag/taxes", title: "Posts tagged taxes", type: "hub", words: 160, inSitemap: false, noindex: true },
  { path: "/blog/tag/invoicing", title: "Posts tagged invoicing", type: "hub", words: 160, inSitemap: false, noindex: true },
  { path: "/status", title: "System status", type: "utility", status: 503, inSitemap: false, shallow: "server-error" },
  ...BLOG.map<Seed>(([slug, title, format, , lede], i) => ({
    path: `/blog/${slug}`,
    title,
    type: "informational",
    format,
    lede,
    words: 900 + ((i * 137) % 1400),
    ageDays: STALE_POSTS[slug] ?? 12 + i * 9,
    changedDays: STALE_POSTS[slug] ?? (i % 3 === 0 ? 12 + i * 9 : 2 + ((i * 17) % 60)),
    meta: i % 9 === 4 ? null : undefined,
    author: i % 5 === 2 ? undefined : ["Maya Okafor", "Tom Reyes", "Inês Duarte"][i % 3],
    noAlt: i % 7 === 3,
    heavyImage: i % 11 === 6,
    pending: slug === "wave-shutting-down-features" || slug === "how-we-price-ledgerly",
  })),
  ...DOCS.map<Seed>(([slug, title, lede], i) => ({
    path: `/docs/${slug}`,
    title: `${title} — Ledgerly help`,
    type: "support",
    lede,
    words: 380 + ((i * 91) % 700),
  })),
];

const SEED_BY_PATH = new Map(SEEDS.map((s) => [s.path, s]));

function abs(path: string): string {
  return path === "/" ? `${ORIGIN}/` : `${ORIGIN}${path}`;
}

function pathOf(url: string): string {
  const p = new URL(url).pathname;
  return p.length > 1 ? p.replace(/\/$/, "") : p;
}

function idFor(path: string): string {
  return `pg_${hashString(path).toString(36)}`;
}

export function pageId(path: string): string {
  return idFor(path);
}

function shortTitle(path: string): string {
  return SEED_BY_PATH.get(path)?.title.replace(/ — .*$/, "").replace(/ \(.*\)$/, "") ?? path;
}

interface Edge {
  src: string;
  dst: string;
  region: LinkRegion;
  anchor: string;
  count: number;
  rel?: string;
}

const edgeMap = new Map<string, Edge>();

function link(src: string, dst: string, region: LinkRegion, anchor = shortTitle(dst), rel?: string) {
  const from = SEED_BY_PATH.get(src);
  if (!from || !SEED_BY_PATH.has(dst) || src === dst) return;
  if ((from.status ?? 200) !== 200) return;
  const key = `${src}>${dst}`;
  const prev = edgeMap.get(key);
  if (prev) prev.count += 1;
  else edgeMap.set(key, { src, dst, region, anchor, count: 1, rel });
}

const HEADER_NAV: Array<[string, string]> = [
  ["/pricing", "Pricing"],
  ["/features/invoicing", "Invoicing"],
  ["/features/expenses", "Expenses"],
  ["/blog", "Blog"],
  ["/docs", "Help"],
];

const FOOTER_NAV: Array<[string, string]> = [
  ["/about", "About"],
  ["/careers", "Careers"],
  ["/contact", "Contact"],
  ["/security", "Security"],
  ["/partners", "Partners"],
  ["/changelog", "Changelog"],
  ["/status", "Status"],
  ["/privacy", "Privacy"],
  ["/terms", "Terms"],
  ["/cookies", "Cookies"],
];

const blogPaths = BLOG.map(([slug]) => `/blog/${slug}`);
const docPaths = DOCS.map(([slug]) => `/docs/${slug}`);

const TOPIC_TARGET: Record<Exclude<Topic, null>, [string, string]> = {
  tax: ["/features/tax", "estimate your quarterly tax"],
  invoice: ["/features/invoicing", "send the invoice from Ledgerly"],
  expense: ["/features/expenses", "track expenses with receipts attached"],
  compare: ["/compare/quickbooks", "how Ledgerly compares"],
  cash: ["/features/reports", "the cash flow report"],
  pricing: ["/pricing", "see the plans"],
};

for (const seed of SEEDS) {
  if (seed.path === "/blog/tag/taxes" || seed.path === "/blog/tag/invoicing") continue;
  for (const [dst, anchor] of HEADER_NAV) link(seed.path, dst, "nav", anchor);
  for (const [dst, anchor] of FOOTER_NAV) link(seed.path, dst, "footer", anchor);
  link(seed.path, "/", "header", "Ledgerly");
}

for (const dst of [
  "/features/invoicing",
  "/features/expenses",
  "/features/bank-feeds",
  "/features/reports",
  "/features/tax",
  "/for/freelancers",
  "/for/consultants",
  "/compare/quickbooks",
  "/templates",
  "/tools/invoice-generator",
]) link("/", dst, "body");

link("/features/invoicing", "/features/time-tracking", "body", "track time and bill it");
link("/features/invoicing", "/features/multi-currency", "body", "invoice in any currency");
link("/features/invoicing", "/docs/create-an-invoice", "body", "how to create an invoice");
link("/features/expenses", "/features/mileage", "body", "log mileage");
link("/features/expenses", "/docs/receipts", "body", "attach receipts");
link("/features/time-tracking", "/features/projects", "body", "group time by project");
link("/features/tax", "/tools/tax-estimator", "body", "try the tax estimator");
link("/features/reports", "/docs/reports-profit-and-loss", "body", "profit and loss report");
link("/features/bank-feeds", "/docs/connect-your-bank", "body", "connect your bank");
link("/for/freelancers", "/for/designers", "body");
link("/for/freelancers", "/for/developers", "body");
link("/for/designers", "/for/cafes", "body");
link("/for/consultants", "/features/time-tracking", "body");
link("/compare/quickbooks", "/compare/freshbooks", "body", "Ledgerly vs FreshBooks");
link("/compare/quickbooks", "/compare/wave", "body", "Ledgerly vs Wave");
link("/compare/wave", "/compare/xero", "body", "Ledgerly vs Xero");
link("/compare/quickbooks", "/pricing", "body", "compare plans");
for (const t of ["/templates/invoice", "/templates/receipt", "/templates/quote", "/templates/expense-report", "/templates/profit-and-loss", "/templates/cash-flow"]) {
  link("/templates", t, "body");
}
link("/templates/invoice", "/templates/late-payment-reminder", "body", "late payment reminder emails");
link("/templates/invoice", "/tools/invoice-generator", "body", "fill it in online");
link("/tools/invoice-generator", "/tools/tax-estimator", "aside", "Tax estimator");
link("/tools/invoice-generator", "/tools/hourly-rate-calculator", "aside", "Hourly rate calculator");
link("/about", "/press", "body", "press kit");
link("/about", "/blog/2023-launch-post", "body", "our launch post");
link("/changelog", "/blog/2023-launch-post", "body", "Ledgerly 1.0");
link("/partners", "/partners/accountants", "body", "accountants and bookkeepers");
link("/partners", "/partners/portal", "body", "partner sign-in");
link("/docs", "/docs/getting-started", "body");

blogPaths.forEach((p, i) => {
  const listing = i < 10 ? "/blog" : i < 30 ? "/blog/page/2" : "/blog/page/3";
  link(listing, p, "body");
  if (i + 1 < blogPaths.length) link(p, blogPaths[i + 1], "body", "Next post", undefined);
  if (i >= 2) link(p, blogPaths[i - 2], "aside", shortTitle(blogPaths[i - 2]));
  const topic = BLOG[i][3];
  if (topic) {
    const [target, anchor] = TOPIC_TARGET[topic];
    link(p, target, "body", anchor);
  }
  link(p, "/blog", "breadcrumb", "Blog");
});
link("/blog", "/blog/page/2", "pagination", "Older posts");
link("/blog/page/2", "/blog/page/3", "pagination", "Older posts");
link("/blog/page/2", "/blog", "pagination", "Newer posts");
link("/blog/page/3", "/blog/page/2", "pagination", "Newer posts");
link("/blog/tax-season-2024-recap", "/webinars/quarterly-taxes-2026", "body", "watch the webinar");
for (const p of ["/blog/how-to-invoice-as-a-freelancer", "/blog/scope-creep", "/blog/retainers-vs-one-off-projects"]) {
  link(p, "/old-pricing", "body", "our pricing");
}
link("/blog/how-to-invoice-as-a-freelancer", "/templates/invoice", "body", "invoice template");
link("/webinars/pricing-your-work", "/blog/tag/invoicing", "body", "more on invoicing");
link("/webinars/pricing-your-work", "/blog/tag/taxes", "body", "more on taxes");
for (const t of ["/blog/tag/taxes", "/blog/tag/invoicing"]) {
  const other = t.endsWith("taxes") ? "/blog/tag/invoicing" : "/blog/tag/taxes";
  link(t, other, "aside");
  for (const p of blogPaths.filter((_, i) => BLOG[i][3] === (t.endsWith("taxes") ? "tax" : "invoice"))) link(t, p, "body");
}
docPaths.forEach((p, i) => {
  link("/docs", p, "body");
  if (i + 1 < docPaths.length) link(p, docPaths[i + 1], "body", `Next: ${shortTitle(docPaths[i + 1])}`);
  link(p, "/docs", "breadcrumb", "Help centre");
});

const EDGES = [...edgeMap.values()];

const EXTERNAL: Record<string, SiteExternalLink[]> = {
  "/": [
    { url: "https://www.linkedin.com/company/ledgerly", region: "footer", anchor: "LinkedIn", count: 1, followable: true },
    { url: "https://x.com/ledgerlyapp", region: "footer", anchor: "X", count: 1, followable: true },
    { url: "https://www.youtube.com/@ledgerly", region: "footer", anchor: "YouTube", count: 1, followable: true },
  ],
  "/blog/quarterly-estimated-taxes-explained": [
    { url: "https://www.irs.gov/forms-pubs/about-form-1040-es", region: "body", anchor: "Form 1040-ES", count: 1, followable: true },
    { url: "https://www.irs.gov/payments/direct-pay", region: "body", anchor: "IRS Direct Pay", count: 1, followable: true },
  ],
  "/blog/1099-nec-guide": [{ url: "https://www.irs.gov/forms-pubs/about-form-1099-nec", region: "body", anchor: "Form 1099-NEC", count: 2, followable: true }],
  "/blog/home-office-deduction": [{ url: "https://www.irs.gov/businesses/small-businesses-self-employed/simplified-option-for-home-office-deduction", region: "body", anchor: "the simplified option", count: 1, followable: true }],
  "/blog/stripe-fees-bookkeeping": [{ url: "https://stripe.com/pricing", region: "body", anchor: "Stripe's pricing page", count: 1, rel: "nofollow", followable: false }],
  "/blog/paypal-vs-stripe-freelancers": [
    { url: "https://stripe.com/pricing", region: "body", anchor: "Stripe fees", count: 1, rel: "nofollow", followable: false },
    { url: "https://www.paypal.com/us/business/paypal-business-fees", region: "body", anchor: "PayPal fees", count: 1, rel: "nofollow", followable: false },
  ],
  "/features/bank-feeds": [{ url: "https://plaid.com/safety/", region: "body", anchor: "how Plaid keeps bank data safe", count: 1, followable: true }],
  "/docs/zapier": [{ url: "https://zapier.com/apps/ledgerly/integrations", region: "body", anchor: "Ledgerly on Zapier", count: 1, followable: true }],
  "/compare/quickbooks": [{ url: "https://quickbooks.intuit.com/pricing/", region: "body", anchor: "QuickBooks pricing", count: 1, rel: "nofollow", followable: false }],
};

function bfsDepth(): Map<string, number> {
  const out = new Map<string, string[]>();
  for (const e of EDGES) out.set(e.src, [...(out.get(e.src) ?? []), e.dst]);
  const depth = new Map<string, number>([["/", 0]]);
  let frontier = ["/"];
  while (frontier.length) {
    const next: string[] = [];
    for (const p of frontier) {
      for (const d of out.get(p) ?? []) {
        if (depth.has(d)) continue;
        depth.set(d, (depth.get(p) ?? 0) + 1);
        next.push(d);
      }
    }
    frontier = next;
  }
  return depth;
}

const REGION_WEIGHT: Partial<Record<LinkRegion, number>> = { body: 1, aside: 0.6, breadcrumb: 0.5, pagination: 0.5 };

function pageRank(): Map<string, number> {
  const ids = SEEDS.filter((s) => (s.status ?? 200) === 200).map((s) => s.path);
  const n = ids.length;
  const index = new Map(ids.map((p, i) => [p, i]));
  const outWeight = new Array<number>(n).fill(0);
  const inbound: Array<Array<[number, number]>> = ids.map(() => []);
  for (const e of EDGES) {
    const s = index.get(e.src);
    const d = index.get(e.dst);
    if (s === undefined || d === undefined) continue;
    const w = REGION_WEIGHT[e.region] ?? 0.2;
    outWeight[s] += w;
    inbound[d].push([s, w]);
  }
  let rank = new Array<number>(n).fill(1 / n);
  for (let it = 0; it < 24; it++) {
    const dangling = rank.reduce((sum, r, i) => (outWeight[i] === 0 ? sum + r : sum), 0);
    rank = rank.map((_, i) => (1 - 0.85) / n + 0.85 * (dangling / n + inbound[i].reduce((sum, [s, w]) => sum + (rank[s] * w) / outWeight[s], 0)));
  }
  const max = Math.max(...rank);
  return new Map(ids.map((p, i) => [p, Math.max(0, Math.round((rank[i] / max) * 100))]));
}

const DEPTH = bfsDepth();
const SCORE = pageRank();
const INLINK_SOURCES = new Map<string, Set<string>>();
for (const e of EDGES) INLINK_SOURCES.set(e.dst, (INLINK_SOURCES.get(e.dst) ?? new Set()).add(e.src));

const H2: Record<string, string[]> = {
  "how-to": ["The short version", "Step by step", "Common mistakes", "How Ledgerly handles it"],
  listicle: ["How we picked", "The list", "What we left out"],
  comparison: ["At a glance", "Where each one wins", "Pricing", "Our pick"],
  "case study": ["The problem", "What changed", "The numbers"],
};

const TYPE_H2: Record<SitePageType, string[]> = {
  money: ["What you get", "How it works", "Pricing", "Questions"],
  hub: ["Start here", "Popular"],
  informational: ["Overview", "Details"],
  support: ["Before you start", "Steps", "Troubleshooting"],
  company: ["Who we are", "Get in touch"],
  legal: ["Summary", "Details"],
  utility: ["How to use it"],
};

function headingsFor(seed: Seed, h1: string): SitePage["headings"] {
  const h2 = (seed.format && H2[seed.format]) || TYPE_H2[seed.type];
  return [{ level: 1, text: h1, ordinal: 0 }, ...h2.map((text, i) => ({ level: 2, text, ordinal: i + 1 }))];
}

function schemaFor(seed: Seed): { types: string[]; nodes: SitePage["schemaNodes"] } {
  if (seed.path === "/") return { types: ["Organization", "WebSite"], nodes: [{ type: "Organization", keys: 6, props: ["name", "url", "logo", "sameAs", "contactPoint", "foundingDate"] }, { type: "WebSite", keys: 3, props: ["name", "url", "potentialAction"] }] };
  if (seed.path.startsWith("/blog/") && seed.format) {
    const props = seed.author ? ["headline", "author", "datePublished", "dateModified", "image"] : ["headline", "datePublished", "image"];
    return { types: ["Article", "BreadcrumbList"], nodes: [{ type: "Article", keys: props.length, props }, { type: "BreadcrumbList", keys: 1, props: ["itemListElement"] }] };
  }
  if (seed.type === "support") return { types: ["TechArticle"], nodes: [{ type: "TechArticle", keys: 4, props: ["headline", "dateModified", "author", "publisher"] }] };
  if (seed.path === "/pricing") return { types: ["Product"], nodes: [{ type: "Product", keys: 3, props: ["name", "offers", "brand"] }] };
  return { types: [], nodes: [] };
}

function indexStateFor(seed: Seed, live: boolean, inlinks: number, i: number): SitePage["indexState"] {
  if (!live) return "excluded";
  if (seed.noindex) return "excluded";
  if (inlinks === 0) return "discovered";
  if (seed.shallow) return "excluded";
  return i % 13 === 7 ? "crawled-not-indexed" : "indexed";
}

function coverageFor(state: SitePage["indexState"], seed: Seed, status: number): string {
  if (status === 404) return "Not found (404)";
  if (status === 410) return "Not found (404)";
  if (status === 301) return "Page with redirect";
  if (status === 403) return "Blocked due to access forbidden (403)";
  if (status >= 500) return "Server error (5xx)";
  if (seed.noindex) return "Excluded by 'noindex' tag";
  if (state === "discovered") return "Discovered - currently not indexed";
  if (state === "crawled-not-indexed") return "Crawled - currently not indexed";
  if (state === "excluded") return "Alternate page with proper canonical tag";
  return "Submitted and indexed";
}

export const PAGES: SitePage[] = SEEDS.map((seed, i): SitePage => {
  const url = abs(seed.path);
  const status = seed.status ?? 200;
  const ok = status === 200;
  const inlinks = INLINK_SOURCES.get(seed.path)?.size ?? 0;
  const ageDays = seed.ageDays ?? 30 + ((i * 53) % 400);
  const changedDays = seed.changedDays ?? Math.min(ageDays, 1 + ((i * 29) % 90));
  const h1 = seed.title.replace(/ — .*$/, "");
  const lede = seed.lede ?? PAGE_LEDES[seed.path] ?? "";
  const meta = seed.meta === null ? undefined : (seed.meta ?? lede.split(/(?<=\.)\s/)[0]);
  const contentHash = hashString(`${seed.path}:${seed.title}:${changedDays}`).toString(16);
  const schema = schemaFor(seed);
  const outLinks = EDGES.filter((e) => e.src === seed.path);
  const external = EXTERNAL[seed.path] ?? [];
  const indexState = indexStateFor(seed, ok, inlinks, i);
  const shallowStage = status >= 400 ? "failed" : seed.shallow ? "skipped" : seed.pending ? "crawled" : "indexed";
  const isArticle = seed.path.startsWith("/blog/") && !!seed.format;
  return {
    id: idFor(seed.path),
    createdAt: ago(41 * DAY),
    updatedAt: ago(2 * HOUR + i * 60_000),
    siteId: SITE_ID,
    url,
    status,
    contentHash: ok ? contentHash : undefined,
    etag: ok ? `"${contentHash.slice(0, 8)}"` : undefined,
    lastModified: ok ? new Date(Date.parse(ago(changedDays * DAY))).toUTCString() : undefined,
    lastCrawledAt: ago(2 * HOUR + i * 9_000),
    inlinks,
    title: ok ? seed.title : undefined,
    titlePixels: ok ? Math.round(seed.title.length * 8.6) : undefined,
    metaDescription: ok ? meta : undefined,
    h1: ok ? [h1] : [],
    headings: ok ? headingsFor(seed, h1) : [],
    bodyText: ok && !seed.shallow ? lede : undefined,
    canonical: ok ? url : undefined,
    robotsDirectives: seed.noindex ? "noindex, follow" : undefined,
    blockedByRobots: false,
    viewportMeta: ok ? "width=device-width, initial-scale=1" : null,
    nosnippetCount: 0,
    socialMetaCount: ok ? (isArticle ? 6 : 4) : 0,
    socialMeta: ok
      ? {
          "og:title": h1,
          "og:description": meta ?? "",
          "og:type": isArticle ? "article" : "website",
          "og:image": `${ORIGIN}/og${seed.path === "/" ? "/home" : seed.path}.png`,
          ...(isArticle ? { "article:published_time": ago(ageDays * DAY), "twitter:creator": "@ledgerlyapp" } : {}),
          "twitter:card": "summary_large_image",
        }
      : {},
    hasGoogleAnalytics: ok ? false : null,
    author: ok ? seed.author : undefined,
    schemaTypes: ok ? schema.types : [],
    schemaNodes: ok ? schema.nodes : [],
    lang: ok ? "en" : undefined,
    hreflang: {},
    pageType: EXTRACTION_TYPE(seed),
    format: seed.format,
    inSitemap: seed.inSitemap ?? true,
    depth: DEPTH.get(seed.path),
    redirectTo: seed.redirectTo,
    redirectFinal: seed.redirectTo,
    redirectHops: seed.redirectTo ? 1 : undefined,
    fetchError: status === 503 ? "503 Service Unavailable after 2 retries" : status === 403 ? "403 Forbidden — the server asks for a sign-in" : undefined,
    contentType: ok || status === 404 ? "text/html; charset=utf-8" : undefined,
    images: ok
      ? [
          {
            src: `${ORIGIN}/img${seed.path === "/" ? "/home" : seed.path}-hero.${seed.heavyImage ? "png" : "webp"}`,
            alt: seed.noAlt ? undefined : h1,
            width: 1600,
            height: 900,
            bytes: seed.heavyImage ? 1_840_000 + i * 1_000 : 84_000 + ((i * 3_517) % 90_000),
            type: seed.heavyImage ? "image/png" : "image/webp",
          },
        ]
      : [],
    publishedAt: isArticle ? ago(ageDays * DAY) : undefined,
    modifiedAt: isArticle ? ago(changedDays * DAY) : undefined,
    wordCount: ok ? seed.words : undefined,
    mixedContent: false,
    contentChangedAt: ok ? ago(changedDays * DAY) : undefined,
    indexState,
    coverageState: coverageFor(indexState, seed, status),
    googleCanonical: ok && !seed.noindex ? url : undefined,
    indexCheckedAt: ago(3 * DAY),
    linkScore: SCORE.get(seed.path),
    chunkedFromHash: ok && !seed.shallow && !seed.pending ? contentHash : undefined,
    embedState: ok && !seed.shallow ? (seed.pending ? "pending" : "embedded") : undefined,
    shallow: !!seed.shallow,
    shallowReason: seed.shallow,
    stage: shallowStage,
    outLinkCount: outLinks.length,
    externalLinkCount: external.length,
    isLeaf: outLinks.length === 0,
  };
});

function EXTRACTION_TYPE(seed: Seed): SitePageType | null {
  if ((seed.status ?? 200) !== 200 || seed.pending || seed.path === "/changelog") return null;
  return seed.type;
}

export const PAGE_BY_ID = new Map(PAGES.map((p) => [p.id, p]));
export const PAGE_BY_PATH = new Map(PAGES.map((p) => [pathOf(p.url), p]));

export const SITE: SiteProfile = {
  id: SITE_ID,
  createdAt: ago(41 * DAY),
  updatedAt: ago(2 * HOUR),
  domain: "ledgerly.app",
  name: "Ledgerly",
  status: "active",
  pausedAt: null,
  deletesAt: null,
  markets: ["US", "GB"],
  language: "en",
  repoUrl: "https://github.com/ledgerly/website",
  summary:
    "Ledgerly is bookkeeping software for freelancers and small teams. The site sells a " +
    "monthly subscription with three tiers, documents the product in a public help centre, " +
    "publishes a weekly blog on invoicing, tax and cash flow for self-employed people, and " +
    "carries a set of comparison pages against QuickBooks, FreshBooks, Wave and Xero. The voice is " +
    "plain and slightly dry; it explains rather than sells.",
  socialLinks: [
    { platform: "linkedin", url: "https://www.linkedin.com/company/ledgerly", handle: "ledgerly" },
    { platform: "x", url: "https://x.com/ledgerlyapp", handle: "@ledgerlyapp" },
    { platform: "youtube", url: "https://www.youtube.com/@ledgerly", handle: "@ledgerly" },
  ],
  sitemapUrls: ["https://ledgerly.app/sitemap.xml"],
  sitemapUrlCount: PAGES.filter((p) => p.inSitemap).length,
  sitemapAtRoot: true,
  robotsTxt: "User-agent: *\nAllow: /\nDisallow: /app/\n\nSitemap: https://ledgerly.app/sitemap.xml\n",
  robotsStatus: 200,
  robotsFetchedAt: LAST_CRAWLED_AT,
  llmsTxt: null,
  llmsStatus: 404,
  llmsFetchedAt: LAST_CRAWLED_AT,
  crawlerAccess: {
    checkedAt: LAST_CRAWLED_AT,
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
    checkedAt: LAST_CRAWLED_AT,
    preferred: "https://ledgerly.app",
    sample: "https://ledgerly.app/pricing",
    variants: [
      { kind: "scheme", url: "http://ledgerly.app/pricing", target: "https://ledgerly.app/pricing", verdict: "redirects", status: 301, hops: 1, finalUrl: "https://ledgerly.app/pricing", canonical: null },
      { kind: "host", url: "https://www.ledgerly.app/pricing", target: "https://ledgerly.app/pricing", verdict: "redirects", status: 301, hops: 1, finalUrl: "https://ledgerly.app/pricing", canonical: null },
      { kind: "trailing-slash", url: "https://ledgerly.app/pricing/", target: "https://ledgerly.app/pricing", verdict: "duplicate", status: 200, hops: 0, finalUrl: "https://ledgerly.app/pricing/", canonical: "https://ledgerly.app/pricing" },
    ],
  },
  lastCrawledAt: LAST_CRAWLED_AT,
  gscProperty: "sc-domain:ledgerly.app",
  gaProperty: "properties/384920111",
};

const EXTRACTED_AT = ago(90 * 60_000);

export const EXTRACTIONS = new Map<string, SitePageLlmExtraction>(
  SEEDS.flatMap((seed): Array<[string, SitePageLlmExtraction]> => {
    if ((seed.status ?? 200) !== 200 || seed.pending) return [];
    const id = idFor(seed.path);
    const failed = seed.path === "/changelog";
    return [
      [
        id,
        {
          id: `ple_${hashString(seed.path).toString(36)}`,
          createdAt: EXTRACTED_AT,
          updatedAt: EXTRACTED_AT,
          siteId: SITE_ID,
          pageId: id,
          pageType: failed ? null : seed.type,
          confidence: failed ? undefined : 0.74 + (hashString(seed.path) % 25) / 100,
          extractedFromHash: PAGE_BY_ID.get(id)?.contentHash,
          model: "deepseek/deepseek-v4.1-flash",
          error: failed ? "The page text ran past the model's input limit." : undefined,
          extractedAt: EXTRACTED_AT,
        },
      ],
    ];
  }),
);

function toLink(e: Edge, i: number): SitePageLink {
  const dst = SEED_BY_PATH.get(e.dst);
  return {
    id: `spl_${hashString(`${e.src}>${e.dst}`).toString(36)}${i}`,
    srcPageId: idFor(e.src),
    srcUrl: abs(e.src),
    dstPageId: idFor(e.dst),
    dstUrl: abs(e.dst),
    region: e.region,
    rel: e.rel,
    anchor: e.anchor,
    count: e.count,
    followable: !e.rel?.includes("nofollow"),
    dstCanonical: (dst?.status ?? 200) === 200 && !dst?.noindex,
  };
}

export function pageLinks(id: string) {
  const page = PAGE_BY_ID.get(id);
  if (!page) return null;
  const path = pathOf(page.url);
  return {
    inbound: EDGES.filter((e) => e.dst === path).map(toLink).sort((a, b) => (a.srcUrl ?? "").localeCompare(b.srcUrl ?? "")),
    outbound: EDGES.filter((e) => e.src === path).map(toLink),
    external: EXTERNAL[path] ?? [],
  };
}

const live = PAGES.filter((p) => (p.status ?? 0) >= 200 && (p.status ?? 0) < 300 && !p.blockedByRobots);
const orphanPages = live.filter((p) => p.inlinks === 0 && p.depth !== 0);
const unreachablePages = live.filter((p) => p.inlinks > 0 && p.depth === undefined);
const deepPages = live.filter((p) => (p.depth ?? 0) >= 4);
export const DEEP_FROM = 4;

function discoveryPage(p: SitePage): SiteDiscoveryPage {
  return { id: p.id, url: p.url, title: p.title, pageType: p.pageType ?? null, inlinks: p.inlinks, depth: p.depth, inSitemap: p.inSitemap };
}

const depthBuckets = new Map<number | undefined, number>();
for (const p of live) depthBuckets.set(p.depth, (depthBuckets.get(p.depth) ?? 0) + 1);

export const DISCOVERY: SiteDiscovery = {
  live: live.length,
  homeFound: true,
  orphans: orphanPages.length,
  unreachable: unreachablePages.length,
  deep: deepPages.length,
  deepFrom: DEEP_FROM,
  byDepth: [...depthBuckets.entries()]
    .sort(([a], [b]) => (a ?? 99) - (b ?? 99))
    .map(([depth, n]) => ({ depth, n })),
  orphanPages: orphanPages.map(discoveryPage),
  unreachablePages: unreachablePages.map(discoveryPage),
  deepPages: deepPages.sort((a, b) => (b.depth ?? 0) - (a.depth ?? 0)).map(discoveryPage),
};

function countBy<K>(rows: SitePage[], key: (p: SitePage) => K) {
  const m = new Map<K, number>();
  for (const p of rows) m.set(key(p), (m.get(key(p)) ?? 0) + 1);
  return [...m.entries()];
}

export const PAGE_STATS = (() => {
  const s = (p: SitePage) => p.status ?? 0;
  return {
    pages: PAGES.filter((p) => !p.blockedByRobots).length,
    blockedByRobots: PAGES.filter((p) => p.blockedByRobots).length,
    blockedAndDiscoverable: 0,
    ok: PAGES.filter((p) => s(p) === 200).length,
    errored: PAGES.filter((p) => (s(p) >= 400 || s(p) === 0) && s(p) !== 404 && s(p) !== 410).length,
    gone: PAGES.filter((p) => s(p) === 404 || s(p) === 410).length,
    notInSitemap: PAGES.filter((p) => !p.inSitemap && s(p) === 200).length,
    sitemapMissing: PAGES.filter((p) => p.inSitemap && (s(p) === 404 || s(p) === 410)).length,
    notFound: PAGES.filter((p) => s(p) === 404).length,
    blocked: PAGES.filter((p) => [401, 403, 429].includes(s(p))).length,
    serverError: PAGES.filter((p) => s(p) >= 500).length,
    unreachable: PAGES.filter((p) => s(p) === 0).length,
    orphans: PAGES.filter((p) => p.inSitemap && p.inlinks === 0 && s(p) === 200).length,
    shallow: PAGES.filter((p) => p.shallow).length,
    embedFailed: 0,
    crawlComplete: PAGES.filter((p) => ["indexed", "skipped", "blocked"].includes(p.stage ?? "")).length,
    byStage: countBy(PAGES, (p) => p.stage ?? "pending").map(([stage, n]) => ({ stage, n })),
    byPageType: countBy(PAGES, (p) => p.pageType ?? null).map(([pageType, n]) => ({ pageType, n })),
    byShallowReason: countBy(PAGES.filter((p) => p.shallow), (p) => p.shallowReason ?? null).map(([reason, n]) => ({ reason, n })),
    chunks: { total: 1_386, embedded: 1_372, failed: 0 },
    sitemapUrlCount: SITE.sitemapUrlCount ?? null,
  };
})();

export function searchPassages(p: SitePage): Array<{ text: string; headingPath?: string }> {
  const h1 = p.h1[0];
  const out: Array<{ text: string; headingPath?: string }> = [];
  if (p.bodyText) for (const sentence of p.bodyText.split(/(?<=\.)\s+/)) out.push({ text: sentence, headingPath: h1 });
  if (p.metaDescription) out.push({ text: p.metaDescription, headingPath: h1 });
  if (p.title) out.push({ text: p.title, headingPath: h1 });
  return out;
}

export interface IssueSeed {
  kind: SiteIssueKind;
  issueType: SiteIssueType;
  severity: SiteIssueSeverity;
  issue: string;
  scope: "site" | "pages";
  paths?: string[];
  rejected?: Record<string, string>;
  state?: SiteIssueState;
  reason?: string;
}

const livePaths = (test: (p: SitePage) => boolean) =>
  PAGES.filter((p) => p.status === 200 && test(p)).map((p) => pathOf(p.url));

const deadTargets = new Set(PAGES.filter((p) => p.status === 404 || p.status === 410).map((p) => pathOf(p.url)));
const titleCounts = countBy(PAGES.filter((p) => p.title && p.status === 200), (p) => p.title);
const duplicateTitles = new Set(titleCounts.filter(([, n]) => n > 1).map(([t]) => t));
const STALE_CUTOFF = Date.now() - 365 * DAY;

export const ISSUE_SEEDS: IssueSeed[] = [
  { scope: "site", kind: "ai-crawler-blocked-at-edge", issueType: "static", severity: "p1", issue: "PerplexityBot gets a 403 from the edge while Googlebot, GPTBot and ClaudeBot are let through. Answers about Ledgerly on Perplexity come from third parties instead of the site." },
  { scope: "site", kind: "llms-missing", issueType: "static", severity: "p2", issue: "There is no llms.txt at the site root, so AI assistants have nothing telling them what Ledgerly is or which pages matter." },
  { scope: "site", kind: "trailing-slash-duplicate", issueType: "static", severity: "p3", issue: "/pricing and /pricing/ both answer 200. The canonical tag points at the version without the slash, so search engines merge them, but every page is crawled twice." },
  { scope: "site", kind: "home-missing-google-analytics", issueType: "static", severity: "p3", issue: "The home page carries no Google Analytics tag.", state: "rejected", reason: "We measure traffic server-side on purpose." },
  { scope: "pages", kind: "sitemap-dead-page", issueType: "static", severity: "p0", issue: "The sitemap lists pages that answer 404 or 410. Search engines read dead entries as a sign the whole sitemap is stale.", paths: PAGES.filter((p) => p.inSitemap && deadTargets.has(pathOf(p.url))).map((p) => pathOf(p.url)) },
  { scope: "pages", kind: "broken-internal-link", issueType: "static", severity: "p1", issue: "These pages link to a page that no longer exists. Readers land on a 404 and the link passes nothing.", paths: [...new Set(EDGES.filter((e) => deadTargets.has(e.dst)).map((e) => e.src))] },
  { scope: "pages", kind: "sitemap-redirect", issueType: "static", severity: "p1", issue: "The sitemap lists a URL that redirects. List the page it redirects to instead.", paths: PAGES.filter((p) => p.inSitemap && p.redirectTo).map((p) => pathOf(p.url)) },
  { scope: "pages", kind: "server-error", issueType: "static", severity: "p1", issue: "The page answered with a server error on every attempt.", paths: PAGES.filter((p) => (p.status ?? 0) >= 500).map((p) => pathOf(p.url)) },
  { scope: "pages", kind: "orphan-page", issueType: "static", severity: "p1", issue: "Listed in the sitemap, but no page on the site links to it. Google can find it; a reader cannot, and it inherits no link equity.", paths: orphanPages.map((p) => pathOf(p.url)) },
  { scope: "pages", kind: "internal-link-to-redirect", issueType: "static", severity: "p2", issue: "These pages link to /old-pricing, which redirects to /pricing. Point the link at /pricing directly.", paths: [...new Set(EDGES.filter((e) => e.dst === "/old-pricing").map((e) => e.src))] },
  { scope: "pages", kind: "deep-page", issueType: "static", severity: "p2", issue: `Four or more clicks from the home page. Pages this deep are crawled less often and rarely rank; most of these are older blog posts only reachable through blog pagination.`, paths: deepPages.map((p) => pathOf(p.url)) },
  { scope: "pages", kind: "missing-meta-description", issueType: "static", severity: "p2", issue: "No meta description. Google writes its own snippet from the page, usually a worse one.", paths: livePaths((p) => !p.metaDescription && !p.shallow) },
  { scope: "pages", kind: "duplicate-title", issueType: "static", severity: "p2", issue: "Two pages share the same title, so they compete for the same searches and Google has to guess which one to show.", paths: livePaths((p) => !!p.title && duplicateTitles.has(p.title)) },
  { scope: "pages", kind: "thin-content", issueType: "static", severity: "p2", issue: "Under 300 words of body text. Thin pages rarely rank and can drag down how the rest of the site is judged.", paths: livePaths((p) => !p.shallow && (p.wordCount ?? 0) < 300) },
  { scope: "pages", kind: "title-too-long", issueType: "static", severity: "p3", issue: "The title is wider than 580 pixels and gets cut off in search results.", paths: livePaths((p) => (p.titlePixels ?? 0) > 580) },
  { scope: "pages", kind: "stale-content", issueType: "static", severity: "p3", issue: "The text has not changed in over a year. Fees, limits and screenshots in posts like these go out of date.", paths: livePaths((p) => !!p.contentChangedAt && Date.parse(p.contentChangedAt) < STALE_CUTOFF && !!p.format) },
  { scope: "pages", kind: "image-missing-alt", issueType: "static", severity: "p3", issue: "Images without alt text. Screen readers skip them and image search cannot tell what they show.", paths: livePaths((p) => p.images.some((im) => !im.alt)), rejected: { "/for/cafes": "The hero is decorative; it is meant to have empty alt text." } },
  { scope: "pages", kind: "image-oversized", issueType: "static", severity: "p3", issue: "An image over 1 MB. Compress it or serve WebP; it slows the page on mobile connections.", paths: livePaths((p) => p.images.some((im) => (im.bytes ?? 0) > 1_000_000)) },
  { scope: "pages", kind: "schema-article-incomplete", issueType: "static", severity: "p3", issue: "Article markup without an author. Google uses the author for article rich results and to judge expertise.", paths: livePaths((p) => p.schemaTypes.includes("Article") && !p.author) },
  { scope: "pages", kind: "noindex-but-linked", issueType: "static", severity: "p3", issue: "Marked noindex but linked from indexable pages, so link equity flows into a page Google discards.", paths: livePaths((p) => !!p.robotsDirectives?.includes("noindex") && p.inlinks > 0) },
  { scope: "pages", kind: "url-stop-words", issueType: "static", severity: "p3", issue: "The URL contains stop words such as 'what', 'is' or 'we'.", paths: ["/blog/what-is-accrual-accounting", "/blog/how-we-price-ledgerly"], state: "rejected", reason: "The slugs match the titles and read better this way." },
  { scope: "pages", kind: "js-only-links", issueType: "desktop", severity: "p1", issue: "Links to other tools exist only after JavaScript runs. Crawlers that do not render never see them.", paths: ["/tools/invoice-generator", "/tools/tax-estimator", "/tools/hourly-rate-calculator"] },
  { scope: "pages", kind: "js-only-content", issueType: "desktop", severity: "p1", issue: "The comparison table is injected by JavaScript. Without rendering, the page is an intro paragraph and a footer.", paths: ["/compare/quickbooks", "/compare/freshbooks", "/compare/wave", "/compare/xero"] },
  { scope: "pages", kind: "heavy-javascript", issueType: "desktop", severity: "p2", issue: "More than 1.5 MB of JavaScript runs before the page is usable.", paths: ["/tools/invoice-generator", "/tools/tax-estimator", "/pricing"] },
  { scope: "pages", kind: "third-party-bloat", issueType: "desktop", severity: "p2", issue: "More than 40% of requests go to third parties: chat widget, two analytics scripts and a font host.", paths: ["/", "/pricing", "/blog", "/features/invoicing"] },
  { scope: "pages", kind: "render-console-errors", issueType: "desktop", severity: "p3", issue: "The page logs errors to the console while it renders.", paths: ["/tools/invoice-generator", "/changelog"] },
  { scope: "pages", kind: "render-failed-requests", issueType: "desktop", severity: "p3", issue: "A request failed while the page rendered.", paths: ["/", "/pricing"], state: "rejected", reason: "That is the chat widget's own endpoint; not ours to fix." },
  { scope: "pages", kind: "mobile-hidden-content", issueType: "mobile", severity: "p1", issue: "Text shown on desktop is hidden on mobile. Google indexes the mobile version, so that text does not count.", paths: ["/compare/quickbooks", "/compare/freshbooks", "/compare/wave"] },
  { scope: "pages", kind: "mobile-intrusive-overlay", issueType: "mobile", severity: "p1", issue: "A full-screen newsletter overlay covers the content on mobile before the reader can scroll.", paths: ["/blog/how-to-invoice-as-a-freelancer", "/blog/quarterly-estimated-taxes-explained", "/blog/late-paying-clients"] },
  { scope: "pages", kind: "mobile-small-tap-targets", issueType: "mobile", severity: "p2", issue: "Tap targets smaller than 48 pixels, close enough together that a thumb hits the wrong one.", paths: ["/pricing", "/compare/quickbooks", "/compare/freshbooks", "/templates"] },
  { scope: "pages", kind: "mobile-viewport-overflow", issueType: "mobile", severity: "p2", issue: "Content is wider than the screen on mobile, so the page scrolls sideways.", paths: ["/changelog", "/docs/api"] },
];

export const ISSUE_GROUPS: Array<{ kind: SiteIssueKind; scope: "site" | "pages"; state: SiteIssueState }> = ISSUE_SEEDS.flatMap((seed) => {
  const state = seed.state ?? "open";
  const rejectedPaths = Object.keys(seed.rejected ?? {});
  const rows = [{ kind: seed.kind, scope: seed.scope, state }];
  if (state === "open" && rejectedPaths.length) rows.push({ kind: seed.kind, scope: seed.scope, state: "rejected" });
  return rows;
});

export const RENDERED: Record<SiteRenderDevice, { pages: number; at: string; jobAt: string; total: number }> = {
  desktop: { pages: 40, at: ago(DAY - 14 * 60_000), jobAt: ago(DAY), total: 40 },
  mobile: { pages: 24, at: ago(3 * DAY - 9 * 60_000), jobAt: ago(3 * DAY), total: 24 },
};

export const RENDER_ELIGIBLE = live.filter((p) => !p.shallow).length;

export const CRAWL_JOBS: SiteCrawlJob[] = [
  { daysAgo: 2 / 24, trigger: "schedule", status: "completed" as const, minutes: 11, stopReason: undefined, changed: 6, newPages: 2 },
  { daysAgo: 3, trigger: "user", status: "completed" as const, minutes: 12, stopReason: undefined, changed: 3, newPages: 0 },
  { daysAgo: 6, trigger: "user", status: "cancelled" as const, minutes: 4, stopReason: "stopped by the user", changed: 1, newPages: 0 },
  { daysAgo: 9, trigger: "schedule", status: "completed" as const, minutes: 13, stopReason: undefined, changed: 11, newPages: 4 },
].map((j, i): SiteCrawlJob => {
  const finished = j.daysAgo * DAY;
  const started = finished + j.minutes * 60_000;
  const fetched = j.status === "cancelled" ? 41 : PAGES.length;
  return {
    id: `scj_${(9_000 - i).toString(36)}`,
    createdAt: ago(started),
    updatedAt: ago(finished),
    siteId: SITE_ID,
    status: j.status,
    trigger: j.trigger,
    sitemapUrls: SITE.sitemapUrls,
    startedAt: ago(started),
    finishedAt: ago(finished),
    heartbeatAt: ago(finished),
    discovered: PAGES.length,
    fetched,
    queued: j.status === "cancelled" ? PAGES.length - fetched : 0,
    newPages: j.newPages,
    changed: j.changed,
    unchanged: fetched - j.changed - j.newPages,
    failed: j.status === "cancelled" ? 1 : 3,
    pagesStored: fetched,
    passagesStored: j.status === "cancelled" ? 212 : 1_386,
    complete: j.status === "completed",
    stopReason: j.stopReason,
    notes: [],
  };
});

interface LinkSeed {
  from: string;
  to: string;
  action: LinkSuggestion["action"];
  state: SuggestionState;
  suggestion: string;
  heading?: string;
  passage?: string;
  anchor?: string;
  resolved?: boolean;
}

const LINK_SEEDS: LinkSeed[] = [
  { from: "/blog/late-paying-clients", to: "/templates/late-payment-reminder", action: "create", state: "review_approved", heading: "The reminder sequence", passage: "Send a polite note on the due date and a firm second reminder seven days later. Most late payers pay after the second one, because it reads like a process rather than a favour.", suggestion: "The post describes the reminder emails in prose while the page with the actual templates goes unlinked. Link \"a firm second reminder\" to the reminder templates." },
  { from: "/blog/quickbooks-alternatives", to: "/compare/quickbooks", action: "create", state: "review_approved", heading: "7. Ledgerly", passage: "Ledgerly is the narrowest tool on this list: invoices, expenses, bank feeds and a quarterly tax estimate, for $12 a month. If you are switching from QuickBooks, the side-by-side comparison covers what you would lose.", suggestion: "Ledgerly's own entry in the list never points to the comparison page, which is exactly where a reader choosing between the two should land. Link \"side-by-side comparison\"." },
  { from: "/blog/receipt-tracking-without-losing-your-mind", to: "/features/expenses", action: "create", state: "review_approved", heading: "The one-touch rule", passage: "The rule is simple: attach the receipt to the transaction the moment you pay, and never touch the paper again.", suggestion: "Link \"attach the receipt to the transaction\" to the expenses feature page. The post sells the habit and never says where to do it." },
  { from: "/for/freelancers", to: "/blog/deductible-expenses-freelancers", action: "create", state: "review_approved", heading: "Tax time", passage: "It even keeps track of deductions you would otherwise forget, from software subscriptions to a share of your phone bill.", suggestion: "The freelancer landing page mentions forgotten deductions in passing. The 42-deductions post is the strongest piece on the site for that question and has only four inbound links." },
  { from: "/blog/hourly-vs-project-pricing", to: "/tools/hourly-rate-calculator", action: "create", state: "review_approved", heading: "Working backwards from a salary", passage: "Start from the salary you want, add 30% for tax and overhead, and divide by the hours you can realistically bill. The number is usually higher than people expect.", suggestion: "The calculator answers exactly the question this section raises and is not linked from it. Link \"divide by the hours you can realistically bill\"." },
  { from: "/blog/multi-currency-invoicing", to: "/features/multi-currency", action: "create", state: "review_approved", heading: "Invoice in their currency", passage: "Invoice in the client's currency, get paid into a local account and convert once a month.", suggestion: "Link \"Invoice in the client's currency\" to the multi-currency feature page. It sits two clicks deep with a single inbound body link." },
  { from: "/docs/create-an-invoice", to: "/docs/payment-reminders", action: "create", state: "review_approved", heading: "Send it", passage: "Pick a client, add line items and send. Turn on reminders so Ledgerly chases the payment for you.", suggestion: "The last step says \"turn on reminders\" without a link, and reminders have their own help page." },
  { from: "/blog/case-study-marina-design", to: "/for/designers", action: "create", state: "review_approved", heading: "The problem", passage: "Like most design studios, Marina Design billed by phase and spent the last days of each month matching deposits to invoices by hand.", suggestion: "The case study is about a design studio and never links to the page for design studios. Link \"Like most design studios\"." },
  { from: "/compare/wave", to: "/blog/wave-shutting-down-features", action: "create", state: "review_approved", heading: "Pricing", passage: "Wave's free plan no longer includes bank connections. Ledgerly's Solo plan does, for $12 a month.", suggestion: "The comparison states Wave's plan change without linking the post that explains it. Linking \"no longer includes bank connections\" keeps the claim sourced." },
  { from: "/blog/bookkeeper-or-software", to: "/partners/accountants", action: "create", state: "review_approved", heading: "The hybrid option", passage: "The hybrid option, software all year and a bookkeeper once a year, suits most freelancers. Many bookkeepers already work inside Ledgerly.", suggestion: "Readers who settle on a bookkeeper should find the accountant programme. Link \"Many bookkeepers already work inside Ledgerly\"." },
  { from: "/blog/how-to-invoice-as-a-freelancer", to: "/old-pricing", action: "delete", state: "review_approved", heading: "What we do in Ledgerly", passage: "Ledgerly sends the invoice, takes the card payment and chases it for you. Have a look at our pricing if you want to try it.", anchor: "our pricing", suggestion: "This link goes to /old-pricing, which redirects. Remove it and link /pricing in its place." },
  { from: "/blog/scope-creep", to: "/old-pricing", action: "delete", state: "review_approved", heading: "How Ledgerly handles it", passage: "Every Ledgerly plan includes the additional-requests line; see our pricing for the details.", anchor: "our pricing", suggestion: "A second link into the /old-pricing redirect. Remove it, or point it at /pricing." },
  { from: "/about", to: "/blog/2023-launch-post", action: "delete", state: "review_approved", heading: "Who we are", passage: "We launched in 2023 with three customers and a spreadsheet. You can still read our launch post if you are curious.", anchor: "our launch post", suggestion: "The launch post was deleted and now answers 404. Remove the link from the About page." },
  { from: "/blog/quarterly-estimated-taxes-explained", to: "/features/tax", action: "create", state: "review_approved", heading: "Working out the number", passage: "Estimate every quarter from profit so far, not from last year's return.", suggestion: "Link \"Estimate every quarter\" to the tax feature page.", resolved: true },
  { from: "/blog/1099-nec-guide", to: "/blog/quarterly-estimated-taxes-explained", action: "create", state: "user_rejected", heading: "If you receive one", passage: "If you received a 1099-NEC, nobody withheld tax on that income. It still needs estimated payments.", suggestion: "Link \"estimated payments\" to the quarterly taxes post." },
  { from: "/blog/accounting-terms-glossary", to: "/pricing", action: "create", state: "user_rejected", heading: "Subscription revenue", passage: "Subscription revenue is income billed on a schedule, like a monthly software plan.", suggestion: "Link \"a monthly software plan\" to Ledgerly's pricing." },
  { from: "/blog/freelance-emergency-fund", to: "/features/bank-feeds", action: "create", state: "review_rejected", suggestion: "Link \"see your balance\" to bank feeds." },
  { from: "/blog/profit-first-for-freelancers", to: "/pricing", action: "create", state: "screening_rejected", suggestion: "Link the pricing mention to /pricing." },
  { from: "/docs/zapier", to: "/docs/webhooks", action: "create", state: "screening_approved", suggestion: "Cross-link the two integration docs." },
  { from: "/blog/stripe-fees-bookkeeping", to: "/docs/online-payments", action: "create", state: "draft", suggestion: "Link Stripe fees to the online payments doc." },
  { from: "/blog/paypal-vs-stripe-freelancers", to: "/docs/online-payments", action: "create", state: "draft", suggestion: "Link Stripe setup to the online payments doc." },
];

export const RESOLVED_LINKS = new Set<string>();

export const LINK_SUGGESTIONS: LinkSuggestion[] = LINK_SEEDS.map((s, i) => {
  const id = `sls_${(i + 1).toString().padStart(3, "0")}`;
  if (s.resolved) RESOLVED_LINKS.add(id);
  const at = ago(3 * DAY + i * 37 * 60_000);
  return {
    id,
    createdAt: at,
    updatedAt: s.state === "user_rejected" ? ago(DAY + i * HOUR) : at,
    siteId: SITE_ID,
    jobId: i < 14 ? "ssj_links_2" : "ssj_links_1",
    fromPageId: idFor(s.from),
    fromChunkId: s.passage ? `sch_${hashString(s.from + s.passage).toString(36)}` : null,
    toPageId: idFor(s.to),
    action: s.action,
    state: s.state,
    suggestion: s.suggestion,
    searchScore: s.action === "delete" ? null : Math.round((0.58 + ((i * 7) % 33) / 100) * 100) / 100,
    confidence: ["review_approved", "user_rejected"].includes(s.state) ? 0.72 + ((i * 11) % 26) / 100 : null,
    score: ["review_approved", "user_rejected"].includes(s.state) ? Math.round((0.94 - i * 0.035) * 100) / 100 : null,
    fromUrl: abs(s.from),
    toUrl: abs(s.to),
    fromChunkHeading: s.heading ?? null,
    fromChunkOrdinal: s.passage ? 1 + (i % 4) : null,
    fromChunkText: s.passage ?? null,
    anchor: s.anchor ?? null,
  };
});

function members(paths: string[]): PillarMember[] {
  return paths.map((p) => ({ id: idFor(p), url: abs(p), title: PAGE_BY_PATH.get(p)?.title ?? null }));
}

interface PillarSeed {
  action: PillarSuggestion["action"];
  topic: string;
  covering?: string;
  state: SuggestionState;
  suggestion: string;
  paths: string[];
  resolved?: boolean;
}

const PILLAR_SEEDS: PillarSeed[] = [
  { action: "create", topic: "Getting paid: invoicing, reminders and late fees", state: "review_approved", suggestion: "Eight posts and two templates cover invoicing, reminders, deposits and late fees, and none of them is the page a reader lands on first. A guide at /guides/getting-paid that introduces the topic and links all ten, one paragraph each, would give the cluster a head and stop the posts competing for \"how to get clients to pay\".", paths: ["/blog/how-to-invoice-as-a-freelancer", "/blog/late-paying-clients", "/blog/invoice-payment-terms", "/blog/late-fee-invoice", "/blog/deposit-before-starting", "/blog/invoice-numbering", "/blog/recurring-invoices", "/blog/scope-creep", "/templates/invoice", "/templates/late-payment-reminder"] },
  { action: "expand", topic: "Self-employed tax", covering: "/features/tax", state: "review_approved", suggestion: "/features/tax already ranks for tax questions but links to none of the seven tax posts. Add a \"Learn more\" section that introduces each one in a sentence, and the feature page becomes the hub these posts are missing.", paths: ["/blog/quarterly-estimated-taxes-explained", "/blog/deductible-expenses-freelancers", "/blog/1099-nec-guide", "/blog/home-office-deduction", "/blog/sales-tax-digital-products", "/blog/year-end-checklist-sole-traders", "/blog/tax-season-2025-recap"] },
  { action: "create", topic: "Choosing bookkeeping software", state: "review_approved", suggestion: "Four comparison pages and three posts all answer \"which bookkeeping tool should I use\" from different angles. One page that frames the decision (price, tax features, who it is for) and points to each comparison would stop them splitting the same searches.", paths: ["/compare/quickbooks", "/compare/freshbooks", "/compare/wave", "/compare/xero", "/blog/quickbooks-alternatives", "/blog/best-bookkeeping-software-freelancers", "/blog/bookkeeper-or-software"] },
  { action: "expand", topic: "Cash flow for freelancers", covering: "/features/reports", state: "review_approved", suggestion: "Five posts explain cash flow, reconciliation and emergency funds, and the reports page that shows the cash flow report links to none of them. A short section per post on /features/reports turns it into the place those readers end up.", paths: ["/blog/cash-flow-forecast-small-business", "/blog/profit-first-for-freelancers", "/blog/bank-reconciliation-basics", "/blog/freelance-emergency-fund", "/templates/cash-flow"] },
  { action: "expand", topic: "Templates", covering: "/templates", state: "review_approved", resolved: true, suggestion: "The templates page lists six templates without describing them, and the late payment reminder templates are missing from it. One line per template, plus the missing one, makes it a proper hub.", paths: ["/templates/invoice", "/templates/receipt", "/templates/quote", "/templates/expense-report", "/templates/profit-and-loss", "/templates/cash-flow", "/templates/late-payment-reminder"] },
  { action: "create", topic: "Payment processors", state: "user_rejected", suggestion: "Two posts compare and explain payment processors. A pillar on accepting payments would tie them to the online payments doc.", paths: ["/blog/stripe-fees-bookkeeping", "/blog/paypal-vs-stripe-freelancers", "/docs/online-payments"] },
  { action: "create", topic: "Case studies", state: "review_rejected", suggestion: "Three case studies with no index page.", paths: ["/blog/case-study-marina-design", "/blog/case-study-north-loop-coffee", "/blog/case-study-fieldnotes-consulting"] },
  { action: "create", topic: "Pricing your work", state: "screening_approved", suggestion: "Pricing posts and the hourly rate calculator.", paths: ["/blog/hourly-vs-project-pricing", "/blog/retainers-vs-one-off-projects", "/tools/hourly-rate-calculator"] },
];

export const RESOLVED_PILLARS = new Set<string>();

export const PILLAR_SUGGESTIONS: PillarSuggestion[] = PILLAR_SEEDS.map((s, i) => {
  const id = `spp_${(i + 1).toString().padStart(3, "0")}`;
  if (s.resolved) RESOLVED_PILLARS.add(id);
  const reviewed = ["review_approved", "user_rejected"].includes(s.state);
  return {
    id,
    createdAt: ago(3 * DAY + i * HOUR),
    updatedAt: ago(3 * DAY + i * HOUR),
    siteId: SITE_ID,
    jobId: "ssj_pillars_1",
    action: s.action,
    topic: s.topic,
    memberPageIds: s.paths.map(idFor),
    coveringPageId: s.covering ? idFor(s.covering) : null,
    coveringUrl: s.covering ? abs(s.covering) : null,
    state: s.state,
    suggestion: s.suggestion,
    searchScore: Math.round((0.84 - i * 0.04) * 100) / 100,
    confidence: reviewed ? Math.round((0.9 - i * 0.03) * 100) / 100 : null,
    score: reviewed ? Math.round((0.88 - i * 0.05) * 100) / 100 : null,
    members: members(s.paths),
  };
});

export { pathOf };
