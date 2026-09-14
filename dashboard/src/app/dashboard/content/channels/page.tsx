"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Cable, Plus, Trash2 } from "lucide-react";
import { PageEnter } from "@/components/animate";
import { Badge, Button, Card, Field, Input, Select, Spinner, Textarea } from "@/components/ui";
import { api, useApi } from "@/lib/use-api";
import { useIsApp } from "@/lib/use-app-mode";
import {
  APP_ONLY_NOTE,
  providerCall,
  useProviderConnected,
  type SocialProfilesResult,
} from "@/lib/providers";
import { cn } from "@/lib/utils";
import type { PostingWindow, SiteChannel } from "@/lib/types";
import { AgentLaunchButton, useAgentTasks } from "../../agent-tasks";
import * as chips from "@/features/prompt-chips/content";
import { ChannelDot } from "../channel-dot";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function ChannelsPage() {
  const { data: channels, loading, refresh } = useApi<SiteChannel[]>("/api/v1/content/channels");
  const isApp = useIsApp();
  const managed = useProviderConnected("social");
  const [social, setSocial] = useState<SocialProfilesResult | null>(null);
  const socialStamp = social ? JSON.stringify(social.profiles) : null;
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!isApp || !managed) return;
    const load = () =>
      providerCall<SocialProfilesResult>("social_profiles")
        .then(setSocial)
        .catch(() => setSocial(null));
    void load();
    const onFocus = () => void load();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [isApp, managed]);

  useEffect(() => {
    if (socialStamp !== null) void refresh();
  }, [socialStamp, refresh]);

  const connected = useMemo(
    () =>
      new Set((social?.profiles ?? []).filter((p) => p.status === "active").map((p) => p.platform)),
    [social],
  );

  const list = channels ?? [];
  const active = list.find((c) => c.channelKey === (activeKey ?? list[0]?.channelKey)) ?? null;

  async function connect(channelKey: string) {
    setErr(null);
    try {
      const link = await providerCall<{ url: string }>("social_connect_link", {
        platform: channelKey,
      });
      window.open(link.url, "_blank", "noopener");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not start the connection.");
    }
  }

  return (
    <PageEnter>
      <div className="mb-5">
        <Link
          href="/dashboard/content"
          className="inline-flex items-center gap-1.5 text-sm text-sub transition-colors hover:text-ink"
        >
          <ArrowLeft size={14} /> Content
        </Link>
        <h1 className="mt-1 font-display text-2xl text-ink">Channel guidelines</h1>
        <p className="mt-1 max-w-2xl text-sm text-sub">
          What each channel allows. Hard limits are checked before anything can be scheduled;
          the rules are given to the agent when it writes a piece for the channel and are yours to edit.
        </p>
      </div>

      {err && <p className="mb-3 text-sm text-bad">{err}</p>}
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

          <ChannelEditor
            key={`${active.id}:${active.updatedAt}`}
            channel={active}
            connected={connected.has(active.channelKey)}
            managed={isApp && managed}
            isApp={isApp}
            onConnect={() => void connect(active.channelKey)}
            onChanged={refresh}
          />
        </div>
      )}
    </PageEnter>
  );
}

