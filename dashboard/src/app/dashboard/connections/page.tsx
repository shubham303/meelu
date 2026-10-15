"use client";

import { useEffect, useState } from "react";
import { Cable, ExternalLink, Plug, Trash2 } from "lucide-react";
import { PageEnter, Stagger } from "@/components/animate";
import { Badge, Button, Card, ConfirmDelete, PageHeader, Spinner } from "@/components/ui";
import { CATEGORY_LABEL, isInstallable, MCP_CATALOG, type CatalogEntry } from "@/lib/mcp-catalog";
import { formatRelative } from "@/lib/utils";
import { ModelPricingCard } from "@/features/llm-models/model-pricing-card";
import { OwnKeyCard } from "@/features/llm-models/own-key-card";
import type { ConnectorsView } from "../agent-tasks";

export default function ConnectionsPage() {
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  const canConnect = !!bridge?.getConnectors;

  const [connectors, setConnectors] = useState<ConnectorsView | null>(null);
  const [loading, setLoading] = useState(canConnect);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!bridge?.getConnectors) return;
    void bridge.getConnectors().then((res) => {
      setLoading(false);
      if ("error" in res) setError(res.error as string);
      else setConnectors(res);
    });
  }, [bridge]);

  const [disconnect, setDisconnect] = useState<CatalogEntry | null>(null);

  const [oauthBusy, setOauthBusy] = useState<string | null>(null);

  const runOauthConnect = async (e: CatalogEntry) => {
    const connect = e.connect === "ga4" ? bridge?.connectGa4 : bridge?.connectGsc;
    if (!connect) return;
    setOauthBusy(e.id);
    setError(null);
    const res = await connect();
    setOauthBusy(null);
    if ("error" in res) {
      setError(res.error as string);
      return;
    }
    setConnectors(res);
  };

  return (
    <PageEnter>
      <PageHeader
        title="Connections"
        description="The hands. Meelu is the memory; each platform you connect here is something the agent can act through — publishing, code, data. Keys are encrypted into this device's keychain and never touch Meelu's servers."
      />

      <OwnKeyCard />
      <ModelPricingCard />

      {!canConnect && (
        <p className="text-sm text-sub mb-4">
          Connecting happens in the Meelu app, where keys stay encrypted on your own device.
          On the web, each platform&apos;s docs page shows how to run its server in your own
          agent instead.
        </p>
      )}

      {error && <p className="text-sm text-bad mb-4">{error}</p>}

      {loading ? (
        <Spinner />
      ) : (
        <Stagger className="grid gap-4 sm:grid-cols-2">
          {MCP_CATALOG.map((e) => {
            const connected = connectors?.[e.id];
            const isOauth = !!e.connect;
            const waiting = oauthBusy === e.id;
            const planned = !isInstallable(e);
            return (
              <Card key={e.id} className="stagger-item">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-ink truncate">{e.name}</p>
                      {e.publisher === "community" && <Badge tone="warn">community</Badge>}
                    </div>
                    <p className="text-xs text-faint mt-0.5">{CATEGORY_LABEL[e.category]}</p>
                  </div>
                  {planned ? (
                    <Badge tone="warn">Planned</Badge>
                  ) : (
                    canConnect &&
                    (connected ? (
                      <Badge tone="good">Connected</Badge>
                    ) : (
                      <Badge tone="neutral">Not connected</Badge>
                    ))
                  )}
                </div>
                <p className="text-sm text-sub mt-2">{e.blurb}</p>

                {connected && (
                  <div className="mt-3 space-y-1">
                    {!isOauth &&
                      Object.entries(connected.fields).map(([k, v]) => (
                        <p key={k} className="text-xs text-faint font-mono">
                          {k}: {v}
                        </p>
                      ))}
                    {connected.updatedAt && (
                      <p className="text-xs text-faint">
                        Connected {formatRelative(connected.updatedAt)}
                      </p>
                    )}
                  </div>
                )}

                {planned && e.caveat && (
                  <p className="text-xs text-sub mt-3 leading-relaxed">{e.caveat}</p>
                )}

                <div className="flex items-center gap-2 mt-4">
                  {!planned &&
                    canConnect &&
                    (connected ? (
                      <>
                        {isOauth && (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={waiting}
                            onClick={() => void runOauthConnect(e)}
                          >
                            <Plug size={13} /> {waiting ? "Waiting for Google…" : "Reconnect"}
                          </Button>
                        )}
                        <Button size="sm" variant="ghost" onClick={() => setDisconnect(e)}>
                          <Trash2 size={13} /> Disconnect
                        </Button>
                      </>
                    ) : (
                      <Button size="sm" disabled={!isOauth || waiting} onClick={() => void runOauthConnect(e)}>
                        <Cable size={13} />{" "}
                        {waiting ? "Waiting for Google…" : "Connect"}
                      </Button>
                    ))}
                  <a
                    href={e.docsUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="ml-auto inline-flex items-center gap-1 text-xs text-sub hover:text-ink transition-colors"
                  >
                    Docs <ExternalLink size={11} />
                  </a>
                </div>
              </Card>
            );
          })}
        </Stagger>
      )}

      <ConfirmDelete
        open={disconnect !== null}
        onClose={() => setDisconnect(null)}
        what={disconnect ? `the ${disconnect.name} connection` : "connection"}
        onConfirm={async () => {
          if (!disconnect || !bridge?.removeConnector) return;
          const res = await bridge.removeConnector(disconnect.id);
          if (!("error" in res)) setConnectors(res);
        }}
      />
    </PageEnter>
  );
}
