"use client";

export type BillingBlockCode = "site_disabled" | "insufficient_credits";

export interface BillingBlock {
  code: BillingBlockCode;
  message: string;
  siteId?: string;
  balanceUsd?: number;
  minimumUsd?: number;
}

let current: BillingBlock | null = null;
let resolvedCount = 0;
const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

export function billingBlock(): BillingBlock | null {
  return current;
}

export function setBillingBlock(block: BillingBlock): void {
  if (current?.code === block.code && current.message === block.message) return;
  current = block;
  emit();
}

export function clearBillingBlock(code?: BillingBlockCode): void {
  if (current === null) return;
  if (code && current.code !== code) return;
  current = null;
  emit();
}

export function resolveBillingBlock(): void {
  current = null;
  resolvedCount += 1;
  emit();
}

export function billingResolvedCount(): number {
  return resolvedCount;
}

export function subscribeToBillingBlock(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function micros(value: unknown): number | undefined {
  return typeof value === "number" ? value / 1_000_000 : undefined;
}

export function readBillingBlock(error: unknown): BillingBlock | null {
  if (typeof error !== "object" || error === null) return null;
  const { code, message, siteId, balanceMicros, minimumMicros } = error as Record<string, unknown>;
  if (code !== "site_disabled" && code !== "insufficient_credits") return null;
  return {
    code,
    message: typeof message === "string" ? message : "This workspace is out of credits.",
    siteId: typeof siteId === "string" ? siteId : undefined,
    balanceUsd: micros(balanceMicros),
    minimumUsd: micros(minimumMicros),
  };
}
