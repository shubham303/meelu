"use client";

import { Check } from "lucide-react";
import { Badge, Button, Card, Spinner, StatCard } from "@/components/ui";
import { usePagedApi } from "@/lib/use-api";
import { formatRelative } from "@/lib/utils";
import type { Lead, LeadSummary } from "@/lib/types";
import { leadsQuery, sourceLabel, STAGE_TONE } from "./lib";
import { Funnel } from "./funnel";
import type { LiveRun } from "./page";

export function OverviewTab({
  summary,
  live,
  running,
  onStop,
  campaignName,
  onOpenLead,
  onCampaignsTab,
  version,
}: {
  summary: LeadSummary | null;
  live: LiveRun;
  running: boolean;
  onStop: () => void;
  campaignName: (id: string | null) => string | null;
  onOpenLead: (lead: Lead) => void;
  onCampaignsTab: () => void;
  version: number;
}) {
  const { data: shortlistedPage, loading } = usePagedApi<Lead>(
    leadsQuery({ stage: "shortlisted", sort: "newest", page_size: 3, v: version }),
  );
  const shortlisted = shortlistedPage?.data ?? [];

  const stages = summary?.stages;
  const lastRun = summary?.lastRun ?? null;

  return (
    <div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 mb-4">
        <StatCard
          label="Found"
          value={stages?.found ?? 0}
          hint="pulled in by discovery, below or awaiting the fit bar"
        />
        <StatCard
          label="Qualified"
          value={stages?.qualified ?? 0}
          hint="cleared the fit bar, worth a look"
        />
        <StatCard
          label="Shortlisted"
          value={stages?.shortlisted ?? 0}
          hint="the ones you picked to pursue"
        />
      </div>

      {(running || Object.keys(live.sourceState).length > 0 || lastRun?.status === "running") && (
        <Card className="mb-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            <span className="font-medium text-ink">
              {running || lastRun?.status === "running"
                ? live.stageDetail || "Finding leads…"
                : "Last run"}
            </span>
            {Object.entries(live.sourceState).map(([id, s]) => (
              <span
                key={id}
                className="inline-flex items-center gap-1.5 rounded-full border border-edge2 bg-panel px-2.5 py-0.5 text-xs text-sub"
              >
                {s.status === "done" && <Check size={12} className="text-good" />}
                {s.status === "fetching" && <Spinner className="h-3 w-3 py-0" />}
                {s.status === "error" && (
                  <span className="text-bad" title={s.error}>
                    ✗
                  </span>
                )}
                {sourceLabel(id)}
                {s.count != null && ` · ${s.count}`}
              </span>
            ))}
            {running && (
              <Button size="sm" variant="ghost" className="ml-auto" onClick={onStop}>
                Stop
              </Button>
            )}
          </div>
          {live.error && <p className="mt-2 text-sm text-bad">{live.error}</p>}
        </Card>
      )}

      <Card className="mb-4">
        <p className="text-xs font-medium uppercase tracking-wide text-faint mb-3">
          Pipeline — all campaigns
        </p>
        <Funnel
          segments={[
            { label: "found", value: stages?.found ?? 0, tone: "muted" },
            { label: "qualified", value: stages?.qualified ?? 0 },
            { label: "shortlisted", value: stages?.shortlisted ?? 0, tone: "good" },
          ]}
        />
        <p className="text-xs text-faint mt-2.5">
          Found leads below the fit bar are never shown. For trends and per-campaign breakdowns,
          download the CSV and ask the Analytics desk.
        </p>
      </Card>

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-faint mb-2.5">
            Recently shortlisted
          </p>
          {loading ? (
            <Spinner />
          ) : shortlisted.length === 0 ? (
            <p className="text-sm text-sub">
              Nothing shortlisted yet — run discovery or open the Leads tab to start curating.
            </p>
          ) : (
            <div className="space-y-3">
              {shortlisted.map((lead) => (
                <Card key={lead.id}>
                  <div className="flex items-center gap-2 flex-wrap text-xs text-sub">
                    <Badge tone={STAGE_TONE[lead.stage]}>{lead.stage}</Badge>
                    <span className="font-medium text-ink">{lead.name}</span>
                    {lead.company && <span>· {lead.company}</span>}
                  </div>
                  {lead.fitReason && <p className="mt-2 text-sm text-sub">{lead.fitReason}</p>}
                  <div className="mt-3 flex items-center gap-2 flex-wrap">
                    {campaignName(lead.campaignId) && (
                      <Badge>{campaignName(lead.campaignId)}</Badge>
                    )}
                    <Button size="sm" className="ml-auto" onClick={() => onOpenLead(lead)}>
                      Open lead
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        <div className="w-full lg:w-72 shrink-0 space-y-4">
          <Card>
            <p className="text-xs font-medium uppercase tracking-wide text-faint mb-2">
              Campaigns
            </p>
            {summary && summary.campaigns.length > 0 ? (
              <div className="space-y-2.5 text-[13px]">
                {summary.campaigns.map((c) => (
                  <div key={c.id} className="flex items-center justify-between gap-3">
                    <span className="truncate text-ink">{c.name}</span>
                    <Badge tone={c.status === "active" ? "good" : "neutral"}>{c.status}</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[13px] text-sub">No campaigns yet.</p>
            )}
            <Button size="sm" variant="ghost" className="mt-2" onClick={onCampaignsTab}>
              Open campaigns
            </Button>
          </Card>
          {lastRun && (
            <Card>
              <p className="text-xs font-medium uppercase tracking-wide text-faint mb-2">
                Last run
              </p>
              <p className="text-[13px] text-ink">
                {lastRun.found} found · {lastRun.qualified} qualified · {lastRun.skippedKnown}{" "}
                already known
              </p>
              <p className="text-xs text-faint mt-1">
                {formatRelative(lastRun.startedAt)}
                {lastRun.status !== "done" && ` · ${lastRun.status}`}
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
