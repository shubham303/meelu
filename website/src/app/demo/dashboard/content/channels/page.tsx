"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { PageEnter } from "@demo/components/animate";
import { Badge, Button, Card, Spinner, Textarea } from "@demo/components/ui";
import { api, useApi } from "@demo/lib/use-api";
import { cn } from "@demo/lib/utils";
import type { SiteChannel } from "@demo/lib/types";
import { AgentLaunchButton, useAgentTasks } from "../../agent-tasks";
import * as chips from "@demo/features/prompt-chips/content";
import { ChannelDot } from "../channel-dot";

export default function ChannelsPage() {
  const { data: channels, loading, refresh } = useApi<SiteChannel[]>("/api/v1/content/channels");
  const [activeKey, setActiveKey] = useState<string | null>(null);

  const list = channels ?? [];
  const active = list.find((c) => c.channelKey === (activeKey ?? list[0]?.channelKey)) ?? null;

  return (
    <PageEnter>
      <div className="mb-5">
        <Link
          href="/demo/dashboard/content"
          className="inline-flex items-center gap-1.5 text-sm text-sub transition-colors hover:text-ink"
        >
          <ArrowLeft size={14} /> Content
        </Link>
        <h1 className="mt-1 font-display text-2xl text-ink">Channel guidelines</h1>
        <p className="mt-1 max-w-2xl text-sm text-sub">
          What each channel allows. Hard limits are checked on every save so a piece fits before you
          post it; the rules are given to the agent when it writes for the channel and are yours to edit.
        </p>
      </div>

      {loading && !channels && <Spinner />}

      {active && (
        <div className="grid grid-cols-[260px_minmax(0,1fr)] gap-6 items-start">
          <Card className="p-2">
            <div className="flex flex-col gap-0.5">
              {list.map((c) => (
                <button
                  key={c.channelKey}
                  type="button"
                  onClick={() => setActiveKey(c.channelKey)}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors cursor-pointer",
                    c.channelKey === active.channelKey
                      ? "bg-panel2 font-medium text-ink"
                      : "text-sub hover:bg-panel2/60 hover:text-ink",
                    !c.enabled && "opacity-60",
                  )}
                >
                  <ChannelDot channelKey={c.channelKey} />
                  <span className="flex-1 truncate">{c.label}</span>
                  {!c.enabled && <span className="text-[10px] uppercase text-faint">off</span>}
                </button>
              ))}
            </div>
          </Card>

          <ChannelEditor key={`${active.id}:${active.updatedAt}`} channel={active} onChanged={refresh} />
        </div>
      )}
    </PageEnter>
  );
}

function ChannelEditor({
  channel,
  onChanged,
}: {
  channel: SiteChannel;
  onChanged: () => Promise<void> | void;
}) {
  const { launchTask } = useAgentTasks();
  const [rules, setRules] = useState<string[]>(channel.rules);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const isWebsite = channel.channelKey === "website";

  const dirty = JSON.stringify(rules) !== JSON.stringify(channel.rules);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setErr(null);
    try {
      await fn();
      await onChanged();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not save");
    } finally {
      setBusy(false);
    }
  }

  const save = () =>
    run(() =>
      api(`/api/v1/content/channels/${channel.channelKey}`, { method: "PUT", body: { rules } }),
    );

  const toggleEnabled = () =>
    run(() =>
      api(`/api/v1/content/channels/${channel.channelKey}`, {
        method: "PUT",
        body: { enabled: !channel.enabled },
      }),
    );

  const reset = () => run(() => api(`/api/v1/content/channels/${channel.channelKey}/reset`, { method: "POST" }));

  return (
    <div className="flex flex-col gap-4">
      <Card className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <ChannelDot channelKey={channel.channelKey} size={28} />
          <div>
            <p className="font-medium text-ink">{channel.label}</p>
            <p className="text-xs text-sub">
              {isWebsite
                ? "Your own site. Meelu writes and checks the piece; you publish it."
                : `Meelu writes and checks the piece against ${channel.label}'s limits; you post it yourself.`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone={channel.enabled ? "good" : "neutral"}>{channel.enabled ? "Enabled" : "Off"}</Badge>
          <Button variant="ghost" size="sm" disabled={busy} onClick={() => void toggleEnabled()}>
            {channel.enabled ? "Turn off" : "Turn on"}
          </Button>
        </div>
      </Card>

      <Card>
        <p className="font-medium text-ink">Hard limits</p>
        <p className="mb-3 mt-0.5 text-xs text-sub">
          Checked by Meelu itself on every save. A version that breaks one is blocked until it fits.
        </p>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Limit label="Character limit" value={channel.characterLimit > 0 ? channel.characterLimit.toLocaleString() : "None"} />
          <Limit
            label="Image"
            value={channel.requiresMedia ? `Required · max ${channel.maxMedia}` : channel.maxMedia > 0 ? `Optional · max ${channel.maxMedia}` : "None"}
          />
          <Limit
            label="Links"
            value={channel.maxLinks === null ? "Unlimited" : channel.maxLinks === 0 ? "None in the body" : `${channel.maxLinks} max`}
          />
          <Limit
            label="Hashtags"
            value={channel.maxHashtags === null ? "Unlimited" : channel.maxHashtags === 0 ? "None" : `Max ${channel.maxHashtags}`}
          />
        </div>
      </Card>

      <Card>
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="font-medium text-ink">Writing rules</p>
            <p className="mt-0.5 text-xs text-sub">
              Given to the agent when it drafts for this channel. One rule per line.
            </p>
          </div>
          <Badge tone="neutral">{rules.length} rules</Badge>
        </div>
        <div className="mt-3">
          <AgentLaunchButton
            title="Tune with Meelu"
            hint="Reshape these rules in a chat — it replaces the whole list only when you say so."
            onClick={() =>
              launchTask({
                title: `Rules for ${channel.label}`,
                endpoint: "/api/agent/content-channel-rules",
                emptyHint:
                  "Say what should change — “more casual”, “never mention pricing”, “add a rule about always crediting photographers”. It saves only when you say so.",
                suggestions: chips.channelRules,
                draft: {
                  channel: `${channel.label} (channelKey ${channel.channelKey})`,
                  rules: channel.rules.join("\n"),
                },
                onCreated: async () => {
                  await onChanged();
                },
              })
            }
          />
        </div>
        <Textarea
          value={rules.join("\n")}
          onChange={(e) => setRules(e.target.value.split("\n"))}
          className="mt-3 min-h-72 font-mono text-[13px] leading-relaxed"
        />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button size="sm" disabled={busy || !dirty} onClick={() => void save()}>
            Save
          </Button>
          <Button variant="ghost" size="sm" disabled={busy} onClick={() => void reset()}>
            Reset rules to platform defaults
          </Button>
          {dirty && <span className="text-xs text-faint">Unsaved changes</span>}
          {err && <span className="text-xs text-bad">{err}</span>}
        </div>
      </Card>
    </div>
  );
}

function Limit({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-edge px-3 py-2.5">
      <p className="text-xs text-faint">{label}</p>
      <p className="mt-0.5 text-sm font-medium text-ink">{value}</p>
    </div>
  );
}
