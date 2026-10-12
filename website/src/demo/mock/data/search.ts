import { DAY, dayKey, hashString, NOW, seeded } from "../rand";
import { ORIGIN, PAGES } from "./site";

const MAX_DAYS = 480;

const rng = seeded(31);

interface Daily {
  clicks: number;
  impressions: number;
  position: number;
}

function series(base: number, ctr: number, pos: number, offset: number): Daily[] {
  const out: Daily[] = [];
  for (let d = MAX_DAYS - 1; d >= 0; d--) {
    const trend = 1 + ((MAX_DAYS - d) / MAX_DAYS) * 0.9;
    const dow = new Date(NOW - d * DAY).getUTCDay();
    const weekday = dow === 0 || dow === 6 ? 0.55 : 1;
    const noise = 0.75 + rng() * 0.5;
    const impressions = Math.round(base * trend * weekday * noise + offset);
    const clicks = Math.round(impressions * ctr * (0.85 + rng() * 0.3));
    out.push({ clicks, impressions, position: pos + (rng() - 0.5) * 1.6 - (MAX_DAYS - d) / MAX_DAYS });
  }
  return out;
}

const PAGE_WEIGHTS: Array<[string, number, number, number]> = [
  ["/", 620, 0.062, 4.2],
  ["/pricing", 210, 0.081, 3.1],
  ["/templates/invoice", 1480, 0.048, 6.8],
  ["/blog/how-to-invoice-as-a-freelancer", 940, 0.041, 8.4],
  ["/blog/quarterly-estimated-taxes-explained", 880, 0.037, 9.1],
  ["/compare/quickbooks", 720, 0.052, 7.2],
  ["/blog/quickbooks-alternatives", 690, 0.033, 11.4],
  ["/blog/deductible-expenses-freelancers", 610, 0.039, 10.2],
  ["/blog/late-paying-clients", 560, 0.044, 8.9],
  ["/tools/invoice-generator", 530, 0.058, 6.1],
  ["/templates/late-payment-reminder", 470, 0.046, 7.7],
  ["/blog/1099-nec-guide", 450, 0.035, 12.3],
  ["/features/invoicing", 380, 0.051, 9.8],
  ["/compare/freshbooks", 350, 0.049, 8.1],
  ["/blog/home-office-deduction", 340, 0.031, 13.6],
  ["/tools/tax-estimator", 320, 0.055, 7.4],
  ["/templates/quote", 300, 0.042, 9.3],
  ["/blog/best-bookkeeping-software-freelancers", 290, 0.029, 14.8],
  ["/blog/cash-flow-forecast-small-business", 270, 0.034, 12.9],
  ["/compare/wave", 250, 0.047, 8.6],
  ["/blog/invoice-payment-terms", 240, 0.04, 11.1],
  ["/features/tax", 220, 0.046, 10.4],
  ["/templates/profit-and-loss", 210, 0.043, 9.9],
  ["/blog/stripe-fees-bookkeeping", 190, 0.036, 12.7],
  ["/blog/multi-currency-invoicing", 180, 0.038, 13.2],
  ["/for/freelancers", 170, 0.05, 9.6],
  ["/blog/recurring-invoices", 160, 0.037, 12.1],
  ["/features/expenses", 150, 0.048, 11.7],
  ["/blog/sales-tax-digital-products", 140, 0.03, 15.4],
  ["/blog/hourly-vs-project-pricing", 130, 0.033, 14.1],
  ["/tools/hourly-rate-calculator", 120, 0.052, 8.8],
  ["/blog/bank-reconciliation-basics", 110, 0.031, 16.2],
  ["/blog/chart-of-accounts-freelancer", 100, 0.034, 13.9],
  ["/docs/connect-your-bank", 90, 0.12, 2.4],
  ["/docs/getting-started", 80, 0.14, 1.9],
  ["/compare/xero", 75, 0.045, 12.6],
  ["/blog/deposit-before-starting", 70, 0.039, 14.4],
  ["/blog/late-fee-invoice", 65, 0.041, 15.1],
  ["/about", 60, 0.09, 3.3],
  ["/blog/accounting-terms-glossary", 55, 0.027, 18.7],
  ["/blog/year-end-checklist-sole-traders", 50, 0.032, 17.3],
  ["/blog/case-study-marina-design", 30, 0.05, 19.8],
];

export const PAGE_SERIES = new Map<string, Daily[]>(
  PAGE_WEIGHTS.map(([path, base, ctr, pos], i) => [`${ORIGIN}${path}`, series(base, ctr, pos, i % 3)]),
);

