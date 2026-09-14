"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Cable, ExternalLink, Plug, Search, Share2, Trash2 } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  ConfirmDelete,
  Field,
  Input,
  Modal,
  Select,
} from "@/components/ui";
import type { ProviderCatalogEntry, ProviderDomain } from "@/components/agent/bridge";
import { useIsApp } from "@/lib/use-app-mode";
import { useCurrentSite } from "@/lib/use-api";
import { GLOBAL } from "@/lib/current-site";
import {
  APP_ONLY_NOTE,
  providerCall,
  useProvidersStatus,
  type SocialProfilesResult,
} from "@/lib/providers";

const PLATFORM_LABEL: Record<string, string> = {
  facebook: "Facebook",
  instagram: "Instagram",
  tiktok: "TikTok",
  linkedin: "LinkedIn",
  youtube: "YouTube",
  twitter: "X (Twitter)",
  threads: "Threads",
  pinterest: "Pinterest",
  bluesky: "Bluesky",
  telegram: "Telegram",
  google_business: "Google Business",
};

function platformLabel(id: string): string {
  return PLATFORM_LABEL[id] ?? id;
}

function useProviderCatalog(domain: ProviderDomain): ProviderCatalogEntry[] {
  const [catalog, setCatalog] = useState<ProviderCatalogEntry[]>([]);
  useEffect(() => {
    const b = typeof window !== "undefined" ? window.meeluAgent : undefined;
    void b?.providersCatalog?.().then((res) => {
      setCatalog(res.catalog.filter((e) => e.domain === domain));
    });
  }, [domain]);
  return catalog;
}

