"use client";

import { useEffect, useState } from "react";
import { Cable, Check, Cpu, ExternalLink, Mail, Plug, Trash2 } from "lucide-react";
import { PageEnter, Stagger } from "@/components/animate";
import {
  Badge,
  Button,
  Card,
  ConfirmDelete,
  Field,
  Input,
  Modal,
  PageHeader,
  Select,
  Spinner,
} from "@/components/ui";
import { CATEGORY_LABEL, isInstallable, MCP_CATALOG, type CatalogEntry } from "@/lib/mcp-catalog";
import { GLOBAL } from "@/lib/current-site";
import { api, useApi, useCurrentSite } from "@/lib/use-api";
import { SearchDataCard, SocialPublishingCard } from "./provider-cards";
import { formatRelative } from "@/lib/utils";
import type { ConnectorsView, LlmConfigView, LlmProvider, MailboxAccountsView } from "../agent-tasks";
import type { SiteProfile } from "@/lib/types";

const MODEL_PLACEHOLDER: Record<LlmProvider, string> = {
  anthropic: "claude-haiku-4-5 (default)",
  openrouter: "e.g. anthropic/claude-sonnet-5",
  llamacpp: "blank — the server runs one model",
  custom: "e.g. qwen3.5:35b-a3b",
};

const KEY_LABEL: Record<LlmProvider, string> = {
  anthropic: "API key",
  openrouter: "API key",
  llamacpp: "API key (if llama-server was started with --api-key)",
  custom: "API key (if your endpoint checks one)",
};

const KEY_PLACEHOLDER: Record<LlmProvider, string> = {
  anthropic: "sk-ant-… (blank = this machine's Claude login)",
  openrouter: "sk-or-v1-…",
  llamacpp: "usually blank",
  custom: "usually blank",
};

const BASE_URL_PLACEHOLDER: Partial<Record<LlmProvider, string>> = {
  llamacpp: "http://localhost:8080 (default)",
  custom: "http://localhost:11434",
};

function ModelProviderCard() {
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  const [view, setView] = useState<LlmConfigView | null>(null);
  const [provider, setProvider] = useState<LlmProvider>("anthropic");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    bridge?.getLlmConfig?.().then((res) => {
      if ("error" in res) return;
      setView(res);
      setProvider(res.provider);
      setModel(res.model);
      setBaseUrl(res.baseUrl);
    });
  }, [bridge]);

  if (!bridge) return null;

  const apply = async (key: string | undefined) => {
    if (!bridge.setLlmConfig) {
      setErr("This app build predates model settings — restart the app after updating.");
      return;
    }
    setBusy(true);
    setErr(null);
    setSaved(false);
    const res = await bridge.setLlmConfig({ provider, model, baseUrl, apiKey: key });
    setBusy(false);
    if ("error" in res) {
      setErr(res.error);
      return;
    }
    setView(res);
    setApiKey("");
    setSaved(true);
  };

  return (
    <Card className="mb-6">
      <div className="flex items-center gap-2.5">
        <Cpu size={15} className="text-accent shrink-0" />
        <p className="font-medium text-ink">Model &amp; provider</p>
        {view?.saved && <Badge tone="good">set</Badge>}
      </div>
      <p className="text-sm text-sub mt-1">
        The brain. Tasks run on this device against the provider you pick here — your key,
        your model, never our server&apos;s.
      </p>
      {provider === "openrouter" && (
        <p className="text-sm text-sub mt-2">
          OpenRouter routes to any model it carries, named provider-first. Tasks here are
          agentic — they lean on tool calling and long turns, so pick a model that handles
          both well.
        </p>
      )}
      {provider === "llamacpp" && (
        <p className="text-sm text-sub mt-2">
          A recent llama-server speaks the Anthropic Messages API. Start it with{" "}
          <code>--jinja</code> so the model can call tools, and load a model that handles
          tool calling and long turns well.
        </p>
      )}

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <Field label="Provider">
          <Select
            value={provider}
            onChange={(e) => setProvider(e.target.value as LlmProvider)}
            aria-label="LLM provider"
          >
            <option value="anthropic">Anthropic API</option>
            <option value="openrouter">OpenRouter</option>
            <option value="llamacpp">llama.cpp (llama-server)</option>
            <option value="custom">Custom endpoint (Ollama, LM Studio, proxy)</option>
          </Select>
        </Field>
        <Field label="Model">
          <Input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder={MODEL_PLACEHOLDER[provider]}
          />
        </Field>
        {(provider === "custom" || provider === "llamacpp") && (
          <Field label="Base URL">
            <Input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder={BASE_URL_PLACEHOLDER[provider]}
            />
          </Field>
        )}
        <Field label={KEY_LABEL[provider]}>
          <div className="space-y-1.5">
            <Input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={
                view?.hasApiKey ? "•••• key saved — type to replace" : KEY_PLACEHOLDER[provider]
              }
            />
            {provider === "openrouter" && (
              <a
                href="https://openrouter.ai/keys"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs text-accent hover:underline"
              >
                Get your key <ExternalLink size={11} />
              </a>
            )}
          </div>
        </Field>
      </div>

      <div className="mt-4 flex items-center gap-2">
        <Button onClick={() => void apply(apiKey ? apiKey : undefined)} disabled={busy}>
          <Plug size={14} /> Save
        </Button>
        {view?.hasApiKey && (
          <Button variant="outline" onClick={() => void apply("")} disabled={busy}>
            <Trash2 size={14} /> Remove key
          </Button>
        )}
        {saved && (
          <span className="flex items-center gap-1.5 text-sm text-good">
            <Check size={14} /> Saved — applies to the next task
          </span>
        )}
      </div>
      {err && <p className="text-sm text-bad mt-2">{err}</p>}
    </Card>
  );
}

