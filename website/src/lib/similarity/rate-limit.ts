/**
 * The comparison runs in the browser, so the only thing worth metering is the
 * optional URL fetch. That is one or two requests rather than a hundred-page
 * crawl, so this keeps the shape of the audit tool's limiter with a budget that
 * suits the job instead of borrowing one meant for crawling. In memory: it
 * resets on restart and does not cross instances, so it is a brake, not a lock.
 */

export const FETCH_LIMITS = {
  perHour: 40,
  perDay: 200,
  concurrent: 6,
};

const HOUR = 60 * 60 * 1000;
const DAY = 24 * HOUR;

const hits = new Map<string, number[]>();
let running = 0;
let lastSweep = 0;

function sweep(now: number) {
  if (now - lastSweep < 5 * 60 * 1000) return;
  lastSweep = now;
  for (const [key, times] of hits) {
    const kept = times.filter((t) => now - t < DAY);
    if (kept.length === 0) hits.delete(key);
    else hits.set(key, kept);
  }
}

export type Verdict =
  | { ok: true; release: () => void }
  | { ok: false; reason: "hourly" | "daily" | "busy"; retryAfterSeconds: number };

export function takeFetchSlot(key: string): Verdict {
  const now = Date.now();
  sweep(now);

  const mine = (hits.get(key) ?? []).filter((t) => now - t < DAY);
  const lastHour = mine.filter((t) => now - t < HOUR);

  if (lastHour.length >= FETCH_LIMITS.perHour) {
    return {
      ok: false,
      reason: "hourly",
      retryAfterSeconds: Math.ceil((HOUR - (now - lastHour[0])) / 1000),
    };
  }
  if (mine.length >= FETCH_LIMITS.perDay) {
    return {
      ok: false,
      reason: "daily",
      retryAfterSeconds: Math.ceil((DAY - (now - mine[0])) / 1000),
    };
  }
  if (running >= FETCH_LIMITS.concurrent) {
    return { ok: false, reason: "busy", retryAfterSeconds: 20 };
  }

  mine.push(now);
  hits.set(key, mine);
  running += 1;
  let released = false;

  return {
    ok: true,
    release: () => {
      if (released) return;
      released = true;
      running = Math.max(0, running - 1);
    },
  };
}
