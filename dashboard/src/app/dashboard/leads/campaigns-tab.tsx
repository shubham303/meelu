"use client";

import { useState } from "react";
import { Plus, Send } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  ConfirmDelete,
  EmptyState,
  Field,
  Input,
  Select,
  Textarea,
} from "@/components/ui";
import { cn, formatRelative } from "@/lib/utils";
import { api } from "@/lib/use-api";
import type { LeadCampaign, LeadSummary } from "@/lib/types";
import { Funnel } from "./funnel";
import type { SourceInfo } from "./lib";

interface Draft {
  name: string;
  audience: string;
  sources: string[];
  schedule: "" | "daily" | "weekly";
}

function toDraft(c: LeadCampaign | null): Draft {
  return {
    name: c?.name ?? "",
    audience: c?.audience ?? "",
    sources: c?.sources ?? ["web-search", "hackernews"],
    schedule: c?.schedule ?? "",
  };
}

export function CampaignsTab({
  campaigns,
  summary,
  sources,
  refresh,
  onRun,
  running,
  isApp,
}: {
  campaigns: LeadCampaign[];
  summary: LeadSummary | null;
  sources: SourceInfo[];
  refresh: () => Promise<void>;
  onRun: (campaignId: string) => void;
  running: boolean;
  isApp: boolean;
}) {
  const [openId, setOpenId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const saved = async () => {
    setCreating(false);
    setOpenId(null);
    await refresh();
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-faint max-w-xl">
          A campaign is one standing play: who to look for and where Meelu searches.
          Discovery runs in the app on the schedule or on demand.
        </p>
        <Button size="sm" onClick={() => setCreating(true)} disabled={creating}>
          <Plus size={13} /> New campaign
        </Button>
      </div>

      {creating && (
        <CampaignEditor
          campaign={null}
          sources={sources}
          onDone={saved}
          onCancel={() => setCreating(false)}
        />
      )}

      {campaigns.length === 0 && !creating ? (
        <EmptyState
          icon={Send}
          title="No campaigns yet"
          hint="Start with one audience — who to look for. Meelu handles the finding and qualifying."
          action={
            <Button size="sm" onClick={() => setCreating(true)}>
              <Plus size={13} /> New campaign
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {campaigns.map((c) =>
            openId === c.id ? (
              <CampaignEditor
                key={c.id}
                campaign={c}
                stats={summary?.campaigns.find((s) => s.id === c.id) ?? null}
                sources={sources}
                onDone={saved}
                onCancel={() => setOpenId(null)}
                onRun={isApp && !running ? () => onRun(c.id) : undefined}
              />
            ) : (
              <CampaignRow
                key={c.id}
                campaign={c}
                stats={summary?.campaigns.find((s) => s.id === c.id) ?? null}
                onOpen={() => setOpenId(c.id)}
                refresh={refresh}
              />
            ),
          )}
        </div>
      )}
    </div>
  );
}

function CampaignRow({
  campaign,
  stats,
  onOpen,
  refresh,
}: {
  campaign: LeadCampaign;
  stats: LeadSummary["campaigns"][number] | null;
  onOpen: () => void;
  refresh: () => Promise<void>;
}) {
  const toggleStatus = async () => {
    await api(`/api/v1/lead-management/campaigns/${campaign.id}`, {
      method: "PATCH",
      body: { status: campaign.status === "paused" ? "active" : "paused" },
    });
    await refresh();
  };

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-display text-base text-ink">{campaign.name}</h3>
          <p className="text-xs text-faint mt-0.5">
            {stats
              ? `${stats.qualified} qualified · ${stats.shortlisted} shortlisted`
              : campaign.audience.slice(0, 120)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone={campaign.status === "active" ? "good" : "neutral"}>
            {campaign.status}
          </Badge>
          {campaign.schedule && <Badge>{campaign.schedule}</Badge>}
          <Button size="sm" variant="ghost" onClick={() => void toggleStatus()}>
            {campaign.status === "paused" ? "Resume" : "Pause"}
          </Button>
          <Button size="sm" variant="ghost" onClick={onOpen}>
            Open
          </Button>
        </div>
      </div>
    </Card>
  );
}

function CampaignEditor({
  campaign,
  stats,
  sources,
  onDone,
  onCancel,
  onRun,
}: {
  campaign: LeadCampaign | null;
  stats?: LeadSummary["campaigns"][number] | null;
  sources: SourceInfo[];
  onDone: () => Promise<void>;
  onCancel: () => void;
  onRun?: () => void;
}) {
  const [draft, setDraft] = useState<Draft>(() => toDraft(campaign));
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = <K extends keyof Draft>(k: K, v: Draft[K]) => setDraft((d) => ({ ...d, [k]: v }));

  const free = sources.filter((s) => s.access === "free");
  const apify = sources.filter((s) => s.access === "apify");
  const apifyConnected = apify.some((s) => s.available);

  const toggleSource = (s: SourceInfo) => {
    if (!s.available) return;
    set(
      "sources",
      draft.sources.includes(s.id)
        ? draft.sources.filter((x) => x !== s.id)
        : [...draft.sources, s.id],
    );
  };

  const save = async () => {
    if (!draft.name.trim() || !draft.audience.trim()) {
      setError("A campaign needs a name and who to look for.");
      return;
    }
    setSaving(true);
    setError(null);
    const body = {
      name: draft.name.trim(),
      audience: draft.audience.trim(),
      sources: draft.sources,
      schedule: draft.schedule || null,
    };
    try {
      if (campaign) {
        await api(`/api/v1/lead-management/campaigns/${campaign.id}`, { method: "PATCH", body });
      } else {
        await api("/api/v1/lead-management/campaigns", { method: "POST", body });
      }
      await onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The campaign did not save.");
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!campaign) return;
    await api(`/api/v1/lead-management/campaigns/${campaign.id}`, { method: "DELETE" });
    await onDone();
  };

  return (
    <Card className="border-accent/30">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <Input
          className="w-72 font-medium"
          placeholder="Campaign name"
          value={draft.name}
          onChange={(e) => set("name", e.target.value)}
        />
        {campaign && (
          <div className="flex items-center gap-2">
            <Badge tone={campaign.status === "active" ? "good" : "neutral"}>
              {campaign.status}
            </Badge>
            {campaign.schedule && <Badge>{campaign.schedule}</Badge>}
          </div>
        )}
      </div>

      {stats && (
        <div className="mt-3">
          <Funnel
            segments={[
              { label: "qualified", value: stats.qualified },
              { label: "shortlisted", value: stats.shortlisted, tone: "good" },
            ]}
          />
        </div>
      )}

      <p className="text-xs font-medium uppercase tracking-wide text-faint mt-4 mb-2">
        The brief
      </p>
      <div className="flex flex-col gap-4 lg:flex-row">
        <div className="flex-1 space-y-3 min-w-0">
          <Field label="Who to look for">
            <Textarea
              rows={2}
              value={draft.audience}
              onChange={(e) => set("audience", e.target.value)}
            />
          </Field>
          <div className="flex flex-wrap gap-3">
            <div className="min-w-[130px]">
              <Field label="Schedule">
                <Select
                  value={draft.schedule}
                  onChange={(e) => set("schedule", e.target.value as Draft["schedule"])}
                >
                  <option value="">Off — on demand</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                </Select>
              </Field>
            </div>
          </div>
        </div>

        <div className="w-full lg:w-72 shrink-0">
          <p className="text-xs font-medium text-sub mb-1.5">Sources</p>
          <p className="text-[11px] uppercase tracking-wide text-faint mt-2 mb-1.5">
            Free — no setup
          </p>
          <div className="flex flex-wrap gap-1.5">
            {free.map((s) => (
              <SourceChip
                key={s.id}
                info={s}
                on={draft.sources.includes(s.id)}
                onToggle={() => toggleSource(s)}
              />
            ))}
          </div>
          <p className="text-[11px] uppercase tracking-wide text-faint mt-3 mb-1.5">
            Paid sources (credits)
          </p>
          <div className="flex flex-wrap gap-1.5">
            {apify.map((s) => (
              <SourceChip
                key={s.id}
                info={s}
                on={draft.sources.includes(s.id) && s.available}
                onToggle={() => toggleSource(s)}
              />
            ))}
          </div>
          {!apifyConnected && (
            <p className="text-xs text-faint mt-2">
              These sources are not enabled on the server yet.
            </p>
          )}
        </div>
      </div>

      {error && <p className="mt-3 text-sm text-bad">{error}</p>}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button size="sm" onClick={() => void save()} disabled={saving}>
          {saving ? "Saving…" : "Save brief"}
        </Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>
          Close
        </Button>
        {onRun && campaign && (
          <Button size="sm" variant="outline" onClick={onRun}>
            <Send size={13} /> Find leads now
          </Button>
        )}
        {campaign && (
          <Button
            size="sm"
            variant="ghost"
            className="ml-auto text-bad"
            onClick={() => setConfirming(true)}
          >
            Delete
          </Button>
        )}
      </div>
      {campaign && (
        <ConfirmDelete
          open={confirming}
          onClose={() => setConfirming(false)}
          onConfirm={remove}
          what={`the "${campaign.name}" campaign`}
        />
      )}
      {campaign && (
        <p className="text-xs text-faint mt-2">
          Created {formatRelative(campaign.createdAt)}. Meelu keeps what clears the fit bar —
          there is no lead quota.
        </p>
      )}
    </Card>
  );
}

function SourceChip({
  info,
  on,
  onToggle,
}: {
  info: SourceInfo;
  on: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={!info.available}
      title={
        info.available ? undefined : "Needs a connected token — set it up on the Connections screen."
      }
      className={cn(
        "rounded-full border px-3 py-1 text-[13px] transition-colors",
        !info.available
          ? "border-edge text-faint cursor-not-allowed opacity-60"
          : on
            ? "border-accent bg-accent-soft text-accent cursor-pointer"
            : "border-edge text-sub hover:text-ink cursor-pointer",
      )}
    >
      {info.label}
    </button>
  );
}
