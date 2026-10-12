import { randomUUID } from "node:crypto";
import { listKeys, putJson, storageConfigured } from "@/lib/storage/r2";
import { CLUSTER_LIMITS } from "./limits";

const PREFIX = "keyword-clusters/runs/";

export function dailyLimit(): number {
  const raw = Number(process.env.KEYWORD_CLUSTER_DAILY_LIMIT);
  return Number.isFinite(raw) && raw >= 0 ? Math.floor(raw) : CLUSTER_LIMITS.dailyRuns;
}

export function secondsUntilUtcMidnight(now = new Date()): number {
  const next = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1);
  return Math.max(1, Math.ceil((next - now.getTime()) / 1000));
}

async function runsOn(day: string): Promise<number> {
  return (await listKeys(`${PREFIX}${day}/`)).length;
}

export type DailyClaim =
  | { ok: true; used: number; limit: number }
  | { ok: false; reason: "exhausted"; used: number; limit: number; retryAfterSeconds: number }
  | { ok: false; reason: "unavailable"; detail: string };

export async function claimDailyRun(): Promise<DailyClaim> {
  const limit = dailyLimit();
  if (!storageConfigured()) {
    if (process.env.NODE_ENV === "production") {
      return { ok: false, reason: "unavailable", detail: "R2 storage is not configured" };
    }
    return { ok: true, used: 0, limit };
  }

  const now = new Date();
  const day = now.toISOString().slice(0, 10);
  try {
    const used = await runsOn(day);
    if (used >= limit) {
      return {
        ok: false,
        reason: "exhausted",
        used,
        limit,
        retryAfterSeconds: secondsUntilUtcMidnight(now),
      };
    }
    await putJson(`${PREFIX}${day}/${now.getTime()}-${randomUUID()}.json`, {
      at: now.toISOString(),
    });
    return { ok: true, used: used + 1, limit };
  } catch (error) {
    return {
      ok: false,
      reason: "unavailable",
      detail: error instanceof Error ? error.message : String(error),
    };
  }
}
