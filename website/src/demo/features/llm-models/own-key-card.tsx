"use client";

import { useEffect, useState } from "react";
import { Check, ExternalLink, KeyRound, Trash2 } from "lucide-react";
import { Button, Card, Field, Input, Select } from "@demo/components/ui";
import type { OwnKeysView, OwnModel } from "@/app/demo/dashboard/agent-tasks";

export function OwnKeyCard() {
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  const [view, setView] = useState<OwnKeysView | null>(null);
  const [models, setModels] = useState<OwnModel[]>([]);
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const loadModels = async () => {
    const listed = await bridge?.ownModels?.();
    if (!listed) return;
    if ("error" in listed) setErr(listed.error);
    else setModels(listed.models);
  };

  useEffect(() => {
    void bridge?.getOwnKeys?.().then((res) => {
      if ("error" in res) return;
      setView(res);
      if (res.anthropic.saved) void loadModels();
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bridge]);

  if (!bridge?.saveOwnAnthropic) return null;
  const anthropic = view?.anthropic;

  const save = async (payload: { apiKey?: string; defaultModel?: string }) => {
    if (!bridge.saveOwnAnthropic) return;
    setBusy(true);
    setErr(null);
    setSaved(false);
    const res = await bridge.saveOwnAnthropic(payload);
    setBusy(false);
    if ("error" in res) {
      setErr(res.error);
      return;
    }
    setView(res);
    setApiKey("");
    setSaved(true);
    if (res.anthropic.saved) await loadModels();
    else setModels([]);
  };

  return (
    <Card className="mb-6">
      <div className="flex items-center gap-2.5">
        <KeyRound size={15} className="text-accent shrink-0" />
        <p className="font-medium text-ink">Your Anthropic key</p>
      </div>
      <p className="text-sm text-sub mt-1">
        Run tasks on your own Anthropic API key. Calls go straight from this device to Anthropic
        and are billed to your Anthropic account, not your Meelu credits. With a key saved, tasks
        use it by default; you can still pick a Meelu model for a task in the chat. The key is
        encrypted on this device and never sent to Meelu.
      </p>
      <p className="text-sm text-sub mt-2">
        On a Claude Max or Team plan? You can claim monthly API credits for your key.{" "}
        <a
          href="https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-accent hover:underline"
        >
          Claim credits <ExternalLink size={11} />
        </a>
      </p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <Field label="Anthropic API key">
          <Input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={anthropic?.saved ? "•••• key saved, type to replace" : "sk-ant-…"}
          />
        </Field>
        {anthropic?.saved && models.length > 0 && (
          <Field label="Default model">
            <Select
              value={anthropic.defaultModel}
              onChange={(e) => void save({ defaultModel: e.target.value })}
              disabled={busy}
              aria-label="Default model for your key"
            >
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </Select>
          </Field>
        )}
      </div>

      <div className="mt-4 flex items-center gap-2">
        <Button onClick={() => void save({ apiKey })} disabled={busy || !apiKey.trim()}>
          <KeyRound size={14} /> {busy ? "Checking…" : "Save key"}
        </Button>
        {anthropic?.saved && (
          <Button variant="outline" onClick={() => void save({ apiKey: "" })} disabled={busy}>
            <Trash2 size={14} /> Remove key
          </Button>
        )}
        {saved && (
          <span className="flex items-center gap-1.5 text-sm text-good">
            <Check size={14} /> Saved, applies to the next task
          </span>
        )}
      </div>
      {err && <p className="text-sm text-bad mt-2">{err}</p>}
    </Card>
  );
}
