"use client";

import { SITE_ID } from "@demo/mock/data/site";

export const GLOBAL = "__global__";

let current: string | null = SITE_ID;
const listeners = new Set<() => void>();

export function currentSiteId(): string | null {
  return current;
}

export function setCurrentSite(siteId: string | null): void {
  if (current === siteId) return;
  current = siteId ?? SITE_ID;
  for (const listener of listeners) listener();
}

export function subscribeToSite(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function activeSiteId(): string | null {
  const id = currentSiteId();
  return id && id !== GLOBAL ? id : null;
}

export function siteHeader(): Record<string, string> {
  const id = currentSiteId();
  return id && id !== GLOBAL ? { "x-meelu-site": id } : {};
}
