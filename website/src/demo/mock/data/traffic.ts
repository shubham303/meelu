import { DAY, dayKey, NOW, seeded } from "../rand";
import { PAGE_BY_PATH } from "./site";

const MAX_DAYS = 400;

const CHANNELS: Array<[string, number, number, number]> = [
  ["Organic Search", 0.46, 0.62, 0.031],
  ["Direct", 0.24, 0.58, 0.044],
  ["Referral", 0.11, 0.55, 0.028],
  ["Organic Social", 0.08, 0.49, 0.019],
  ["Email", 0.06, 0.71, 0.062],
  ["Paid Search", 0.03, 0.52, 0.037],
  ["Unassigned", 0.02, 0.3, 0.004],
];

interface DayRow {
  sessions: number;
  users: number;
  newUsers: number;
  engaged: number;
  pageViews: number;
  engagementSeconds: number;
  keyEvents: number;
  revenue: number;
  byChannel: Record<string, { sessions: number; engaged: number; keyEvents: number; revenue: number }>;
}

const rng = seeded(101);

export const DAYS: DayRow[] = Array.from({ length: MAX_DAYS }, (_, idx) => {
  const d = MAX_DAYS - 1 - idx;
  const trend = 1 + ((MAX_DAYS - d) / MAX_DAYS) * 0.7;
  const dow = new Date(NOW - d * DAY).getUTCDay();
  const weekday = dow === 0 || dow === 6 ? 0.6 : 1;
  const spike = d === 37 || d === 38 ? 2.4 : 1;
  const sessions = Math.round(1180 * trend * weekday * spike * (0.8 + rng() * 0.4));
  const byChannel: DayRow["byChannel"] = {};
  let engaged = 0;
  let keyEvents = 0;
  let revenue = 0;
  for (const [name, share, engRate, convRate] of CHANNELS) {
    const s = Math.round(sessions * share * (0.85 + rng() * 0.3));
    const e = Math.round(s * engRate);
    const k = Math.round(s * convRate);
    const r = k * (name === "Paid Search" ? 14.2 : 12) * (0.7 + rng() * 0.6);
    byChannel[name] = { sessions: s, engaged: e, keyEvents: k, revenue: r };
    engaged += e;
    keyEvents += k;
    revenue += r;
  }
  return {
    sessions,
    users: Math.round(sessions * 0.82),
    newUsers: Math.round(sessions * 0.61),
    engaged,
    pageViews: Math.round(sessions * 2.3),
    engagementSeconds: Math.round(sessions * 74),
    keyEvents,
    revenue,
    byChannel,
  };
});

function window_(days: number, shift = 0) {
  return DAYS.slice(Math.max(0, DAYS.length - days - shift), DAYS.length - shift);
}

export function totals(days: number, shift = 0) {
  const rows = window_(days, shift);
  const t = { users: 0, newUsers: 0, sessions: 0, engagedSessions: 0, pageViews: 0, engagementSeconds: 0, keyEvents: 0, revenue: 0 };
  for (const r of rows) {
    t.users += r.users;
    t.newUsers += r.newUsers;
    t.sessions += r.sessions;
    t.engagedSessions += r.engaged;
    t.pageViews += r.pageViews;
    t.engagementSeconds += r.engagementSeconds;
    t.keyEvents += r.keyEvents;
    t.revenue += r.revenue;
  }
  return t;
}

export function channelTotals(days: number, shift = 0) {
  const rows = window_(days, shift);
  const out: Record<string, { sessions: number; engagedSessions: number; keyEvents: number; revenue: number }> = {};
  for (const r of rows) {
    for (const [name, c] of Object.entries(r.byChannel)) {
      const o = (out[name] ??= { sessions: 0, engagedSessions: 0, keyEvents: 0, revenue: 0 });
      o.sessions += c.sessions;
      o.engagedSessions += c.engaged;
      o.keyEvents += c.keyEvents;
      o.revenue += c.revenue;
    }
  }
  return out;
}

