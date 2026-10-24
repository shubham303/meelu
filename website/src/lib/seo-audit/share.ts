import { randomBytes } from "node:crypto";
import { getJson, putJson, storageConfigured } from "@/lib/storage/r2";
import type { SlimResult } from "./audit";

const SHARE_ID = /^[A-Za-z0-9_-]{16}$/;

export type SharedAudit = {
  savedAt: string;
  result: SlimResult;
};

function keyFor(id: string): string {
  return `audits/${id}.json`;
}

export function shareUrlPath(id: string): string {
  return `/tools/seo-audit/r/${id}`;
}

export async function saveSharedAudit(result: SlimResult): Promise<string | null> {
  if (!storageConfigured()) return null;
  const id = randomBytes(12).toString("base64url");
  const shared: SharedAudit = { savedAt: new Date().toISOString(), result };
  await putJson(keyFor(id), shared);
  return id;
}

export async function loadSharedAudit(id: string): Promise<SharedAudit | null> {
  if (!SHARE_ID.test(id) || !storageConfigured()) return null;
  const shared = (await getJson(keyFor(id))) as SharedAudit | null;
  return shared?.result ? shared : null;
}
