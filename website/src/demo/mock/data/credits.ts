import { DAY, HOUR, NOW, between, int, pick, seeded } from "../rand";

export const SITE_DAILY_USD = 1;
export const SITE_DAILY_DISCOUNTED_USD = 0.5;
export const FULL_PRICE_SITES = 5;
export const TRIAL_DAYS = 1;
export const MIN_TOPUP_USD = 5;
export const MAX_TOPUP_USD = 500;
export const PAUSED_RETENTION_DAYS = 30;
export const ACCOUNT_AGE_DAYS = 41;
export const FIRST_SITE_ADDED_MS = ACCOUNT_AGE_DAYS * DAY - 7 * HOUR;

export type LedgerKind = "purchase" | "grant" | "usage" | "site_day";

export interface LedgerEntry {
  id: string;
  kind: LedgerKind;
  deltaMicros: number;
  balanceAfterMicros: number;
  deltaUsd: number;
  balanceAfterUsd: number;
  providerCallId: string | null;
  note: string | null;
  createdAt: string;
}

export type PaymentStatus = "pending" | "succeeded" | "failed" | "cancelled";

export interface Payment {
  id: string;
  status: PaymentStatus;
  creditMicros: number;
  creditUsd: number;
  checkoutUrl: string | null;
  paidAmount: number | null;
  paidCurrency: string | null;
  creditedAt: string | null;
  createdAt: string;
}

export interface SiteBilling {
  siteId: string;
  status: "active" | "disabled";
  lastChargedAt: string | null;
  nextChargeAt: string | null;
  chargeCount: number;
  chargedMicros: number;
  dailyPriceMicros: number;
}

export function micros(usd: number): number {
  return Math.round(usd * 1_000_000);
}

export function usd(value: number): number {
  return Math.round(value) / 1_000_000;
}

export function sitePriceMicros(earlierSites: number): number {
  return micros(earlierSites < FULL_PRICE_SITES ? SITE_DAILY_USD : SITE_DAILY_DISCOUNTED_USD);
}

interface Event {
  at: number;
  kind: LedgerKind;
  deltaMicros: number;
  note: string;
  providerCallId?: string;
}

interface PaymentSeed {
  daysAgo: number;
  amountUsd: number;
  status: PaymentStatus;
  ref: string;
}

const PAYMENT_SEEDS: PaymentSeed[] = [
  { daysAgo: 40.97, amountUsd: 20, status: "succeeded", ref: "pay_0Nx4Lw2QhT8bVd" },
  { daysAgo: 22.3, amountUsd: 20, status: "cancelled", ref: "pay_0Pa7Rk9DmV1sXe" },
  { daysAgo: 21.4, amountUsd: 50, status: "failed", ref: "pay_0Qc2Hn6TyK3pZa" },
  { daysAgo: 21.39, amountUsd: 50, status: "succeeded", ref: "pay_0Qc9Jm1WbF5rLo" },
];

const USAGE: { note: string; weight: number; lo: number; hi: number }[] = [
  { note: "llm/anthropic/claude-haiku-5.5", weight: 30, lo: 0.018, hi: 0.31 },
  { note: "llm/deepseek/deepseek-v4-flash", weight: 10, lo: 0.0004, hi: 0.0042 },
  { note: "llm/openai/gpt-6-luna", weight: 3, lo: 0.03, hi: 0.42 },
  { note: "json-data-extractor/decide", weight: 6, lo: 0.0006, hi: 0.0031 },
  { note: "seo-data/serp.organic", weight: 7, lo: 0.002, hi: 0.006 },
  { note: "seo-data/keywords.ideas", weight: 3, lo: 0.011, hi: 0.024 },
  { note: "seo-data/keywords.related", weight: 2, lo: 0.011, hi: 0.019 },
  { note: "seo-data/domains.ranked_keywords", weight: 2, lo: 0.021, hi: 0.062 },
  { note: "seo-data/domains.competitors", weight: 1, lo: 0.012, hi: 0.03 },
  { note: "seo-data/backlinks.pages_summary", weight: 1, lo: 0.02, hi: 0.024 },
  { note: "social-listening/search.reddit", weight: 5, lo: 0.018, hi: 0.092 },
  { note: "social-listening/search.x", weight: 3, lo: 0.012, hi: 0.06 },
  { note: "social-listening/search.linkedin", weight: 1, lo: 0.02, hi: 0.07 },
];