export const FIRST_DAY = dayKey(MAX_DAYS - 1);
export const LAST_DAY = dayKey(1);

export function totalsFor(url: string | null, days: number, shift = 0) {
  const lists = url ? [PAGE_SERIES.get(url) ?? []] : [...PAGE_SERIES.values()];
  let clicks = 0;
  let impressions = 0;
  let posWeighted = 0;
  for (const list of lists) {
    const slice = list.slice(Math.max(0, list.length - days - shift), list.length - shift);
    for (const d of slice) {
      clicks += d.clicks;
      impressions += d.impressions;
      posWeighted += d.position * d.impressions;
    }
  }
  return {
    clicks,
    impressions,
    ctr: impressions ? clicks / impressions : null,
    position: impressions ? posWeighted / impressions : null,
  };
}

export function pointsFor(url: string | null, days: number) {
  const lists = url ? [PAGE_SERIES.get(url) ?? []] : [...PAGE_SERIES.values()];
  const out = [];
  for (let d = days; d >= 1; d--) {
    let clicks = 0;
    let impressions = 0;
    let posWeighted = 0;
    for (const list of lists) {
      const row = list[list.length - d];
      if (!row) continue;
      clicks += row.clicks;
      impressions += row.impressions;
      posWeighted += row.position * row.impressions;
    }
    out.push({
      day: dayKey(d),
      clicks,
      impressions,
      ctr: impressions ? clicks / impressions : null,
      position: impressions ? posWeighted / impressions : null,
    });
  }
  return out;
}

export function pageRows(days: number) {
  return [...PAGE_SERIES.keys()].map((url) => {
    const cur = totalsFor(url, days);
    const prev = totalsFor(url, days, days);
    const page = PAGES.find((p) => p.url === url);
    return {
      page: url,
      clicks: cur.clicks,
      prevClicks: prev.clicks,
      impressions: cur.impressions,
      position: cur.position,
      indexState: page?.indexState ?? null,
      coverageState: page?.coverageState ?? null,
      googleCanonical: page?.googleCanonical ?? null,
      lastCrawlTime: page?.lastCrawledAt ?? null,
      indexCheckedAt: page?.indexCheckedAt ?? null,
    };
  });
}

