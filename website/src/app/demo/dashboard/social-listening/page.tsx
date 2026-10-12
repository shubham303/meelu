"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Download, Radar, Sparkles, Square } from "lucide-react";
import { PageEnter } from "@demo/components/animate";
import { Button, IconButton, PageHeader, Spinner, Tabs } from "@demo/components/ui";
import { GLOBAL } from "@demo/lib/current-site";
import { api, apiPaged, useApi, useCurrentSite, usePagedApi } from "@demo/lib/use-api";
import { useIsApp } from "@demo/lib/use-app-mode";
import type {
  SocialListeningConfig,
  SocialListeningQuery,
  SocialListeningPost,
  SocialListeningSummary,
  SocialListeningTarget,
} from "@demo/lib/types";
import { useAgentTasks } from "../agent-tasks";
import { postsQuery, type PlatformInfo } from "./lib";
import { OverviewTab } from "./overview-tab";
import { SetupTab } from "./setup-tab";
import { InboxTab } from "./inbox-tab";
import { BrandMentionsTab, CompetitorMentionsTab } from "./mentions-tab";
import { ReplyDrawer } from "./reply-drawer";

export interface LiveRun {
  stageDetail: string;
  progress: { judged: number; total: number } | null;
  gate: { pending: number; kept: number; filtered: number } | null;
  platformState: Record<string, { status: "fetching" | "done" | "error"; count?: number; error?: string }>;
  error: string | null;
}

const EMPTY_LIVE: LiveRun = {
  stageDetail: "",
  progress: null,
  gate: null,
  platformState: {},
  error: null,
};

type TabKey = "overview" | "setup" | "inbox" | "mentions" | "competitors";

