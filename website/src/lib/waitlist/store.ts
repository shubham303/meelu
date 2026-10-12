import { createHash } from "node:crypto";
import { putJson, storageConfigured } from "@/lib/storage/r2";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function normalizeEmail(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const email = raw.trim().toLowerCase();
  if (email.length > 254 || !EMAIL_PATTERN.test(email)) return null;
  return email;
}

export function waitlistKey(email: string): string {
  return `waitlist/${createHash("sha256").update(email).digest("hex").slice(0, 32)}.json`;
}

export type JoinResult = { ok: true } | { ok: false; detail: string };

export async function joinWaitlist(email: string, platform: string | null): Promise<JoinResult> {
  if (!storageConfigured()) return { ok: false, detail: "R2 storage is not configured" };
  try {
    await putJson(waitlistKey(email), {
      email,
      at: new Date().toISOString(),
      source: "download-cap",
      platform,
    });
    return { ok: true };
  } catch (error) {
    return { ok: false, detail: error instanceof Error ? error.message : String(error) };
  }
}
