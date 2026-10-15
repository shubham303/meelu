"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { currentSiteId, subscribeToSite } from "./current-site";
import { mockFetch } from "@demo/mock/api";
import {
  billingResolvedCount,
  readBillingBlock,
  setBillingBlock,
  subscribeToBillingBlock,
} from "./billing-block";

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export type Paged<T, Extra = object> = Extra & {
  data: T[];
  pagination: Pagination;
  note?: string | null;
};

async function request(
  path: string,
  opts: { method?: string; body?: unknown } = {},
): Promise<Record<string, unknown>> {
  const res = await mockFetch(opts.method ?? "GET", path, opts.body);
  const payload = (res.payload ?? {}) as Record<string, unknown>;
  if (res.status >= 400) {
    const err = payload.error as { message?: string; code?: string } | undefined;
    const blocked = res.status === 402 ? readBillingBlock(err) : null;
    if (blocked) setBillingBlock(blocked);
    throw new Error(err?.message ?? `Request failed (${res.status})`);
  }
  return payload;
}

export async function api<T = unknown>(
  path: string,
  opts: { method?: string; body?: unknown } = {},
): Promise<T> {
  const payload = await request(path, opts);
  return payload.data as T;
}

export async function apiPaged<T = unknown, Extra = object>(
  path: string,
): Promise<Paged<T, Extra>> {
  return (await request(path)) as unknown as Paged<T, Extra>;
}

export function useCurrentSite(): string | null {
  return useSyncExternalStore(
    subscribeToSite,
    currentSiteId,
    () => null,
  );
}

function useFetched<T>(path: string | null, fetcher: (path: string) => Promise<T>) {
  const siteId = useCurrentSite();
  const billingResolved = useSyncExternalStore(
    subscribeToBillingBlock,
    billingResolvedCount,
    () => 0,
  );
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!path) return;
    try {
      const d = await fetcher(path);
      setData(d);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, siteId, billingResolved]);

  useEffect(() => {
    setData(null);
    setError(null);
    setLoading(true);
    void refresh();
  }, [refresh]);

  return { data, loading, error, refresh };
}

export function useApi<T = unknown>(path: string | null) {
  return useFetched<T>(path, (p) => api<T>(p));
}

export function usePagedApi<T = unknown, Extra = object>(path: string | null) {
  return useFetched<Paged<T, Extra>>(path, (p) => apiPaged<T, Extra>(p));
}