interface MailboxField {
  key: string;
  label: string;
  help: string;
  placeholder: string;
  secret: boolean;
  optional?: boolean;
  url?: string;
}

const MAILBOX_FORM: { name: string; blurb: string; docsUrl: string; fields: MailboxField[] } = {
  name: "Your mailbox",
  blurb:
    "Send and read email as YOU — your own address over IMAP/SMTP with an app password. Replies land in your real inbox.",
  docsUrl: "https://support.google.com/accounts/answer/185833",
  fields: [
    {
      key: "address",
      label: "Email address",
      help: "The mailbox to send from and read — your real address.",
      placeholder: "you@gmail.com",
      secret: false,
    },
    {
      key: "password",
      label: "App password",
      help: "NOT your normal password: turn on 2-Step Verification, then create an app password. Gmail, Zoho, Fastmail, iCloud and custom IMAP mailboxes work.",
      placeholder: "abcd efgh ijkl mnop",
      secret: true,
      url: "https://myaccount.google.com/apppasswords",
    },
    {
      key: "imapHost",
      label: "IMAP host",
      help: "Leave blank to auto-detect — big providers by address, custom domains by their MX records. Set it only for a self-hosted or unusual provider.",
      placeholder: "",
      secret: false,
      optional: true,
    },
    {
      key: "smtpHost",
      label: "SMTP host",
      help: "Leave blank to auto-detect, same as the IMAP host.",
      placeholder: "",
      secret: false,
      optional: true,
    },
  ],
};

