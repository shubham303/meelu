"use client";

import { useEffect, useState } from "react";
import { Cable, Check, Cpu, ExternalLink, Plug, Trash2 } from "lucide-react";
import { PageEnter, Stagger } from "@demo/components/animate";
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
} from "@demo/components/ui";
import { CATEGORY_LABEL, isInstallable, MCP_CATALOG, type CatalogEntry } from "@demo/lib/mcp-catalog";
import { CreditsCard } from "./credits-card";
import { formatRelative } from "@demo/lib/utils";
import type { ConnectorsView, LlmConfigView, LlmProvider } from "../agent-tasks";

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
        description="The hands. Meelu is the memory; each platform you connect here is something the agent can act through — publishing, code, data. Keys are encrypted into this device's keychain and never touch Meelu's servers."
      />

      <ModelProviderCard />
      <CreditsCard />

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
