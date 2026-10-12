export function seeded(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function hashString(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export const NOW = Date.now();
export const HOUR = 3_600_000;
export const DAY = 24 * HOUR;

export function ago(ms: number): string {
  return new Date(NOW - ms).toISOString();
}

export function dayKey(daysAgo: number): string {
  return new Date(NOW - daysAgo * DAY).toISOString().slice(0, 10);
}

export function pick<T>(rng: () => number, list: readonly T[]): T {
  return list[Math.floor(rng() * list.length)];
}

export function between(rng: () => number, lo: number, hi: number): number {
  return lo + rng() * (hi - lo);
}

export function int(rng: () => number, lo: number, hi: number): number {
  return Math.floor(between(rng, lo, hi + 1));
}
