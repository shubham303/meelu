"use client";

import { useCallback, useEffect, useState } from "react";
import {
  bridge,
  type ProviderDomain,
  type ProvidersStatus,
} from "@/components/agent/bridge";
import { activeSiteId } from "./current-site";
import { useIsApp } from "./use-app-mode";

export const APP_ONLY_NOTE = "Publishing happens in the Meelu app.";
export const SEO_APP_ONLY_NOTE = "Search-data pulls happen in the Meelu app.";

export const CONNECT_NOTE: Record<ProviderDomain, string> = {
  "seo-data": "Connect a search-data provider on the Connections screen.",
  social: "Connect a social publishing provider on the Connections screen.",
};

export class ProviderCallError extends Error {
  code: string;
  extra: Record<string, unknown>;

  constructor(code: string, message: string, extra: Record<string, unknown> = {}) {
    super(message);
    this.name = "ProviderCallError";
    this.code = code;
    this.extra = extra;
  }
}

export interface SocialProfile {
  id: string;
  name: string;
  status: string;
  platform: string;
  avatarUrl: string | null;
}

export interface SocialProfilesResult {
  provider: string;
  accountConnected: boolean;
  profiles: SocialProfile[];
  platforms: string[];
}

export function providerBridgeReady(): boolean {
  return !!bridge()?.providerCall;
}

export async function providerCall<T = unknown>(
  tool: string,
  input: Record<string, unknown> = {},
): Promise<T> {
  const b = bridge();
  if (!b?.providerCall) {
    throw new ProviderCallError("no_bridge", "This action runs in the Meelu app.");
  }
  const payload = "siteId" in input ? input : { siteId: activeSiteId(), ...input };
  const res = await b.providerCall(tool, payload);
  if (!res.ok) {
    const { code, message, ...extra } = res.error;
    throw new ProviderCallError(code, message, extra);
  }
  return res.result as T;
}

export function useProvidersStatus() {
  const isApp = useIsApp();
  const [status, setStatus] = useState<ProvidersStatus | null>(null);
  const [loading, setLoading] = useState(isApp);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const b = bridge();
    if (!isApp || !b?.providersStatus) return;
    try {
      setStatus(await b.providersStatus());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read provider status.");
    } finally {
      setLoading(false);
    }
  }, [isApp]);

  useEffect(() => {
    const b = bridge();
    if (!isApp || !b?.providersStatus) return;
    b.providersStatus()
      .then((s) => {
        setStatus(s);
        setError(null);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Could not read provider status.");
      })
      .finally(() => setLoading(false));
  }, [isApp]);

  const setDefault = useCallback(
    async (domain: ProviderDomain, providerId: string | null) => {
      const b = bridge();
      if (!b?.setProviderDefault) return;
      try {
        setStatus(await b.setProviderDefault(domain, providerId));
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not set the default provider.");
      }
    },
    [],
  );

  return { status, loading, error, refresh, setDefault };
}

export function useProviderConnected(domain: ProviderDomain): boolean {
  const { status } = useProvidersStatus();
  return (status?.[domain]?.connected.length ?? 0) > 0;
}

export function useProviderGate(domain: ProviderDomain): { ready: boolean; note: string | null } {
  const isApp = useIsApp();
  const connected = useProviderConnected(domain);
  if (!isApp) return { ready: false, note: domain === "social" ? APP_ONLY_NOTE : SEO_APP_ONLY_NOTE };
  if (!connected) return { ready: false, note: CONNECT_NOTE[domain] };
  return { ready: true, note: null };
}