const WEIGHTED = USAGE.flatMap((u) => Array.from({ length: u.weight }, () => u));

function callId(rng: () => number): string {
  return `pc_${Math.floor(rng() * 36 ** 8).toString(36).padStart(8, "0")}`;
}

function buildEvents(): Event[] {
  const rng = seeded(4127);
  const events: Event[] = [];

  for (const p of PAYMENT_SEEDS) {
    if (p.status !== "succeeded") continue;
    events.push({
      at: NOW - p.daysAgo * DAY + 2 * 60_000,
      kind: "purchase",
      deltaMicros: micros(p.amountUsd),
      note: `Top-up $${p.amountUsd.toFixed(2)} · ${p.ref}`,
    });
  }

  for (let n = TRIAL_DAYS + 1; ; n++) {
    const at = NOW - FIRST_SITE_ADDED_MS + n * DAY;
    if (at > NOW) break;
    events.push({ at, kind: "site_day", deltaMicros: -sitePriceMicros(0), note: "ledgerly.app · one day" });
  }

  for (let d = ACCOUNT_AGE_DAYS - 1; d >= 0; d--) {
    const busy = d > 30 ? 6 : 4;
    const count = int(rng, Math.max(1, busy - 3), busy + 3);
    for (let i = 0; i < count; i++) {
      const offset = between(rng, 8, 22) * HOUR;
      const at = NOW - d * DAY - DAY + offset;
      if (at > NOW - 20 * 60_000 || at < NOW - FIRST_SITE_ADDED_MS + HOUR) continue;
      const u = pick(rng, WEIGHTED);
      events.push({
        at,
        kind: "usage",
        deltaMicros: -micros(between(rng, u.lo, u.hi)),
        note: u.note,
        providerCallId: callId(rng),
      });
    }
  }

  return events.sort((a, b) => a.at - b.at);
}

function buildLedger(): { entries: LedgerEntry[]; balanceMicros: number } {
  let balance = 0;
  const entries = buildEvents().map((e, i) => {
    balance += e.deltaMicros;
    return {
      id: `lg_${(i + 1).toString().padStart(4, "0")}`,
      kind: e.kind,
      deltaMicros: e.deltaMicros,
      balanceAfterMicros: balance,
      deltaUsd: usd(e.deltaMicros),
      balanceAfterUsd: usd(balance),
      providerCallId: e.providerCallId ?? null,
      note: e.note,
      createdAt: new Date(e.at).toISOString(),
    } satisfies LedgerEntry;
  });
  return { entries: entries.reverse(), balanceMicros: balance };
}

const built = buildLedger();

export const LEDGER: LedgerEntry[] = built.entries;
export const BALANCE_MICROS: number = built.balanceMicros;

export const PAYMENTS: Payment[] = PAYMENT_SEEDS.map((p, i) => {
  const created = NOW - p.daysAgo * DAY;
  const cents = Math.round(p.amountUsd * 100);
  return {
    id: `paym_${(i + 1).toString().padStart(3, "0")}`,
    status: p.status,
    creditMicros: micros(p.amountUsd),
    creditUsd: p.amountUsd,
    checkoutUrl: p.status === "pending" ? "https://checkout.dodopayments.com/session/demo" : null,
    paidAmount: p.status === "succeeded" ? cents : null,
    paidCurrency: p.status === "succeeded" ? "USD" : null,
    creditedAt: p.status === "succeeded" ? new Date(created + 2 * 60_000).toISOString() : null,
    createdAt: new Date(created).toISOString(),
  } satisfies Payment;
}).reverse();
