const HOUR = 60 * 60 * 1000;
const PER_HOUR = 6;

const hits = new Map<string, number[]>();
const running = new Set<string>();

export type ClusterSlot =
  | { ok: true; release: () => void }
  | { ok: false; reason: "hourly" | "busy"; retryAfterSeconds: number };

export function takeClusterSlot(key: string): ClusterSlot {
  const now = Date.now();
  for (const [k, times] of hits) {
    const kept = times.filter((t) => now - t < HOUR);
    if (kept.length === 0) hits.delete(k);
    else hits.set(k, kept);
  }
  if (running.has(key)) return { ok: false, reason: "busy", retryAfterSeconds: 30 };
  const mine = hits.get(key) ?? [];
  if (mine.length >= PER_HOUR) {
    return { ok: false, reason: "hourly", retryAfterSeconds: Math.ceil((HOUR - (now - mine[0])) / 1000) };
  }
  mine.push(now);
  hits.set(key, mine);
  running.add(key);
  let released = false;
  return {
    ok: true,
    release: () => {
      if (released) return;
      released = true;
      running.delete(key);
    },
  };
}