export default function SocialListeningPage() {
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();
  const selected = useCurrentSite();
  const siteId = selected && selected !== GLOBAL ? selected : null;

  const [tab, setTab] = useState<TabKey>("overview");
  const [version, setVersion] = useState(0);
  const bump = useCallback(() => setVersion((v) => v + 1), []);

  const {
    data: config,
    loading: configLoading,
    refresh: refreshConfig,
  } = useApi<SocialListeningConfig>("/api/v1/social-listening/config");
  const { data: queries, refresh: refreshQueries } = useApi<SocialListeningQuery[]>(
    "/api/v1/social-listening/queries",
  );
  const { data: targets, refresh: refreshTargets } = useApi<SocialListeningTarget[]>(
    "/api/v1/social-listening/targets",
  );
  const { data: summary, refresh: refreshSummary } = useApi<SocialListeningSummary>(
    `/api/v1/social-listening/summary?v=${version}`,
  );
  const { data: bestPage } = usePagedApi<SocialListeningPost>(
    postsQuery({ kind: "topic", status: "needs_reply", sort: "best", page_size: 2, v: version }),
  );

  const [platformInfo, setPlatformInfo] = useState<PlatformInfo[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [live, setLive] = useState<LiveRun>(EMPTY_LIVE);
  const [drawerPost, setDrawerPost] = useState<SocialListeningPost | null>(null);
  const [downloading, setDownloading] = useState(false);
  const jobRef = useRef<string | null>(null);

  useEffect(() => {
    void bridge?.socialSignalsPlatforms?.().then((res) => {
      if (!("error" in res)) setPlatformInfo(res.platforms);
    });
  }, [bridge]);

  useEffect(() => {
    if (!bridge?.onSocialSignalsEvent) return;
    return bridge.onSocialSignalsEvent((m) => {
      if (m.jobId !== jobRef.current) return;
      const d = m.data as Record<string, unknown>;
      if (m.event === "stage") {
        const stage = String(d.stage);
        setLive((prev) => ({
          ...prev,
          stageDetail:
            stage === "expanding"
              ? `Turning "${String(d.query ?? "")}" into search terms…`
              : stage === "fetching"
                ? "Searching platforms…"
                : stage === "gating"
                  ? "Comparing posts to your queries…"
                  : stage === "classifying"
                    ? `Reviewing ${d.total ?? ""} matched posts…`
                    : prev.stageDetail,
          progress:
            stage === "classifying" ? { judged: 0, total: Number(d.total ?? 0) } : null,
          gate: stage === "gating" ? prev.gate : null,
        }));
      } else if (m.event === "gate") {
        setLive((prev) => ({
          ...prev,
          gate: {
            pending: Number(d.pending ?? 0),
            kept: (prev.gate?.kept ?? 0) + Number(d.kept ?? 0),
            filtered: (prev.gate?.filtered ?? 0) + Number(d.filtered ?? 0),
          },
        }));
      } else if (m.event === "classified") {
        setLive((prev) => ({
          ...prev,
          progress: { judged: Number(d.judged ?? 0), total: Number(d.total ?? 0) },
        }));
      } else if (m.event === "platform") {
        const platform = String(d.platform);
        setLive((prev) => ({
          ...prev,
          platformState: {
            ...prev.platformState,
            [platform]: {
              status: d.status as "fetching" | "done" | "error",
              count: d.count as number | undefined,
              error: d.error as string | undefined,
            },
          },
        }));
      } else if (m.event === "done" || m.event === "stopped") {
        jobRef.current = null;
        setJobId(null);
        setLive((prev) => ({ ...prev, stageDetail: "", progress: null, gate: null }));
        bump();
        void refreshSummary();
      } else if (m.event === "error") {
        jobRef.current = null;
        setJobId(null);
        setLive((prev) => ({
          ...prev,
          stageDetail: "",
          progress: null,
          gate: null,
          error: String(d.message ?? "The run failed."),
        }));
      }
    });
  }, [bridge, bump, refreshSummary]);

  const running = jobId !== null;

  const runNow = async () => {
    if (!bridge?.socialSignalsSearch || running || !config || !siteId) return;
    const available = new Set(platformInfo.filter((p) => p.available).map((p) => p.id));
    setLive(EMPTY_LIVE);
    const res = await bridge.socialSignalsSearch({
      siteId,
      platforms: config.platforms.filter((p) => available.has(p)),
    });
    if (res.error) {
      setLive({ ...EMPTY_LIVE, error: res.error });
      return;
    }
    jobRef.current = res.jobId ?? null;
    setJobId(res.jobId ?? null);
  };

  const stop = () => {
    if (jobId) void bridge?.socialSignalsStop?.(jobId);
  };

  const skip = async (post: SocialListeningPost) => {
    await api(`/api/v1/social-listening/posts/${post.id}`, {
      method: "PATCH",
      body: { status: "skipped" },
    });
    bump();
  };

  const download = async () => {
    setDownloading(true);
    try {
      const rows: SocialListeningPost[] = [];
      let page = 1;
      for (;;) {
        const res = await apiPaged<SocialListeningPost>(
          postsQuery({ sort: "newest", page, page_size: 200 }),
        );
        rows.push(...res.data);
        if (!res.pagination.has_next || page >= 25) break;
        page += 1;
      }
      const cols = [
        "url",
        "platform",
        "kind",
        "status",
        "title",
        "text",
        "authorHandle",
        "postedAt",
        "intent",
        "sentiment",
        "classes",
        "matchedTargets",
        "similarity",
        "relevance",
        "compositeScore",
        "keepReason",
        "suggestedAngle",
      ] as const;
      const cell = (v: unknown) => {
        const s = Array.isArray(v) ? v.join("|") : v == null ? "" : String(v);
        return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
      };
      const csv = [
        cols.join(","),
        ...rows.map((r) => cols.map((c) => cell(r[c])).join(",")),
      ].join("\n");
      const blob = new Blob([csv], { type: "text/csv" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "social-listening-posts.csv";
      a.click();
      URL.revokeObjectURL(a.href);
    } finally {
      setDownloading(false);
    }
  };

  const ask = () =>
    launchTask({
      title: "Ask — Social Listening",
      endpoint: "/api/agent/ask-social-listening",
      emptyHint:
        "Ask which posts to reply to first, what a switch opportunity is worth, or for a suggested angle on anything in the inbox.",
      draft: {},
      onWrote: () => {
        bump();
        void refreshSummary();
      },
    });

  const platformLabel = useCallback(
    (id: string) => platformInfo.find((p) => p.id === id)?.label ?? id,
    [platformInfo],
  );

  const platforms = config?.platforms ?? [];

  return (
    <PageEnter>
      <PageHeader
        title="Social Listening"
        description="Meelu watches the platforms for conversations your site belongs in — people asking for what you sell, and people naming your brand — and lines them up with a suggested angle for each reply."
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
                disabled={!isApp || !config}
                title={isApp ? undefined : "Listening runs on your device, in the Meelu app."}
              >
                <Radar size={14} /> Run listening now
              </Button>
            )}
            {isApp && (
              <IconButton
                title="Ask Meelu"
                aria-label="Ask Meelu"
                className="border border-accent/30 bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent"
                onClick={ask}
              >
                <Sparkles size={16} />
              </IconButton>
            )}
          </div>
        }
      />

      <Tabs
        tabs={[
          { key: "overview", label: "Overview" },
          { key: "setup", label: "Queries & setup" },
          { key: "inbox", label: "Post inbox", count: summary?.needsReply },
          { key: "mentions", label: "Brand mentions", count: summary?.brandMentions },
          { key: "competitors", label: "Competitor mentions", count: summary?.competitorMentions },
        ]}
        active={tab}
        onChange={(k) => setTab(k as TabKey)}
      />

      {configLoading ? (
        <Spinner />
      ) : (
        <>
          {tab === "overview" && (
            <OverviewTab
              summary={summary}
              config={config}
              queries={queries ?? []}
              best={bestPage?.data ?? []}
              live={live}
              running={running}
              onStop={stop}
              platformLabel={platformLabel}
              onSkip={(p) => void skip(p)}
              onDraft={setDrawerPost}
              onSetupTab={() => setTab("setup")}
            />
          )}
          {tab === "setup" && (
            <SetupTab
              config={config}
              queries={queries ?? []}
              targets={targets ?? []}
              platformInfo={platformInfo}
              refreshConfig={refreshConfig}
              refreshQueries={refreshQueries}
              refreshTargets={refreshTargets}
            />
          )}
          {tab === "inbox" && (
            <InboxTab
              summary={summary}
              queries={queries ?? []}
              platforms={platforms}
              platformLabel={platformLabel}
              onSkip={(p) => void skip(p)}
              onDraft={setDrawerPost}
              version={version}
            />
          )}
          {tab === "mentions" && (
            <BrandMentionsTab
              summary={summary}
              platformLabel={platformLabel}
              onSkip={(p) => void skip(p)}
              onDraft={setDrawerPost}
              version={version}
            />
          )}
          {tab === "competitors" && (
            <CompetitorMentionsTab
              summary={summary}
              targets={targets ?? []}
              platformLabel={platformLabel}
              onSkip={(p) => void skip(p)}
              onDraft={setDrawerPost}
              version={version}
            />
          )}
        </>
      )}

      <ReplyDrawer
        post={drawerPost}
        siteId={siteId}
        platformLabel={platformLabel}
        onClose={() => setDrawerPost(null)}
        onSaved={() => {
          bump();
          void refreshSummary();
        }}
      />
    </PageEnter>
  );
}
