import { createHash } from "node:crypto";
import { putJson, storageConfigured } from "@/lib/storage/r2";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function normalizeEmail(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const email = raw.trim().toLowerCase();
  if (email.length > 254 || !EMAIL_PATTERN.test(email)) return null;
  return email;
}

function downloadKey(email: string): string {
  return `downloads/${createHash("sha256").update(email).digest("hex").slice(0, 32)}.json`;
}

export type RecordResult = { ok: true } | { ok: false; detail: string };

export async function recordDownload(
  email: string,
  country: string,
  build: string,
): Promise<RecordResult> {
  if (!storageConfigured()) return { ok: false, detail: "R2 storage is not configured" };
  try {
    await putJson(downloadKey(email), { email, country, build, at: new Date().toISOString() });
    return { ok: true };
  } catch (error) {
    return { ok: false, detail: error instanceof Error ? error.message : String(error) };
  }
}