export function channelRows(days: number) {
  const cur = channelTotals(days);
  const prev = channelTotals(days, days);
  return CHANNELS.map(([name]) => ({
    key: [name],
    sessions: cur[name]?.sessions ?? 0,
    prevSessions: prev[name]?.sessions ?? 0,
    users: Math.round((cur[name]?.sessions ?? 0) * 0.82),
    engagedSessions: cur[name]?.engagedSessions ?? 0,
    keyEvents: cur[name]?.keyEvents ?? 0,
    revenue: cur[name]?.revenue ?? 0,
  }));
}

export function seriesPoints(days: number) {
  return window_(days).map((r, i) => ({
    day: dayKey(days - i),
    users: r.users,
    sessions: r.sessions,
    engagedSessions: r.engaged,
    pageViews: r.pageViews,
    keyEvents: r.keyEvents,
    revenue: r.revenue,
    organicSessions: r.byChannel["Organic Search"]?.sessions ?? 0,
  }));
}

const LANDING_WEIGHTS: Array<[string, number]> = [
  ["/", 0.19],
  ["/templates/invoice", 0.12],
  ["/pricing", 0.07],
  ["/blog/how-to-invoice-as-a-freelancer", 0.06],
  ["/blog/quarterly-estimated-taxes-explained", 0.055],
  ["/compare/quickbooks", 0.05],
  ["/tools/invoice-generator", 0.045],
  ["/blog/deductible-expenses-freelancers", 0.04],
  ["/blog/late-paying-clients", 0.035],
  ["/templates/late-payment-reminder", 0.03],
  ["/blog/quickbooks-alternatives", 0.028],
  ["/features/invoicing", 0.025],
  ["/blog/1099-nec-guide", 0.022],
  ["/tools/tax-estimator", 0.02],
  ["/compare/freshbooks", 0.018],
  ["/for/freelancers", 0.016],
  ["/templates/quote", 0.015],
  ["/blog/home-office-deduction", 0.014],
  ["/docs/getting-started", 0.013],
  ["/blog/stripe-fees-bookkeeping", 0.012],
  ["/features/tax", 0.011],
  ["/compare/wave", 0.01],
  ["/blog/cash-flow-forecast-small-business", 0.009],
  ["/about", 0.008],
  ["/tools/hourly-rate-calculator", 0.008],
  ["/templates/profit-and-loss", 0.007],
  ["/blog/multi-currency-invoicing", 0.007],
  ["/features/expenses", 0.006],
  ["/docs/connect-your-bank", 0.006],
  ["/blog/invoice-payment-terms", 0.005],
  ["/blog/recurring-invoices", 0.005],
  ["/blog/hourly-vs-project-pricing", 0.004],
  ["/blog/best-bookkeeping-software-freelancers", 0.004],
  ["/for/consultants", 0.003],
  ["/blog/sales-tax-digital-products", 0.003],
  ["/changelog", 0.003],
];

export function landingRows(days: number) {
  const cur = totals(days);
  const prev = totals(days, days);
  const lrng = seeded(days);
  return LANDING_WEIGHTS.map(([path, w]) => {
    const page = PAGE_BY_PATH.get(path);
    const sessions = Math.round(cur.sessions * w);
    return {
      landingPage: path,
      title: page?.title ?? null,
      sessions,
      prevSessions: Math.round(prev.sessions * w * (0.8 + lrng() * 0.4)),
      engagedSessions: Math.round(sessions * (0.45 + lrng() * 0.3)),
      keyEvents: Math.round(sessions * (path === "/pricing" ? 0.09 : 0.025 + lrng() * 0.02)),
      revenue: Math.round(sessions * (path === "/pricing" ? 0.09 : 0.02) * 12 * 100) / 100,
    };
  });
}

