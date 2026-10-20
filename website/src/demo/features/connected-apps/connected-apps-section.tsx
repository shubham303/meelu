"use client";

import { useEffect, useState } from "react";
import { Cable, RefreshCw, Trash2 } from "lucide-react";
import { Stagger } from "@demo/components/animate";
import { Badge, Button, Card, ConfirmDelete, Spinner } from "@demo/components/ui";
import { api, useApi, useCurrentSite } from "@demo/lib/use-api";

interface Connection {
  connectionId: string;
  status: string;
  label?: string | null;
}

interface AppConnections {
  desk: string;
  app: string;
  name: string;
  connections: Connection[];
}

interface ConnectLink {
  url: string;
}

const DESK_LABEL: Record<string, string> = {
  email: "Email",
  cms: "CMS",
  crm: "CRM",
  docs: "Docs",
  social: "Social",
};

const DESK_BLURB: Record<string, string> = {
  email: "Meelu searches your mail and saves draft emails and newsletters. You send every one yourself.",
  cms: "Meelu reads your collections and saves pages as drafts. You publish them.",
  crm: "Meelu looks up contacts and deals and adds the contacts and notes you approve.",
  docs: "Meelu reads your pages and adds new pages, rows and comments. It never edits what you wrote.",
  social: "Meelu posts a reply you approved to a thread you picked, from your own account. It never starts a post.",
};

function statusBadge(status: string) {
  if (status === "ACTIVE") return <Badge tone="good">Connected</Badge>;
  if (status === "INITIATED" || status === "INITIALIZING") return <Badge tone="warn">Waiting for sign-in</Badge>;
  return <Badge tone="bad">{status.toLowerCase()}</Badge>;
}

export function ConnectedAppsSection() {
  const site = useCurrentSite();
  const { data, loading, error, refresh } = useApi<AppConnections[]>(
    site ? "/api/v1/connected-apps" : null,
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [disconnect, setDisconnect] = useState<{ app: AppConnections; connection: Connection } | null>(
    null,
  );

  useEffect(() => {
    const onFocus = () => void refresh();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [refresh]);

  if (!site) return null;

  const connect = async (app: AppConnections) => {
    setBusy(app.app);
    setActionError(null);
    try {
      const link = await api<ConnectLink>("/api/v1/connected-apps", {
        method: "POST",
        body: { desk: app.desk, app: app.app },
      });
      window.open(link.url, "_blank", "noopener");
      await refresh();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Could not start the sign-in");
    } finally {
      setBusy(null);
    }
  };

  const desks = [...new Set((data ?? []).map((a) => a.desk))];

  return (
    <section className="mt-8">
      <div className="flex items-center justify-between gap-3 mb-1">
        <h2 className="text-base font-medium text-ink">Your accounts</h2>
        <Button size="sm" variant="ghost" onClick={() => void refresh()}>
          <RefreshCw size={13} /> Check again
        </Button>
      </div>
      <p className="text-sm text-sub mb-4">
        Connect this website&apos;s own email, CMS, CRM, docs and social accounts. Sign-in runs through Composio,
        which keeps the account&apos;s login; Meelu asks before every write.
      </p>

      {(error || actionError) && <p className="text-sm text-bad mb-4">{actionError ?? error}</p>}

      {loading ? (
        <Spinner />
      ) : (
        desks.map((desk) => (
          <div key={desk} className="mb-6">
            <p className="text-sm font-medium text-ink">{DESK_LABEL[desk] ?? desk}</p>
            <p className="text-xs text-faint mb-3">{DESK_BLURB[desk]}</p>
            <Stagger className="grid gap-4 sm:grid-cols-2">
              {(data ?? [])
                .filter((a) => a.desk === desk)
                .map((app) => {
                  const active = app.connections.some((c) => c.status === "ACTIVE");
                  return (
                    <Card key={`${app.desk}-${app.app}`} className="stagger-item">
                      <div className="flex items-start justify-between gap-3">
                        <p className="font-medium text-ink truncate">{app.name}</p>
                        {app.connections.length === 0 && <Badge tone="neutral">Not connected</Badge>}
                      </div>

                      {app.connections.length > 0 && (
                        <ul className="mt-3 space-y-2">
                          {app.connections.map((c) => (
                            <li key={c.connectionId} className="flex items-center gap-2">
                              {statusBadge(c.status)}
                              <span className="text-xs text-faint font-mono truncate">
                                {c.label ?? c.connectionId}
                              </span>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="ml-auto"
                                onClick={() => setDisconnect({ app, connection: c })}
                              >
                                <Trash2 size={13} /> {c.status === "ACTIVE" ? "Disconnect" : "Cancel"}
                              </Button>
                            </li>
                          ))}
                        </ul>
                      )}

                      <div className="flex items-center gap-2 mt-4">
                        <Button
                          size="sm"
                          variant={active ? "outline" : undefined}
                          disabled={busy === app.app}
                          onClick={() => void connect(app)}
                        >
                          <Cable size={13} />{" "}
                          {busy === app.app ? "Opening sign-in…" : active ? "Connect another" : "Connect"}
                        </Button>
                      </div>
                    </Card>
                  );
                })}
            </Stagger>
          </div>
        ))
      )}

      <ConfirmDelete
        open={disconnect !== null}
        onClose={() => setDisconnect(null)}
        what={disconnect ? `the ${disconnect.app.name} connection` : "connection"}
        onConfirm={async () => {
          if (!disconnect) return;
          try {
            await api(`/api/v1/connected-apps/${disconnect.connection.connectionId}`, {
              method: "DELETE",
            });
          } catch (e) {
            setActionError(e instanceof Error ? e.message : "Could not disconnect");
          }
          await refresh();
        }}
      />
    </section>
  );
}
