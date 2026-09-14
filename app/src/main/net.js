import { Agent, fetch as pooledFetch } from "undici";

function positive(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

const MAX_OUTBOUND = positive(process.env.MEELU_CRAWL_MAX_OUTBOUND, 12);
const PER_ORIGIN = positive(process.env.MEELU_CRAWL_PER_ORIGIN, 6);

const crawlDispatcher = new Agent({
  connections: PER_ORIGIN,
  keepAliveTimeout: 10_000,
  keepAliveMaxTimeout: 60_000,
  connectTimeout: 10_000,
});

const apiDispatcher = new Agent({
  connections: positive(process.env.MEELU_API_CONNECTIONS, 8),
  keepAliveTimeout: 30_000,
  keepAliveMaxTimeout: 120_000,
});

let inFlight = 0;
const waiting = [];

function acquire() {
  if (inFlight < MAX_OUTBOUND) {
    inFlight += 1;
    return Promise.resolve();
  }
  return new Promise((resolve) => waiting.push(resolve));
}

function release() {
  const next = waiting.shift();
  if (next) {
    next();
    return;
  }
  inFlight -= 1;
}

export async function withOutboundSlot(work) {
  await acquire();
  try {
    return await work();
  } finally {
    release();
  }
}

export function crawlFetch(url, init = {}) {
  return pooledFetch(url, { ...init, dispatcher: crawlDispatcher });
}

export function apiFetch(url, init = {}) {
  return pooledFetch(url, { ...init, dispatcher: apiDispatcher });
}
