"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Download, Send, Sparkles, Square } from "lucide-react";
import { PageEnter } from "@/components/animate";
import { Button, PageHeader, Spinner, Tabs } from "@/components/ui";
import { apiPaged, useApi } from "@/lib/use-api";
import { useIsApp } from "@/lib/use-app-mode";
import type { Lead, LeadCampaign, LeadSummary } from "@/lib/types";
import { useAgentTasks } from "../agent-tasks";
import { defaultSources, leadsQuery, type SourceInfo } from "./lib";
import { OverviewTab } from "./overview-tab";
import { CampaignsTab } from "./campaigns-tab";
import { LeadsTab } from "./leads-tab";
import { LeadDrawer } from "./lead-drawer";

export interface LiveRun {
  stageDetail: string;
  sourceState: Record<string, { status: "fetching" | "done" | "error"; count?: number; error?: string }>;
  error: string | null;
}

const EMPTY_LIVE: LiveRun = { stageDetail: "", sourceState: {}, error: null };

type TabKey = "overview" | "campaigns" | "leads";

export default function LeadManagementPage() {
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();

  const [tab, setTab] = useState<TabKey>("overview");
  const [version, setVersion] = useState(0);
  const bump = useCallback(() => setVersion((v) => v + 1), []);

  const { data: campaigns, refresh: refreshCampaigns } = useApi<LeadCampaign[]>(
    "/api/v1/lead-management/campaigns",
  );
  const { data: summary, refresh: refreshSummary } = useApi<LeadSummary>(
    `/api/v1/lead-management/summary?v=${version}`,
  );

  const [sources, setSources] = useState<SourceInfo[]>(defaultSources());
  const [jobId, setJobId] = useState<string | null>(null);
  const [live, setLive] = useState<LiveRun>(EMPTY_LIVE);
  const [drawerLead, setDrawerLead] = useState<Lead | null>(null);
  const [downloading, setDownloading] = useState(false);
  const jobRef = useRef<string | null>(null);

  useEffect(() => {
    void bridge?.prospectSources?.().then((res) => {
      if (!("error" in res)) setSources(res.sources);
    });
  }, [bridge]);

  useEffect(() => {
    if (!bridge?.onLeadsEvent) return;
    return bridge.onLeadsEvent((m) => {
      if (m.jobId !== jobRef.current) return;
      const d = m.data as Record<string, unknown>;
      if (m.event === "stage") {
        const stage = String(d.stage);
        setLive((prev) => ({
          ...prev,
          stageDetail:
            stage === "expanding"
              ? "Expanding the brief into searches…"
              : stage === "fetching"
                ? "Searching sources…"
                : stage === "qualifying"
                  ? `Qualifying ${d.total ?? ""} people…`
                  : stage === "enriching"
                    ? "Hunting emails on their pages…"
                    : prev.stageDetail,
        }));
      } else if (m.event === "source") {
        const source = String(d.source);
        setLive((prev) => ({
          ...prev,
          sourceState: {
            ...prev.sourceState,
            [source]: {
              status: d.status as "fetching" | "done" | "error",
              count: d.count as number | undefined,
              error: d.error as string | undefined,
            },
          },
        }));
      } else if (m.event === "done" || m.event === "stopped") {
        jobRef.current = null;
        setJobId(null);
        setLive((prev) => ({ ...prev, stageDetail: "" }));
        bump();
        void refreshSummary();
      } else if (m.event === "error") {
        jobRef.current = null;
        setJobId(null);
        setLive((prev) => ({
          ...prev,
          stageDetail: "",
          error: String(d.message ?? "The run failed."),
        }));
      }
    });
  }, [bridge, bump, refreshSummary]);

  useEffect(() => {
    if (bridge?.onLeadsEvent || summary?.lastRun?.status !== "running") return;
    const t = setInterval(() => void refreshSummary(), 8000);
    return () => clearInterval(t);
  }, [bridge, summary?.lastRun?.status, refreshSummary]);

  const running = jobId !== null;

  const runNow = async (campaignId?: string) => {
    if (!bridge?.leadsRun || running) return;
    setLive(EMPTY_LIVE);
    const res = await bridge.leadsRun(campaignId ? { campaignId } : {});
    if (res.error) {
      setLive({ ...EMPTY_LIVE, error: res.error });
      return;
    }
    jobRef.current = res.jobId ?? null;
    setJobId(res.jobId ?? null);
  };

  const stop = () => {
    if (jobId) void bridge?.leadsStop?.(jobId);
  };

  const download = async () => {
    setDownloading(true);
    try {
      const rows: Lead[] = [];
      let page = 1;
      for (;;) {
        const res = await apiPaged<Lead>(
          leadsQuery({ sort: "newest", page, page_size: 200 }),
        );
        rows.push(...res.data);
        if (!res.pagination.has_next || page >= 25) break;
        page += 1;
      }
      const cols = [
        "name",
        "company",
        "role",
        "email",
        "emailVerified",
        "website",
        "source",
        "sourceUrl",
        "stage",
        "fitScore",
        "fitReason",
        "campaignId",
        "note",
        "createdAt",
      ] as const;
      const cell = (v: unknown) => {
        const s = v == null ? "" : String(v);
        return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
      };
      const csv = [
        cols.join(","),
        ...rows.map((r) => cols.map((c) => cell(r[c])).join(",")),
      ].join("\n");
      const blob = new Blob([csv], { type: "text/csv" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "leads.csv";
      a.click();
      URL.revokeObjectURL(a.href);
    } finally {
      setDownloading(false);
    }
  };

  const ask = () =>
    launchTask({
      title: "Ask — Lead Management",
      endpoint: "/api/agent/ask-leads",
      emptyHint:
        "Ask which qualified leads look strongest, what the last run turned up, or who to shortlist first.",
      draft: {},
      onWrote: () => {
        bump();
        void refreshSummary();
      },
    });

  const campaignName = useCallback(
    (id: string | null) => (campaigns ?? []).find((c) => c.id === id)?.name ?? null,
    [campaigns],
  );

  const onSaved = useCallback(() => {
    bump();
    void refreshSummary();
  }, [bump, refreshSummary]);

  return (
    <PageEnter>
      <PageHeader
        title="Lead Management"
        description="Meelu finds and qualifies people worth talking to — bloggers, partners, curators — and keeps the list honest. You decide who makes the shortlist and how to reach out."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => void download()} disabled={downloading}>
              <Download size={14} /> {downloading ? "Building…" : "Download data"}
            </Button>
            {running ? (
              <Button variant="outline" onClick={stop}>
                <Square size={14} /> Stop
              </Button>
            ) : (
              <Button
                variant="outline"
                onClick={() => void runNow()}
                disabled={!isApp}
                title={isApp ? undefined : "Discovery runs on your device, in the Meelu app."}
              >
                <Send size={14} /> Find leads now
              </Button>
            )}
            {isApp && (
              <Button onClick={ask}>
                <Sparkles size={14} /> Ask Meelu
              </Button>
            )}
          </div>
        }
      />

      <Tabs
        tabs={[
          { key: "overview", label: "Overview" },
          { key: "campaigns", label: "Campaigns", count: campaigns?.length },
          { key: "leads", label: "Leads", count: summary?.stages.qualified },
        ]}
        active={tab}
        onChange={(k) => setTab(k as TabKey)}
      />

      {!summary && !campaigns ? (
        <Spinner />
      ) : (
        <>
          {tab === "overview" && (
            <OverviewTab
              summary={summary}
              live={live}
              running={running}
              onStop={stop}
              campaignName={campaignName}
              onOpenLead={setDrawerLead}
              onCampaignsTab={() => setTab("campaigns")}
              version={version}
            />
          )}
          {tab === "campaigns" && (
            <CampaignsTab
              campaigns={campaigns ?? []}
              summary={summary}
              sources={sources}
              refresh={refreshCampaigns}
              onRun={(id) => void runNow(id)}
              running={running}
              isApp={isApp}
            />
          )}
          {tab === "leads" && (
            <LeadsTab
              summary={summary}
              campaigns={campaigns ?? []}
              campaignName={campaignName}
              onOpen={setDrawerLead}
              version={version}
            />
          )}
        </>
      )}

      <LeadDrawer
        lead={drawerLead}
        campaignName={campaignName}
        onClose={() => setDrawerLead(null)}
        onSaved={onSaved}
      />
    </PageEnter>
  );
}
