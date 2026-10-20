"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Download, Inbox, RotateCw, Sparkles, Square } from "lucide-react";
import { PageEnter } from "@demo/components/animate";
import { Button, IconButton, PageHeader, Spinner } from "@demo/components/ui";
import { GLOBAL } from "@demo/lib/current-site";
import { api, useApi, useCurrentSite, usePagedApi } from "@demo/lib/use-api";
import { useIsApp } from "@demo/lib/use-app-mode";
import { cn } from "@demo/lib/utils";
import type {
  SocialListeningConfig,
  SocialListeningEstimate,
  SocialListeningPost,
  SocialListeningQuery,
  SocialListeningReviewStatus,
  SocialListeningSummary,
} from "@demo/lib/types";
import { useAgentTasks, type SocialSignalsSnapshot } from "../agent-tasks";
import {
  downloadPostsCsv,
  EMPTY_LIVE,
  hoursAgo,
  liveAfter,
  postsPath,
  TAB_STATUSES,
  type LiveRun,
  type PlatformInfo,
  type TabKey,
} from "./lib";
import { ListeningCard } from "./listening-card";
import { PostCard } from "./post-card";
import { ReplyPanel } from "./reply-panel";
import { RunProgress } from "./run-progress";
import { RunResult, type RunOutcome } from "./run-result";

const PAGE_SIZE = 25;

const EMPTY_TAB: Record<TabKey, { title: string; hint: string }> = {
  to_reply: {
    title: "Nothing to reply to right now",
    hint: "Press Run now to look again. Posts Meelu has already shown you never come back.",
  },
  drafted: {
    title: "No drafts waiting",
    hint: "When you copy a reply, the post waits here until you mark it replied.",
  },
  done: {
    title: "Nothing done yet",
    hint: "Posts you reply to, skip or mark not relevant end up here.",
  },
};