function MailboxCard() {
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  const selected = useCurrentSite();
  const site = selected && selected !== GLOBAL ? selected : null;
  const entry = MAILBOX_FORM;

  const [view, setView] = useState<MailboxAccountsView | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [forgetting, setForgetting] = useState<{ id: string; address: string } | null>(null);

  useEffect(() => {
    void bridge?.getMailboxAccounts?.().then((res) => {
      if (!("error" in res)) setView(res);
    });
  }, [bridge]);

  const { data: siteRecord, refresh: refreshSite } = useApi<SiteProfile>(
    site ? `/sites/${site}` : null,
  );

  if (!bridge?.getMailboxAccounts) return null;

  const accounts = view?.accounts ?? [];
  const intended = null;
  const here = intended !== null && accounts.some((a) => a.id === intended);
  const inUse = here ? intended : intended === null && accounts.length === 1 ? accounts[0].id : null;
  const missing = intended !== null && !here;

  const apply = (res: MailboxAccountsView | { error: string }) => {
    if ("error" in res) {
      setErr(res.error as string);
      return false;
    }
    setView(res);
    setErr(null);
    return true;
  };

  const choose = async (address: string | null) => {
    if (!site) return;
    setBusy(true);
    try {
      await api(`/sites/${site}`, { method: "PATCH", body: { sendingAddress: address } });
      await refreshSite();
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not set the sending address.");
    }
    setBusy(false);
  };

  const connect = async () => {
    if (!bridge.connectMailbox) return;
    for (const f of entry.fields) {
      if (!f.optional && (values[f.key] ?? "").trim() === "") {
        setErr(`Missing required field: ${f.label}`);
        return;
      }
    }
    setBusy(true);
    const res = await bridge.connectMailbox(
      values,
      entry.fields.filter((f) => f.secret).map((f) => f.key),
    );
    setBusy(false);
    if (!apply(res)) return;
    setModalOpen(false);
    const connectedId = "connectedId" in res ? res.connectedId : undefined;
    if (site && connectedId) await choose(connectedId);
  };

  return (
    <Card className="mb-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Mail size={15} className="text-sub shrink-0" />
            <p className="font-medium text-ink truncate">{entry.name}</p>
          </div>
          <p className="text-xs text-faint mt-0.5">
            One mailbox per website — this is the address its outreach is sent and read from.
          </p>
        </div>
        {inUse ? <Badge tone="good">Connected</Badge> : <Badge tone="neutral">Not connected</Badge>}
      </div>

      {!site ? (
        <p className="text-sm text-sub mt-3">
          Pick a website above to choose the mailbox it writes from.
        </p>
      ) : (
        <>
          {missing && (
            <p className="text-sm text-warn mt-3">
              This website sends as <span className="text-ink">{intended}</span>, but that mailbox
              is not connected on this device. Connect it below, or pick a different address —
              nothing will be sent as anything else.
            </p>
          )}

          {accounts.length === 0 ? (
            <p className="text-sm text-sub mt-3">
              No mailbox connected on this device yet. Connect one and this website will write
              from it.
            </p>
          ) : (
            <div className="mt-3 space-y-1.5">
              {accounts.map((a) => {
                const active = a.id === inUse;
                return (
                  <div
                    key={a.id}
                    className="flex items-center gap-3 rounded-md border border-line px-3 py-2"
                  >
                    <label className="flex items-center gap-2.5 min-w-0 flex-1 cursor-pointer">
                      <input
                        type="radio"
                        name="mailbox-account"
                        checked={active}
                        disabled={busy}
                        onChange={() => void choose(a.id)}
                        className="shrink-0"
                      />
                      <span className="min-w-0">
                        <span className="block text-sm text-ink truncate">{a.address}</span>
                        {a.updatedAt && (
                          <span className="block text-xs text-faint">
                            Connected {formatRelative(a.updatedAt)}
                            {active && intended === null && " · used by default"}
                          </span>
                        )}
                      </span>
                    </label>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setForgetting({ id: a.id, address: a.address })}
                    >
                      <Trash2 size={13} /> Forget
                    </Button>
                  </div>
                );
              })}
            </div>
          )}

          <div className="flex items-center gap-2 mt-4">
            <Button
              size="sm"
              variant={accounts.length === 0 ? "primary" : "outline"}
              disabled={busy}
              onClick={() => {
                setValues({});
                setErr(null);
                setModalOpen(true);
              }}
            >
              <Cable size={13} /> {accounts.length === 0 ? "Connect a mailbox" : "Connect another"}
            </Button>
            <a
              href={entry.docsUrl}
              target="_blank"
              rel="noreferrer"
              className="ml-auto inline-flex items-center gap-1 text-xs text-sub hover:text-ink transition-colors"
            >
              Docs <ExternalLink size={11} />
            </a>
          </div>
        </>
      )}

      {err && <p className="text-sm text-bad mt-2">{err}</p>}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Connect a mailbox">
        <div className="space-y-4">
          <p className="text-sm text-sub">{entry.blurb}</p>
          {entry.fields.map((f) => (
            <Field
              key={f.key}
              label={f.optional ? `${f.label} (optional)` : f.label}
              hint={f.help}
            >
              <div className="space-y-1.5">
                <Input
                  type={f.secret ? "password" : "text"}
                  value={values[f.key] ?? ""}
                  onChange={(ev) => setValues((v) => ({ ...v, [f.key]: ev.target.value }))}
                  placeholder={f.placeholder}
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
            <Button variant="ghost" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button disabled={busy} onClick={connect}>
              Connect
            </Button>
          </div>
        </div>
      </Modal>

      <ConfirmDelete
        open={forgetting !== null}
        onClose={() => setForgetting(null)}
        what={
          forgetting
            ? `${forgetting.address} — every website using it will be left without a mailbox`
            : "mailbox"
        }
        onConfirm={async () => {
          if (!forgetting || !bridge.forgetMailbox) return;
          apply(await bridge.forgetMailbox(forgetting.id));
        }}
      />
    </Card>
  );
}

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

  const [entry, setEntry] = useState<CatalogEntry | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [values, setValues] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
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

  const openConnect = (e: CatalogEntry) => {
    if (e.connect) return void runOauthConnect(e);
    setEntry(e);
    setValues({});
    setErr(null);
    setModalOpen(true);
  };

  const save = async () => {
    if (!entry || !bridge?.setConnector) return;
    for (const f of entry.fields ?? []) {
      if (!f.optional && (values[f.key] ?? "").trim() === "") {
        setErr(`Missing required field: ${f.label}`);
        return;
      }
    }
    setBusy(true);
    setErr(null);
    const res = await bridge.setConnector(
      entry.id,
      values,
      (entry.fields ?? []).filter((f) => f.secret).map((f) => f.key),
    );
    setBusy(false);
    if ("error" in res) {
      setErr(res.error as string);
      return;
    }
    setConnectors(res);
    setModalOpen(false);
  };

  return (
    <PageEnter>
      <PageHeader
        title="Connections"
        description="The hands. Meelu is the memory; each platform you connect here is something the agent can act through — email, publishing, code. Keys are encrypted into this device's keychain and never touch Meelu's servers."
      />

      <ModelProviderCard />
      <SocialPublishingCard />
      <SearchDataCard />
      <MailboxCard />

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
            const needsKey = (e.fields ?? []).length > 0;
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
                        {(needsKey || isOauth) && (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={waiting}
                            onClick={() => openConnect(e)}
                          >
                            <Plug size={13} />{" "}
                            {isOauth
                              ? waiting
                                ? "Waiting for Google…"
                                : "Reconnect"
                              : "Update key"}
                          </Button>
                        )}
                        <Button size="sm" variant="ghost" onClick={() => setDisconnect(e)}>
                          <Trash2 size={13} /> Disconnect
                        </Button>
                      </>
                    ) : (
                      <Button size="sm" disabled={waiting} onClick={() => openConnect(e)}>
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

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={entry ? `Connect ${entry.name}` : "Connect"}
      >
        {entry && (
          <div className="space-y-4">
            <p className="text-sm text-sub">{entry.blurb}</p>
            {(entry.fields ?? []).length === 0 ? (
              <p className="text-sm text-sub">
                No key needed — {entry.name} authenticates in the browser the first time the
                agent uses it. Connecting just tells Meelu it&apos;s available.
              </p>
            ) : (
              (entry.fields ?? []).map((f) => (
                <Field
                  key={f.key}
                  label={f.optional ? `${f.label} (optional)` : f.label}
                  hint={f.help}
                >
                  <div className="space-y-1.5">
                    <Input
                      type={f.secret ? "password" : "text"}
                      value={values[f.key] ?? ""}
                      onChange={(ev) =>
                        setValues((v) => ({ ...v, [f.key]: ev.target.value }))
                      }
                      placeholder={f.placeholder}
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
              ))
            )}
            {err && <p className="text-sm text-bad">{err}</p>}
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button disabled={busy} onClick={save}>
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
          if (!disconnect || !bridge?.removeConnector) return;
          const res = await bridge.removeConnector(disconnect.id);
          if (!("error" in res)) setConnectors(res);
        }}
      />
    </PageEnter>
  );
}
