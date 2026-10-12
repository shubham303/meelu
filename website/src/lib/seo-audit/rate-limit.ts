/**
 * A free tool that fetches a hundred pages on demand is a free proxy and a free
 * denial-of-service amplifier unless somebody counts. This counter lives in
 * memory: it resets when the server restarts and does not cross instances, so
 * treat it as a brake rather than a lock.
 */

export const LIMITS = {
  perHour: 5,
  perDay: 20,
  concurrent: 3,
  globalPerHour: 120,
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
  | { ok: true; release: () => void; remainingToday: number }
  | { ok: false; reason: "hourly" | "daily" | "busy" | "global"; retryAfterSeconds: number };

export function takeSlot(key: string): Verdict {
  const now = Date.now();
  sweep(now);

  const mine = (hits.get(key) ?? []).filter((t) => now - t < DAY);
  const lastHour = mine.filter((t) => now - t < HOUR);

  if (lastHour.length >= LIMITS.perHour) {
    return {
      ok: false,
      reason: "hourly",
      retryAfterSeconds: Math.ceil((HOUR - (now - lastHour[0])) / 1000),
    };
  }
  if (mine.length >= LIMITS.perDay) {
    return {
      ok: false,
      reason: "daily",
      retryAfterSeconds: Math.ceil((DAY - (now - mine[0])) / 1000),
    };
  }

  const globalLastHour = [...hits.values()]
    .flat()
    .filter((t) => now - t < HOUR).length;
  if (globalLastHour >= LIMITS.globalPerHour) {
    return { ok: false, reason: "global", retryAfterSeconds: 600 };
  }

  if (running >= LIMITS.concurrent) {
    return { ok: false, reason: "busy", retryAfterSeconds: 30 };
  }

  mine.push(now);
  hits.set(key, mine);
  running += 1;
  let released = false;

  return {
    ok: true,
    remainingToday: Math.max(0, LIMITS.perDay - mine.length),
    release: () => {
      if (released) return;
      released = true;
      running = Math.max(0, running - 1);
    },
  };
}

/** Best available caller identity behind the usual proxies. */
export function clientKey(headers: Headers): string {
  const forwarded = headers.get("x-forwarded-for");
  const candidate =
    headers.get("cf-connecting-ip") ??
    headers.get("x-real-ip") ??
    forwarded?.split(",")[0].trim() ??
    "";
  return candidate || "unknown";
}