const QUERY_SEEDS: Array<[string, string, number, number]> = [
  ["invoice template", "/templates/invoice", 0.09, 6.2],
  ["free invoice template", "/templates/invoice", 0.07, 7.1],
  ["invoice template word", "/templates/invoice", 0.03, 9.4],
  ["how to invoice as a freelancer", "/blog/how-to-invoice-as-a-freelancer", 0.06, 5.8],
  ["freelance invoice", "/blog/how-to-invoice-as-a-freelancer", 0.04, 8.9],
  ["quarterly estimated taxes", "/blog/quarterly-estimated-taxes-explained", 0.05, 7.6],
  ["estimated taxes self employed", "/blog/quarterly-estimated-taxes-explained", 0.02, 11.3],
  ["1040-es", "/blog/quarterly-estimated-taxes-explained", 0.01, 14.8],
  ["quickbooks alternative", "/compare/quickbooks", 0.05, 8.2],
  ["quickbooks alternatives", "/blog/quickbooks-alternatives", 0.02, 11.9],
  ["ledgerly vs quickbooks", "/compare/quickbooks", 0.31, 1.4],
  ["ledgerly", "/", 0.58, 1.1],
  ["ledgerly pricing", "/pricing", 0.42, 1.2],
  ["ledgerly app", "/", 0.5, 1.3],
  ["ledgerly login", "/", 0.6, 1.0],
  ["freelance tax deductions", "/blog/deductible-expenses-freelancers", 0.03, 10.4],
  ["what can i deduct as a freelancer", "/blog/deductible-expenses-freelancers", 0.05, 9.2],
  ["client not paying invoice", "/blog/late-paying-clients", 0.06, 6.9],
  ["late payment reminder email", "/templates/late-payment-reminder", 0.05, 8.1],
  ["payment reminder template", "/templates/late-payment-reminder", 0.04, 9.7],
  ["invoice generator", "/tools/invoice-generator", 0.02, 13.5],
  ["free invoice generator", "/tools/invoice-generator", 0.03, 11.2],
  ["1099 nec", "/blog/1099-nec-guide", 0.01, 17.8],
  ["1099-nec explained", "/blog/1099-nec-guide", 0.06, 8.4],
  ["freshbooks alternative", "/compare/freshbooks", 0.05, 8.6],
  ["freshbooks vs ledgerly", "/compare/freshbooks", 0.28, 1.5],
  ["home office deduction", "/blog/home-office-deduction", 0.01, 19.3],
  ["home office deduction freelancer", "/blog/home-office-deduction", 0.04, 10.8],
  ["self employed tax calculator", "/tools/tax-estimator", 0.03, 12.1],
  ["freelance tax estimator", "/tools/tax-estimator", 0.06, 7.9],
  ["quote template", "/templates/quote", 0.04, 9.8],
  ["best bookkeeping software for freelancers", "/blog/best-bookkeeping-software-freelancers", 0.03, 12.4],
  ["bookkeeping software freelancers", "/blog/best-bookkeeping-software-freelancers", 0.02, 14.6],
  ["cash flow forecast template", "/blog/cash-flow-forecast-small-business", 0.03, 12.8],
  ["wave accounting alternative", "/compare/wave", 0.05, 8.3],
  ["invoice payment terms", "/blog/invoice-payment-terms", 0.04, 10.6],
  ["net 30 meaning", "/blog/invoice-payment-terms", 0.02, 13.7],
  ["profit and loss template", "/templates/profit-and-loss", 0.03, 10.1],
  ["stripe fees accounting", "/blog/stripe-fees-bookkeeping", 0.05, 9.9],
  ["how to record stripe fees", "/blog/stripe-fees-bookkeeping", 0.06, 8.7],
  ["multi currency invoice", "/blog/multi-currency-invoicing", 0.04, 11.4],
  ["bookkeeping for freelancers", "/for/freelancers", 0.04, 10.9],
  ["recurring invoice", "/blog/recurring-invoices", 0.03, 12.3],
  ["expense tracking app", "/features/expenses", 0.02, 15.9],
  ["sales tax digital products", "/blog/sales-tax-digital-products", 0.03, 13.1],
  ["hourly rate calculator", "/tools/hourly-rate-calculator", 0.04, 9.1],
  ["freelance hourly rate calculator", "/tools/hourly-rate-calculator", 0.06, 7.3],
  ["hourly vs project pricing", "/blog/hourly-vs-project-pricing", 0.05, 8.8],
  ["bank reconciliation", "/blog/bank-reconciliation-basics", 0.01, 21.4],
  ["chart of accounts for freelancers", "/blog/chart-of-accounts-freelancer", 0.05, 10.3],
  ["xero alternative", "/compare/xero", 0.03, 12.7],
  ["deposit invoice", "/blog/deposit-before-starting", 0.03, 13.3],
  ["late fee on invoice", "/blog/late-fee-invoice", 0.04, 11.6],
  ["accounting terms", "/blog/accounting-terms-glossary", 0.01, 22.9],
  ["year end bookkeeping checklist", "/blog/year-end-checklist-sole-traders", 0.03, 14.2],
  ["connect bank ledgerly", "/docs/connect-your-bank", 0.34, 1.6],
  ["ledgerly api", "/docs/api", 0.4, 1.3],
  ["bookkeeping app for consultants", "/for/consultants", 0.04, 11.8],
  ["invoice numbering", "/blog/invoice-numbering", 0.03, 12.9],
];

export function queryRows(days: number, pages: string[] | null) {
  const qrng = seeded(17 + days);
  const rows = QUERY_SEEDS.map(([query, path, ctr, pos]) => {
    const url = `${ORIGIN}${path}`;
    const pageTotal = totalsFor(url, days);
    const share = 0.08 + qrng() * 0.3;
    const impressions = Math.round(pageTotal.impressions * share);
    const clicks = Math.round(impressions * ctr);
    const page = PAGES.find((p) => p.url === url);
    return { query, page: url, inlinks: page?.inlinks ?? null, clicks, impressions, position: pos + (qrng() - 0.5) };
  });
  const filtered = pages && pages.length ? rows.filter((r) => pages.some((p) => p.replace(/\/$/, "") === r.page.replace(/\/$/, ""))) : rows;
  return filtered.sort((a, b) => b.clicks - a.clicks);
}

export function strikingRows() {
  return queryRows(28, null)
    .filter((r) => r.position !== null && r.position > 10 && r.position <= 20)
    .sort((a, b) => b.impressions - a.impressions);
}

export function indexationCounts() {
  const counts: Record<string, number> = {};
  for (const p of PAGES) {
    const key = p.indexState ?? "unknown";
    counts[key] = (counts[key] ?? 0) + 1;
  }
  return counts;
}

export function seedFor(s: string): number {
  return hashString(s);
}
