import { Agent, buildConnector, fetch as pooledFetch } from "undici";
import { isPrivateAddress, privateHostError, publicLookup } from "./public-address.js";

function positive(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

const MAX_OUTBOUND = positive(process.env.MEELU_CRAWL_MAX_OUTBOUND, 12);
const PER_ORIGIN = positive(process.env.MEELU_CRAWL_PER_ORIGIN, 6);

const connectAnyPublic = buildConnector({ timeout: 10_000, lookup: publicLookup });

function connectPublic(opts, callback) {
  if (isPrivateAddress(opts.hostname)) {
    callback(privateHostError(opts.hostname));
    return;
  }
  connectAnyPublic(opts, callback);
}

const crawlDispatcher = new Agent({
  connections: PER_ORIGIN,
  keepAliveTimeout: 10_000,
  keepAliveMaxTimeout: 60_000,
  connect: connectPublic,
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