export default function SocialListeningPage() {
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();
  const selected = useCurrentSite();
  const siteId = selected && selected !== GLOBAL ? selected : null;

  const [tab, setTab] = useState<TabKey>("to_reply");
  const [pageSize, setPageSize] = useState(PAGE_SIZE);
  const [editingLines, setEditingLines] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [drawerPost, setDrawerPost] = useState<SocialListeningPost | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [platformInfo, setPlatformInfo] = useState<PlatformInfo[] | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [live, setLive] = useState<LiveRun>(EMPTY_LIVE);
  const [runStartedAt, setRunStartedAt] = useState<number | null>(null);
  const [stopping, setStopping] = useState(false);
  const [outcome, setOutcome] = useState<RunOutcome | null>(null);
  const jobRef = useRef<string | null>(null);
  const liveRef = useRef<LiveRun>(EMPTY_LIVE);

  useEffect(() => {
    liveRef.current = live;
  }, [live]);

  const { data: config, loading: configLoading, refresh: refreshConfig } = useApi<SocialListeningConfig>(
    "/api/v1/social-listening/config",
  );
  const { data: queries, loading: queriesLoading, refresh: refreshQueries } = useApi<SocialListeningQuery[]>(
    "/api/v1/social-listening/queries",
  );
  const { data: summary, refresh: refreshSummary } = useApi<SocialListeningSummary>(
    "/api/v1/social-listening/summary",
  );
  const { data: estimate, refresh: refreshEstimate } = useApi<SocialListeningEstimate>(
    "/api/v1/social-listening/estimate",
  );
  const {
    data: postsPage,
    loading: postsLoading,
    refresh: refreshPosts,
  } = usePagedApi<SocialListeningPost>(
    postsPath({
      status: TAB_STATUSES[tab].join(","),
      page: 1,
      page_size: pageSize,
    }),
  );

  const refreshAll = useCallback(async () => {
    await Promise.all([refreshPosts(), refreshSummary(), refreshQueries(), refreshEstimate()]);
  }, [refreshPosts, refreshSummary, refreshQueries, refreshEstimate]);

  useEffect(() => {
    void bridge?.socialSignalsPlatforms?.().then((res) => {
      if (!("error" in res)) setPlatformInfo(res.platforms);
    });
  }, [bridge]);

  const resume = useCallback(
    (snapshot: SocialSignalsSnapshot | { error: string } | undefined) => {
      if (!snapshot || "error" in snapshot || !snapshot.jobId) return;
      jobRef.current = snapshot.jobId;
      setJobId(snapshot.jobId);
      setStopping(snapshot.stopping);
      setRunStartedAt(snapshot.startedAt ?? Date.now());
      setLive(
        snapshot.progress.reduce<LiveRun>((acc, p) => liveAfter(acc, p.event, p.data), {
          ...EMPTY_LIVE,
          step: "terms",
        }),
      );
    },
    [],
  );

  useEffect(() => {
    if (!siteId || !bridge?.socialSignalsActive) return;
    let cancelled = false;
    void bridge.socialSignalsActive(siteId).then((snapshot) => {
      if (!cancelled) resume(snapshot);
    });
    return () => {
      cancelled = true;
    };
  }, [bridge, siteId, resume]);

  useEffect(() => {
    if (!bridge?.onSocialSignalsEvent) return;
    return bridge.onSocialSignalsEvent((m) => {
      if (m.jobId !== jobRef.current) return;
      const d = m.data;
      if (m.event !== "done" && m.event !== "stopped" && m.event !== "error") {
        setLive((prev) => liveAfter(prev, m.event, d));
        if (m.event === "judged") {
          void refreshPosts();
          void refreshSummary();
        }
        return;
      }
      const n = (v: unknown) => Number(v ?? 0) || 0;
      if (m.event !== "error") {
        const prev = liveRef.current;
        setOutcome({
          stopped: m.event === "stopped",
          fetched: m.event === "done" ? n(d.fetched) : prev.fetched,
          inserted: m.event === "done" ? n(d.inserted) : prev.inserted,
          kept: m.event === "done" ? n(d.kept) : (prev.judged?.kept ?? 0),
          platforms:
            m.event === "done"
              ? ((d.platforms ?? {}) as RunOutcome["platforms"])
              : Object.fromEntries(Object.entries(prev.platforms).map(([id, p]) => [id, { error: p.error }])),
        });
      }
      jobRef.current = null;
      setJobId(null);
      setStopping(false);
      setRunStartedAt(null);
      setLive(m.event === "error" ? { ...EMPTY_LIVE, error: String(d.message ?? "The run failed.") } : EMPTY_LIVE);
      void refreshAll();
    });
  }, [bridge, refreshAll, refreshPosts, refreshSummary]);

  const running = jobId !== null;
  const lines = queries ?? [];
  const enabledLines = lines.filter((q) => q.enabled).length;
  const availableIds = new Set((platformInfo ?? []).filter((p) => p.available).map((p) => p.id));
  const runPlatforms = (config?.platforms ?? []).filter((p) => availableIds.has(p));
  const firstVisit = !queriesLoading && lines.length === 0;
  const neverRun = !summary?.lastRun;
  const runBlocker = !isApp
    ? "Listening runs on your device, in the Meelu app."
    : enabledLines === 0
      ? "Add a line to listen for first."
      : runPlatforms.length === 0
        ? "Turn on at least one platform."
        : undefined;

  const platformLabel = useCallback(
    (id: string) => platformInfo?.find((p) => p.id === id)?.label ?? id,
    [platformInfo],
  );
  const lineOf = (id: string | null) => (id ? (lines.find((q) => q.id === id)?.text ?? null) : null);

  const runNow = async () => {
    if (!bridge?.socialSignalsSearch || running || !siteId || runBlocker) return;
    setLive({ ...EMPTY_LIVE, step: "terms" });
    setOutcome(null);
    setActionError(null);
    setTab("to_reply");
    const res = await bridge.socialSignalsSearch({ siteId, platforms: runPlatforms });
    if (res.jobId && res.error) {
      resume(await bridge.socialSignalsActive?.(siteId));
      return;
    }
    if (res.error || !res.jobId) {
      setLive({ ...EMPTY_LIVE, error: res.error ?? "The run did not start." });
      return;
    }
    jobRef.current = res.jobId;
    setJobId(res.jobId);
    setStopping(false);
    setRunStartedAt(Date.now());
  };

  const stop = () => {
    if (!jobId || stopping) return;
    setStopping(true);
    void bridge?.socialSignalsStop?.(jobId).then((res) => {
      if (res?.stopping === false) {
        jobRef.current = null;
        setJobId(null);
        setStopping(false);
        setRunStartedAt(null);
        setLive(EMPTY_LIVE);
        void refreshAll();
      }
    });
  };

  const setStatus = async (post: SocialListeningPost, status: SocialListeningReviewStatus) => {
    setBusyId(post.id);
    setActionError(null);
    try {
      await api(`/api/v1/social-listening/posts/${post.id}`, { method: "PATCH", body: { status } });
      await Promise.all([refreshPosts(), refreshSummary()]);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "The change did not save.");
    } finally {
      setBusyId(null);
    }
  };

  const download = async () => {
    setDownloading(true);
    try {
      await downloadPostsCsv(lines);
    } finally {
      setDownloading(false);
    }
  };

  const ask = () =>
    launchTask({
      title: "Ask — Social Listening",
      endpoint: "/api/agent/ask-social-listening",
      emptyHint: "Ask which posts to reply to first, why a line keeps nothing, or for an angle on any post.",
      draft: {},
      onWrote: () => void refreshAll(),
    });

  const counts: Record<TabKey, number> = {
    to_reply: summary?.toReply ?? 0,
    drafted: summary?.drafted ?? 0,
    done: summary?.done ?? 0,
  };
  const lastRun = summary?.lastRun ?? null;
  const runLine = running
    ? "Running now"
    : lastRun
      ? `Last run ${hoursAgo(lastRun.startedAt) === "just now" ? "just now" : `${hoursAgo(lastRun.startedAt)} ago`} · ${lastRun.fetchedCount} found → ${lastRun.matchedCount} close in meaning → ${lastRun.keptCount} kept${lastRun.status !== "done" ? ` · ${lastRun.status}` : ""}`
      : "";
  const posts = postsPage?.data ?? [];
  const hasMore = postsPage?.pagination.has_next ?? false;

  return (
    <PageEnter>
      <PageHeader
        title="Social Listening"
        description="Posts where a reply from you belongs. Meelu finds them and suggests an angle. You decide which to answer."
        actions={
          <div className="relative flex items-center gap-2">
            <Button variant="ghost" onClick={() => void download()} disabled={downloading || lines.length === 0}>
              <Download size={14} /> {downloading ? "Building CSV…" : "Download CSV"}
            </Button>
            {running ? (
              <Button variant="outline" onClick={stop} disabled={stopping}>
                <Square size={13} /> {stopping ? "Stopping…" : "Stop"}
              </Button>
            ) : (
              <span title={runBlocker}>
                <Button
                  variant={neverRun ? "primary" : "outline"}
                  onClick={() => void runNow()}
                  disabled={Boolean(runBlocker) || !config}
                >
                  <RotateCw size={14} /> Run now
                </Button>
              </span>
            )}
            {isApp && (
              <IconButton
                title="Ask Meelu"
                aria-label="Ask Meelu"
                className="h-9 w-9 border border-accent/30 bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent"
                onClick={ask}
              >
                <Sparkles size={16} />
              </IconButton>
            )}
          </div>
        }
      />

      {configLoading || queriesLoading ? (
        <Spinner />
      ) : (
        <div className="space-y-5">
          <ListeningCard
            queries={lines}
            config={config}
            platformInfo={platformInfo}
            estimate={estimate}
            expanded={editingLines}
            onExpand={() => setEditingLines(true)}
            onCollapse={() => setEditingLines(false)}
            refreshQueries={async () => {
              await Promise.all([refreshQueries(), refreshEstimate()]);
            }}
            refreshConfig={refreshConfig}
          />

          {running && <RunProgress live={live} platformLabel={platformLabel} />}
          {!running && live.error && <p className="text-sm text-bad">{live.error}</p>}
          {!running && outcome && (
            <RunResult outcome={outcome} platformLabel={platformLabel} onDismiss={() => setOutcome(null)} />
          )}

          {firstVisit ? (
            <div className="flex flex-col items-center gap-2.5 rounded-2xl border border-dashed border-edge2 px-6 py-12 text-center">
              <Inbox size={26} className="text-sub" />
              <p className="text-[15px] font-semibold text-ink">Nothing to reply to yet</p>
              <p className="max-w-md text-[13.5px] text-sub">
                When your lines look right, press Run now. The first run looks back 7 days, so it can take a few
                minutes.
              </p>
            </div>
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div role="tablist" className="inline-flex gap-0.5 rounded-lg border border-edge2 bg-panel2 p-[3px]">
                  {(["to_reply", "drafted", "done"] as TabKey[]).map((key) => (
                    <button
                      key={key}
                      role="tab"
                      aria-selected={tab === key}
                      onClick={() => {
                        setTab(key);
                        setPageSize(PAGE_SIZE);
                      }}
                      className={cn(
                        "cursor-pointer rounded-md px-3.5 py-1 text-[13px] transition-colors",
                        tab === key
                          ? "bg-panel font-medium text-ink shadow-[0_1px_2px_#1f2d3d14]"
                          : "text-sub hover:text-ink",
                      )}
                    >
                      {key === "to_reply" ? "To reply" : key === "drafted" ? "Drafted" : "Done"}
                      <span className="ml-1.5 tabular-nums text-sub">{counts[key]}</span>
                    </button>
                  ))}
                </div>
                {runLine && <p className="text-[13px] tabular-nums text-sub">{runLine}</p>}
              </div>

              {actionError && <p className="text-sm text-bad">{actionError}</p>}

              {postsLoading && posts.length === 0 ? (
                <Spinner />
              ) : posts.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-edge2 px-6 py-10 text-center">
                  <p className="text-[15px] font-semibold text-ink">{EMPTY_TAB[tab].title}</p>
                  <p className="mx-auto mt-1 max-w-md text-[13.5px] text-sub">{EMPTY_TAB[tab].hint}</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {posts.map((p) => (
                    <PostCard
                      key={p.id}
                      post={p}
                      tab={tab}
                      line={lineOf(p.queryId)}
                      platformLabel={platformLabel}
                      fresh={runStartedAt !== null && new Date(p.updatedAt).getTime() >= runStartedAt}
                      busy={busyId === p.id}
                      onStatus={(post, status) => void setStatus(post, status)}
                      onDraft={setDrawerPost}
                    />
                  ))}
                  {hasMore && (
                    <div className="flex justify-center">
                      <Button variant="ghost" size="sm" onClick={() => setPageSize((n) => n + PAGE_SIZE)}>
                        Show {Math.min(PAGE_SIZE, (postsPage?.pagination.total ?? 0) - posts.length)} more
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}

      <ReplyPanel
        post={drawerPost}
        siteId={siteId}
        platformLabel={platformLabel}
        onClose={() => setDrawerPost(null)}
        onSaved={() => {
          void refreshPosts();
          void refreshSummary();
        }}
      />
    </PageEnter>
  );
}