function ChannelEditor({
  channel,
  connected,
  managed,
  isApp,
  onConnect,
  onChanged,
}: {
  channel: SiteChannel;
  connected: boolean;
  managed: boolean;
  isApp: boolean;
  onConnect: () => void;
  onChanged: () => Promise<void> | void;
}) {
  const { launchTask } = useAgentTasks();
  const [rules, setRules] = useState<string[]>(channel.rules);
  const [timezone, setTimezone] = useState(channel.timezone);
  const [minGap, setMinGap] = useState(String(channel.minGapHours));
  const [windows, setWindows] = useState<PostingWindow[]>(channel.postingWindows);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const isWebsite = channel.channelKey === "website";

  const dirty =
    JSON.stringify(rules) !== JSON.stringify(channel.rules) ||
    timezone !== channel.timezone ||
    minGap !== String(channel.minGapHours) ||
    JSON.stringify(windows) !== JSON.stringify(channel.postingWindows);

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
      api(`/api/v1/content/channels/${channel.channelKey}`, {
        method: "PUT",
        body: { rules, timezone, minGapHours: Number(minGap), postingWindows: windows },
      }),
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
                ? "Your own site — published by hand, recorded here."
                : connected
                  ? "Connected — pieces for this channel are scheduled and posted through it"
                  : managed
                    ? "Not connected — connect the account to write and schedule for this channel"
                    : isApp
                      ? "Connect a social publishing provider on the Connections screen"
                      : APP_ONLY_NOTE}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isWebsite ? (
            <>
              <Badge tone={channel.enabled ? "good" : "neutral"}>
                {channel.enabled ? "Enabled" : "Off"}
              </Badge>
              <Button variant="ghost" size="sm" disabled={busy} onClick={() => void toggleEnabled()}>
                {channel.enabled ? "Turn off" : "Turn on"}
              </Button>
            </>
          ) : connected ? (
            <Badge tone="good">Connected</Badge>
          ) : (
            <>
              <Badge tone="neutral">Not connected</Badge>
              {managed && (
                <Button variant="outline" size="sm" onClick={onConnect}>
                  <Cable size={14} /> Connect
                </Button>
              )}
            </>
          )}
        </div>
      </Card>

      <Card>
        <p className="font-medium text-ink">Hard limits</p>
        <p className="mb-3 mt-0.5 text-xs text-sub">
          Checked by Meelu itself on every save. A version that breaks one is blocked until it fits.
        </p>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
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
          <Field label="Min gap between posts" hint="hours">
            <Input value={minGap} onChange={(e) => setMinGap(e.target.value)} inputMode="numeric" />
          </Field>
          <Field label="Timezone" hint="for slots and windows">
            <Input value={timezone} onChange={(e) => setTimezone(e.target.value)} placeholder="UTC" />
          </Field>
        </div>
      </Card>

      {!isWebsite && (
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-ink">Posting windows</p>
              <p className="mt-0.5 text-xs text-sub">
                When free slots are offered. No windows means any hour.
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={() => setWindows([...windows, { days: [1, 3], time: "09:00" }])}>
              <Plus size={14} /> Window
            </Button>
          </div>
          {windows.length > 0 && (
            <div className="mt-3 flex flex-col gap-2">
              {windows.map((w, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2 rounded-lg border border-edge bg-panel2 px-3 py-2">
                  <div className="flex gap-1">
                    {WEEKDAYS.map((d, day) => (
                      <button
                        key={d}
                        type="button"
                        onClick={() =>
                          setWindows(
                            windows.map((x, j) =>
                              j === i
                                ? {
                                    ...x,
                                    days: x.days.includes(day)
                                      ? x.days.filter((v) => v !== day)
                                      : [...x.days, day].sort(),
                                  }
                                : x,
                            ),
                          )
                        }
                        className={cn(
                          "h-7 w-9 rounded-md text-xs transition-colors cursor-pointer",
                          w.days.includes(day) ? "bg-accent text-white" : "bg-panel text-sub hover:text-ink",
                        )}
                      >
                        {d}
                      </button>
                    ))}
                  </div>
                  <Select
                    value={w.time}
                    onChange={(e) => setWindows(windows.map((x, j) => (j === i ? { ...x, time: e.target.value } : x)))}
                    className="w-28"
                  >
                    {Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, "0")}:00`).map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </Select>
                  <button
                    type="button"
                    onClick={() => setWindows(windows.filter((_, j) => j !== i))}
                    className="ml-auto rounded-md p-1.5 text-sub hover:text-bad cursor-pointer"
                    aria-label="Remove window"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

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
