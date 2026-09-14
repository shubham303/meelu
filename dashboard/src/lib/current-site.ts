"use client";

const COOKIE = "meelu_site";
const MAX_AGE = 60 * 60 * 24 * 365;

export const GLOBAL = "__global__";

let current: string | null = null;
let hydrated = false;
const listeners = new Set<() => void>();

function readCookie(): string | null {
  if (typeof document === "undefined") return null;
  const hit = document.cookie
    .split("; ")
    .find((part) => part.startsWith(`${COOKIE}=`));
  return hit ? decodeURIComponent(hit.slice(COOKIE.length + 1)) : null;
}

export function currentSiteId(): string | null {
  if (!hydrated) {
    current = readCookie();
    hydrated = true;
  }
  return current;
}

export function setCurrentSite(siteId: string | null): void {
  if (currentSiteId() === siteId) return;
  current = siteId;
  if (typeof document !== "undefined") {
    document.cookie = siteId
      ? `${COOKIE}=${encodeURIComponent(siteId)}; path=/; max-age=${MAX_AGE}; samesite=lax`
      : `${COOKIE}=; path=/; max-age=0; samesite=lax`;
  }
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