function ProviderDomainCard({
  domain,
  title,
  icon,
  blurb,
  children,
}: {
  domain: ProviderDomain;
  title: string;
  icon: ReactNode;
  blurb: string;
  children?: (connected: boolean) => ReactNode;
}) {
  const isApp = useIsApp();
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  const catalog = useProviderCatalog(domain);
  const { status, error, refresh, setDefault } = useProvidersStatus();
  const facade = status?.[domain] ?? null;

  const [entry, setEntry] = useState<ProviderCatalogEntry | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [disconnect, setDisconnect] = useState<ProviderCatalogEntry | null>(null);

  if (!isApp || !bridge?.providersStatus) {
    return (
      <Card className="mb-6">
        <div className="flex items-center gap-2.5">
          {icon}
          <p className="font-medium text-ink">{title}</p>
        </div>
        <p className="text-sm text-sub mt-1">
          {domain === "social" ? APP_ONLY_NOTE : "Search-data providers connect in the Meelu app."}
        </p>
      </Card>
    );
  }

  const connected = facade?.connected ?? [];

  const save = async () => {
    if (!entry || !bridge.setConnector) return;
    for (const f of entry.fields) {
      if ((values[f.key] ?? "").trim() === "") {
        setErr(`Missing required field: ${f.label}`);
        return;
      }
    }
    setBusy(true);
    setErr(null);
    const res = await bridge.setConnector(
      entry.id,
      values,
      entry.fields.filter((f) => f.secret).map((f) => f.key),
    );
    setBusy(false);
    if ("error" in res) {
      setErr(res.error as string);
      return;
    }
    setEntry(null);
    await refresh();
  };

  return (
    <Card className="mb-6">
      <div className="flex items-center gap-2.5">
        {icon}
        <p className="font-medium text-ink">{title}</p>
        {connected.length > 0 && <Badge tone="good">{connected.length} connected</Badge>}
      </div>
      <p className="text-sm text-sub mt-1">{blurb}</p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {catalog.map((e) => {
          const isConnected = connected.includes(e.id);
          const isDefault = facade?.default === e.id;
          return (
            <div key={e.id} className="rounded-lg border border-line px-3 py-2.5">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-ink truncate">{e.name}</p>
                {isConnected ? (
                  <Badge tone="good">Connected</Badge>
                ) : (
                  <Badge tone="neutral">Not connected</Badge>
                )}
                {isDefault && connected.length > 1 && <Badge tone="accent">default</Badge>}
              </div>
              <div className="mt-2 flex items-center gap-2">
                {isConnected ? (
                  <>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setEntry(e);
                        setValues({});
                        setErr(null);
                      }}
                    >
                      <Plug size={13} /> Update key
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setDisconnect(e)}>
                      <Trash2 size={13} /> Disconnect
                    </Button>
                  </>
                ) : (
                  <Button
                    size="sm"
                    onClick={() => {
                      setEntry(e);
                      setValues({});
                      setErr(null);
                    }}
                  >
                    <Cable size={13} /> Connect
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {connected.length > 1 && (
        <div className="mt-4 max-w-xs">
          <Field label="Default provider" hint="Used when a task does not name one.">
            <Select
              value={facade?.default ?? ""}
              onChange={(e) => void setDefault(domain, e.target.value || null)}
              aria-label={`Default ${title} provider`}
            >
              <option value="">Choose…</option>
              {connected.map((id) => (
                <option key={id} value={id}>
                  {catalog.find((c) => c.id === id)?.name ?? id}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      )}

      {(error || err) && !entry && <p className="text-sm text-bad mt-2">{error ?? err}</p>}

      {children?.(connected.length > 0)}

      <Modal
        open={entry !== null}
        onClose={() => setEntry(null)}
        title={entry ? `Connect ${entry.name}` : "Connect"}
      >
        {entry && (
          <div className="space-y-4">
            {entry.fields.map((f) => (
              <Field key={f.key} label={f.label} hint={f.help}>
                <div className="space-y-1.5">
                  <Input
                    type={f.secret ? "password" : "text"}
                    value={values[f.key] ?? ""}
                    onChange={(ev) => setValues((v) => ({ ...v, [f.key]: ev.target.value }))}
                  />
                  {f.url && (
                    <a
                      href={f.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-accent hover:underline"
                    >
                      Get your key <ExternalLink size={11} />
                    </a>
                  )}
                </div>
              </Field>
            ))}
            {err && <p className="text-sm text-bad">{err}</p>}
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setEntry(null)}>
                Cancel
              </Button>
              <Button disabled={busy} onClick={() => void save()}>
                Connect
              </Button>
            </div>
          </div>
        )}
      </Modal>

      <ConfirmDelete
        open={disconnect !== null}
        onClose={() => setDisconnect(null)}
        what={disconnect ? `the ${disconnect.name} connection` : "connection"}
        onConfirm={async () => {
          if (!disconnect || !bridge.removeConnector) return;
          const res = await bridge.removeConnector(disconnect.id);
          if ("error" in res) setErr(res.error as string);
          await refresh();
        }}
      />
    </Card>
  );
}

function SocialProfilesSection() {
  const selected = useCurrentSite();
  const site = selected && selected !== GLOBAL ? selected : null;
  const [data, setData] = useState<SocialProfilesResult | null>(null);
  const [platform, setPlatform] = useState("instagram");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState<{ id: string; label: string } | null>(null);

  const load = useCallback(async () => {
    if (!site) return;
    try {
      setData(await providerCall<SocialProfilesResult>("social_profiles", { siteId: site }));
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not read connected profiles.");
    }
  }, [site]);

  useEffect(() => {
    if (!site) return;
    const pull = () =>
      providerCall<SocialProfilesResult>("social_profiles", { siteId: site })
        .then((res) => {
          setData(res);
          setErr(null);
        })
        .catch((e: unknown) => {
          setErr(e instanceof Error ? e.message : "Could not read connected profiles.");
        });
    void pull();
    const onFocus = () => void pull();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [site]);

  if (!site) {
    return (
      <p className="text-sm text-sub mt-4">Pick a website above to connect its social accounts.</p>
    );
  }

  const platforms = data?.platforms.length ? data.platforms : Object.keys(PLATFORM_LABEL);
  const profiles = data?.profiles ?? [];

  const connect = async () => {
    setBusy(true);
    setErr(null);
    try {
      const link = await providerCall<{ url: string; expiresAt?: string }>("social_connect_link", {
        siteId: site,
        platform,
      });
      window.open(link.url, "_blank", "noopener");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not start the connection.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-5 border-t border-line pt-4">
      <p className="text-xs uppercase tracking-wide text-sub">Connected accounts</p>
      <p className="text-xs text-faint mt-0.5">
        You authorize each network on its own consent screen; the grant lives with the publishing
        provider, and no password or token lands here.
      </p>

      {profiles.length > 0 && (
        <div className="mt-3 space-y-1">
          {profiles.map((p) => (
            <div key={p.id} className="flex items-center gap-2 text-sm">
              <span className="text-ink">{platformLabel(p.platform)}</span>
              <span className="text-faint">{p.name}</span>
              {p.status === "active" ? (
                <Badge tone="good">active</Badge>
              ) : (
                <Badge tone="warn">{p.status} — reconnect below</Badge>
              )}
              <button
                onClick={() =>
                  setDisconnecting({
                    id: p.id,
                    label: `${platformLabel(p.platform)}${p.name ? ` (${p.name})` : ""}`,
                  })
                }
                className="ml-auto text-xs text-faint hover:text-bad transition-colors cursor-pointer"
              >
                Disconnect
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 flex items-center gap-2">
        <Select
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
          aria-label="Platform to connect"
        >
          {platforms.map((id) => (
            <option key={id} value={id}>
              {platformLabel(id)}
            </option>
          ))}
        </Select>
        <Button onClick={() => void connect()} disabled={busy}>
          <Cable size={14} /> Connect
        </Button>
      </div>
      {err && <p className="text-sm text-bad mt-2">{err}</p>}

      <ConfirmDelete
        open={Boolean(disconnecting)}
        onClose={() => setDisconnecting(null)}
        what={disconnecting?.label ?? "this account"}
        onConfirm={async () => {
          if (!disconnecting) return;
          setErr(null);
          try {
            await providerCall("social_disconnect_profile", {
              siteId: site,
              profileId: disconnecting.id,
            });
            await load();
          } catch (e) {
            setErr(e instanceof Error ? e.message : "Could not disconnect that account.");
          } finally {
            setDisconnecting(null);
          }
        }}
      />
    </div>
  );
}

export function SocialPublishingCard() {
  return (
    <ProviderDomainCard
      domain="social"
      title="Social publishing"
      icon={<Share2 size={15} className="text-accent shrink-0" />}
      blurb="Where scheduled pieces go out. Connect a publishing provider with your own key, then authorize each network."
    >
      {(connected) => (connected ? <SocialProfilesSection /> : null)}
    </ProviderDomainCard>
  );
}

export function SearchDataCard() {
  return (
    <ProviderDomainCard
      domain="seo-data"
      title="Search data"
      icon={<Search size={15} className="text-accent shrink-0" />}
      blurb="Rank checks, keyword ideas, SERP snapshots, vitals and AI-visibility pulls run through this provider with your own key, against the monthly search-data budget."
    />
  );
}