export function contentRows(days: number) {
  const cur = totals(days);
  const prev = totals(days, days);
  const crng = seeded(days + 7);
  return [["/pricing", 0.16], ["/docs/getting-started", 0.04], ["/features/invoicing", 0.05], ...LANDING_WEIGHTS.filter(([p]) => p !== "/pricing" && p !== "/docs/getting-started" && p !== "/features/invoicing")].map(([path, w]) => {
    const views = Math.round(cur.pageViews * (w as number) * 0.9);
    const users = Math.round(views * 0.7);
    return {
      pagePath: path as string,
      views,
      prevViews: Math.round(prev.pageViews * (w as number) * 0.9 * (0.8 + crng() * 0.4)),
      users,
      engagementSeconds: Math.round(users * (30 + crng() * 120)),
      keyEvents: Math.round(views * 0.02),
    };
  });
}

const BREAKDOWNS: Record<string, Array<[string[], number]>> = {
  source: [
    [["google", "organic"], 0.44],
    [["(direct)", "(none)"], 0.24],
    [["bing", "organic"], 0.03],
    [["producthunt.com", "referral"], 0.028],
    [["news.ycombinator.com", "referral"], 0.024],
    [["linkedin.com", "social"], 0.03],
    [["reddit.com", "referral"], 0.021],
    [["substack", "email"], 0.032],
    [["newsletter", "email"], 0.028],
    [["x.com", "social"], 0.022],
    [["duckduckgo", "organic"], 0.012],
    [["google", "cpc"], 0.03],
    [["indiehackers.com", "referral"], 0.011],
    [["youtube.com", "social"], 0.014],
    [["chatgpt.com", "referral"], 0.009],
    [["perplexity.ai", "referral"], 0.003],
  ],
  event: [
    [["page_view"], 2.3],
    [["session_start"], 1.0],
    [["first_visit"], 0.61],
    [["scroll"], 0.72],
    [["click"], 0.38],
    [["template_download"], 0.061],
    [["signup_started"], 0.048],
    [["signup_completed"], 0.031],
    [["pricing_viewed"], 0.14],
    [["file_download"], 0.02],
  ],
  country: [
    [["United States"], 0.52],
    [["United Kingdom"], 0.13],
    [["Canada"], 0.08],
    [["Australia"], 0.06],
    [["Germany"], 0.04],
    [["India"], 0.04],
    [["Netherlands"], 0.02],
    [["Ireland"], 0.02],
    [["France"], 0.015],
    [["Portugal"], 0.012],
    [["Other"], 0.043],
  ],
  device: [
    [["desktop"], 0.61],
    [["mobile"], 0.36],
    [["tablet"], 0.03],
  ],
  os: [
    [["Macintosh"], 0.34],
    [["Windows"], 0.27],
    [["iOS"], 0.22],
    [["Android"], 0.14],
    [["Linux"], 0.02],
    [["Chrome OS"], 0.01],
  ],
  browser: [
    [["Chrome"], 0.58],
    [["Safari"], 0.27],
    [["Firefox"], 0.06],
    [["Edge"], 0.06],
    [["Samsung Internet"], 0.02],
    [["Opera"], 0.01],
  ],
};

export function breakdownRows(by: string, days: number) {
  const cur = totals(days);
  const prev = totals(days, days);
  const brng = seeded(days + by.length);
  const list = BREAKDOWNS[by] ?? BREAKDOWNS.source;
  return list.map(([key, w]) => {
    const sessions = Math.round(cur.sessions * w);
    return {
      key,
      sessions,
      prevSessions: Math.round(prev.sessions * w * (0.82 + brng() * 0.36)),
      users: Math.round(sessions * 0.82),
      engagedSessions: Math.round(sessions * (0.5 + brng() * 0.25)),
      keyEvents: Math.round(sessions * 0.03),
      revenue: Math.round(sessions * 0.03 * 12 * 100) / 100,
    };
  });
}

export const TRAFFIC_FIRST_DAY = dayKey(MAX_DAYS - 1);
export const TRAFFIC_LAST_DAY = dayKey(1);
export const CHANNEL_NAMES = CHANNELS.map(([n]) => n);
export const DAYS_STORED = MAX_DAYS;

export function channelShare(channel: string): number {
  return CHANNELS.find(([name]) => name === channel)?.[1] ?? 0;
}
