"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Square } from "lucide-react";
import { PageEnter } from "@demo/components/animate";
import { Button, Card, Input, PageHeader, Select, Spinner, Textarea } from "@demo/components/ui";
import { GLOBAL } from "@demo/lib/current-site";
import { api, useApi, useCurrentSite, usePagedApi } from "@demo/lib/use-api";
import { useIsApp } from "@demo/lib/use-app-mode";
import { cn } from "@demo/lib/utils";
import type { Lead, LeadBrief, LeadReviewStatus, LeadSummary } from "@demo/lib/types";
import { useAgentTasks, type FindLeadsSnapshot } from "../agent-tasks";
import { BriefsPanel } from "./briefs-panel";
import { LeadCard, LeadRow } from "./lead-card";
import {
  EMPTY_LIVE,
  leadsPath,
  liveAfter,
  runStamp,
  sourceLabel,
  sourceTotals,
  TAB_LABEL,
  type LiveRun,
} from "./lib";
import { RunProgress } from "./run-progress";
import { RunError, RunResult, type RunOutcome } from "./run-messages";

const DEFAULT_TARGET = 20;
const MAX_TARGET = 100;
const TARGET_KEY = "meelu.findLeads.target";

const noSubscribe = () => () => {};

function readSavedTarget(): number {
  try {
    const saved = Number(localStorage.getItem(TARGET_KEY));
    return saved >= 1 && saved <= MAX_TARGET ? saved : DEFAULT_TARGET;
  } catch {
    return DEFAULT_TARGET;
  }
}
const PAGE_SIZE = 25;
const DOWNLOAD_URL = "https://meelu.tech/download";
const TABS: LeadReviewStatus[] = ["new", "contacted", "discarded"];

const EMPTY_TAB: Record<LeadReviewStatus, { title: string; hint: string }> = {
  new: {
    title: "No new leads right now",
    hint: "Press Find leads to look again. People Meelu has already shown you never come back.",
  },
  contacted: {
    title: "Nobody contacted yet",
    hint: "When you message someone, mark them contacted and they wait here.",
  },
  discarded: {
    title: "Nothing discarded",
    hint: "People you discard wait here for 30 days, then their details are deleted.",
  },
};

function AskIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true">
      <path d="M12 3v18M4.2 7.5l15.6 9M4.2 16.5l15.6-9" />
    </svg>
  );
}

function FirstVisit({
  isApp,
  onCreated,
  onSuggest,
}: {
  isApp: boolean;
  onCreated: (id: string) => Promise<void>;
  onSuggest: () => void;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    const clean = text.trim();
    if (!clean) {
      setError("Describe who you are looking for.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const brief = await api<LeadBrief>("/api/v1/find-leads/briefs", { method: "POST", body: { text: clean } });
      await onCreated(brief.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "The brief did not save.");
      setBusy(false);
    }
  };

  const steps = [
    {
      title: "1 · Meelu searches",
      body: "People who posted about the problem, LinkedIn profiles that match, and pages found on the web.",
    },
    {
      title: "2 · Meelu checks",
      body: "It reads each shortlisted person's recent activity and keeps only the ones worth your time.",
    },
    {
      title: "3 · You reach out",
      body: "Open their profile or public email, send your own message, then mark them contacted.",
    },
  ];

  return (
    <div className="space-y-4">
      <Card className="space-y-4 p-6 sm:p-8">
        <div className="max-w-2xl space-y-1.5">
          <h2 className="font-display text-2xl text-ink">Who would you like to talk to?</h2>
          <p className="text-[15px] leading-relaxed text-sub">
            Describe the people in a sentence. Each run, Meelu looks for them where you choose, drops the ones
            that aren&apos;t a fit and shows you who&apos;s left, with the reason and a link to reach them.
          </p>
        </div>
        <label className="block space-y-1.5">
          <span className="block text-[13px] font-semibold text-ink">Your first brief</span>
          <Textarea
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="e.g. Owners of small online stores who say their Google traffic dropped"
            className="min-h-0 bg-white text-[15px] leading-relaxed"
          />
        </label>
        {error && <p className="text-[13px] text-bad">{error}</p>}
        <div className="flex flex-wrap items-center justify-between gap-3">
          {isApp ? (
            <Button variant="outline" onClick={onSuggest}>
              <span className="text-accent">
                <AskIcon />
              </span>
              Suggest briefs from my website
            </Button>
          ) : (
            <span />
          )}
          <Button disabled={busy} onClick={() => void save()}>
            {busy ? "Saving…" : "Save and choose sources"}
          </Button>
        </div>
      </Card>
      <div className="grid gap-3 sm:grid-cols-3">
        {steps.map((s) => (
          <Card key={s.title} className="space-y-1.5 p-4">
            <h3 className="text-sm font-semibold text-ink">{s.title}</h3>
            <p className="text-[13.5px] leading-relaxed text-sub">{s.body}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}

export default function FindLeadsPage() {
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();
  const selected = useCurrentSite();
  const siteId = selected && selected !== GLOBAL ? selected : null;

  const [tab, setTab] = useState<LeadReviewStatus>("new");
  const [briefFilter, setBriefFilter] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE);
  const [openId, setOpenId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [live, setLive] = useState<LiveRun>(EMPTY_LIVE);
  const [runStartedAt, setRunStartedAt] = useState<number | null>(null);
  const [stopping, setStopping] = useState(false);
  const [outcome, setOutcome] = useState<RunOutcome | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const savedTarget = useSyncExternalStore(noSubscribe, readSavedTarget, () => DEFAULT_TARGET);
  const [chosenTarget, setChosenTarget] = useState<number | null>(null);
  const target = chosenTarget ?? savedTarget;

  const changeTarget = (value: string) => {
    const next = Math.min(Math.max(Math.floor(Number(value)) || 1, 1), MAX_TARGET);
    setChosenTarget(next);
    try {
      localStorage.setItem(TARGET_KEY, String(next));
    } catch {}
  };
  const jobRef = useRef<string | null>(null);
  const liveRef = useRef<LiveRun>(EMPTY_LIVE);

  useEffect(() => {
    liveRef.current = live;
  }, [live]);

  const { data: briefs, loading: briefsLoading, refresh: refreshBriefs } = useApi<LeadBrief[]>(
    "/api/v1/find-leads/briefs",
  );
  const { data: summary, refresh: refreshSummary } = useApi<LeadSummary>("/api/v1/find-leads/summary");
  const paged = tab !== "new";
  const {
    data: leadsPage,
    loading: leadsLoading,
    refresh: refreshLeads,
  } = usePagedApi<Lead>(
    leadsPath({
      status: tab,
      briefId: tab === "new" ? briefFilter : null,
      q: tab === "contacted" ? query.trim() : null,
      page: paged ? page : 1,
      page_size: paged ? PAGE_SIZE : pageSize,
    }),
  );

  const refreshAll = useCallback(async () => {
    await Promise.all([refreshLeads(), refreshSummary(), refreshBriefs()]);
  }, [refreshLeads, refreshSummary, refreshBriefs]);

  const resume = useCallback((snapshot: FindLeadsSnapshot | { error: string } | undefined) => {
    if (!snapshot || "error" in snapshot || !snapshot.jobId) return;
    jobRef.current = snapshot.jobId;
    setJobId(snapshot.jobId);
    setStopping(snapshot.stopping);
    setRunStartedAt(snapshot.startedAt ?? Date.now());
    setLive(
      snapshot.progress.reduce<LiveRun>((acc, p) => liveAfter(acc, p.event, p.data), { ...EMPTY_LIVE, step: "plan" }),
    );
  }, []);

  useEffect(() => {
    if (!siteId || !bridge?.findLeadsActive) return;
    let cancelled = false;
    void bridge.findLeadsActive(siteId).then((snapshot) => {
      if (!cancelled) resume(snapshot);
    });
    return () => {
      cancelled = true;
    };
  }, [bridge, siteId, resume]);

  useEffect(() => {
    if (!bridge?.onFindLeadsEvent) return;
    return bridge.onFindLeadsEvent((m) => {
      if (m.jobId !== jobRef.current) return;
      const d = m.data;
      if (m.event !== "done" && m.event !== "stopped" && m.event !== "error") {
        setLive((prev) => liveAfter(prev, m.event, d));
        if (m.event === "judged") {
          void refreshLeads();
          void refreshSummary();
        }
        return;
      }
      const n = (v: unknown) => Number(v ?? 0) || 0;
      const prev = liveRef.current;
      const failed = Object.entries(prev.sources)
        .filter(([, s]) => s.status === "error")
        .map(([key]) => sourceLabel(key));
      if (m.event === "error") {
        setRunError(String(d.message ?? "The run failed."));
      } else {
        const totals = sourceTotals(prev.sources);
        setOutcome({
          stopped: m.event === "stopped",
          found: m.event === "done" ? n(d.found) : totals.posts + totals.linkedin + totals.web,
          shortlisted: m.event === "done" ? n(d.shortlisted) : (prev.screened?.kept ?? 0),
          kept: m.event === "done" ? n(d.kept) : (prev.judged?.kept ?? 0),
          failed,
        });
      }
      jobRef.current = null;
      setJobId(null);
      setStopping(false);
      setRunStartedAt(null);
      setLive(EMPTY_LIVE);
      void refreshAll();
    });
  }, [bridge, refreshAll, refreshLeads, refreshSummary]);

  const running = jobId !== null;
  const briefList = briefs ?? [];
  const enabledBriefs = briefList.filter((b) => b.enabled).length;
  const firstVisit = !briefsLoading && briefList.length === 0 && openId === null;
  const runBlocker = enabledBriefs === 0 ? "Turn on a brief first." : undefined;

  const findLeads = async () => {
    if (!bridge?.findLeadsSearch || running || !siteId || runBlocker) return;
    setLive({ ...EMPTY_LIVE, step: "plan" });
    setOutcome(null);
    setRunError(null);
    setActionError(null);
    setTab("new");
    const res = await bridge.findLeadsSearch({ siteId, target });
    if (res.jobId && res.error) {
      resume(await bridge.findLeadsActive?.(siteId));
      return;
    }
    if (res.error || !res.jobId) {
      setLive(EMPTY_LIVE);
      setRunError(res.error ?? "The run did not start.");
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
    void bridge?.findLeadsStop?.(jobId).then((res) => {
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

  const setStatus = async (lead: Lead, status: LeadReviewStatus) => {
    setBusyId(lead.id);
    setActionError(null);
    try {
      await api(`/api/v1/find-leads/leads/${lead.id}`, { method: "PATCH", body: { status } });
      await Promise.all([refreshLeads(), refreshSummary()]);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "The change did not save.");
    } finally {
      setBusyId(null);
    }
  };

  const ask = () =>
    launchTask({
      title: "Ask — Find Leads",
      endpoint: "/api/agent/ask-find-leads",
      emptyHint: "Ask who to look for, why a brief keeps nobody, or what to say to someone on the list.",
      draft: {},
      onWrote: () => void refreshAll(),
    });

  const suggest = () =>
    launchTask({
      title: "Suggest briefs",
      endpoint: "/api/agent/find-leads-setup",
      emptyHint: "Meelu reads your website and proposes who to look for. Say go when the wording is right.",
      draft: {},
      autoStart: "Suggest who I should look for, based on my website.",
      onWrote: () => void refreshAll(),
    });

  const lastRun = summary?.lastRun ?? null;
  const lastTotals = lastRun ? sourceTotals(lastRun.sourceStats) : null;
  const runLine =
    lastRun && lastTotals ? (
      <>
        Last run {runStamp(lastRun)} · {lastRun.foundCount} {lastRun.foundCount === 1 ? "person" : "people"} found →{" "}
        {lastRun.shortlistedCount} shortlisted →{" "}
        <strong className="font-semibold text-ink">{lastRun.keptCount} worth contacting</strong>
        {lastRun.status !== "done" && lastRun.status !== "running" ? ` · ${lastRun.status}` : ""}
        {Object.keys(lastRun.sourceStats).some((k) => k.startsWith("posts:")) && ` · Post authors ${lastTotals.posts}`}
        {lastRun.sourceStats.linkedin && ` · LinkedIn ${lastTotals.linkedin}`}
        {lastRun.sourceStats.web && ` · Web ${lastTotals.web}`}
      </>
    ) : null;

  const counts: Record<LeadReviewStatus, number> = {
    new: summary?.new ?? 0,
    contacted: summary?.contacted ?? 0,
    discarded: summary?.discarded ?? 0,
  };
  const leads = leadsPage?.data ?? [];
  const pagination = leadsPage?.pagination;
  const briefText = (id: string | null) => (id ? (briefList.find((b) => b.id === id)?.text ?? null) : null);

  const switchTab = (key: LeadReviewStatus) => {
    setTab(key);
    setPage(1);
    setPageSize(PAGE_SIZE);
  };

  return (
    <PageEnter>
      <PageHeader
        title="Find Leads"
        description="People worth a personal message. You write it and send it yourself."
        actions={
          isApp ? (
            <div className="flex items-center gap-2">
              <button
                type="button"
                aria-label="Ask Meelu"
                title="Ask Meelu"
                onClick={ask}
                className="inline-flex h-10 w-10 cursor-pointer items-center justify-center rounded-lg border border-edge2 bg-panel text-accent hover:bg-panel2"
              >
                <AskIcon />
              </button>
              {running ? (
                <Button variant="danger" className="h-10" onClick={stop} disabled={stopping}>
                  <Square size={12} fill="currentColor" /> {stopping ? "Stopping…" : "Stop run"}
                </Button>
              ) : (
                <div className="flex items-center gap-2">
                  <label className="flex h-10 items-center gap-2 rounded-lg border border-edge2 bg-panel pl-3 pr-1 text-[13px] text-sub">
                    How many
                    <input
                      type="number"
                      min={1}
                      max={MAX_TARGET}
                      value={target}
                      onChange={(e) => changeTarget(e.target.value)}
                      aria-label="How many leads to find"
                      className="h-8 w-14 rounded-md border border-edge bg-bg px-2 text-[13px] tabular-nums text-ink focus:border-accent focus:outline-none"
                    />
                  </label>
                  <span title={runBlocker}>
                    <Button className="h-10" onClick={() => void findLeads()} disabled={Boolean(runBlocker)}>
                      Find leads
                    </Button>
                  </span>
                </div>
              )}
            </div>
          ) : (
            <a
              href={DOWNLOAD_URL}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-10 items-center rounded-lg bg-accent px-4 text-sm font-semibold text-white hover:bg-accent-hi"
            >
              Open in the Meelu app
            </a>
          )
        }
      />

      {briefsLoading && !briefs ? (
        <Spinner />
      ) : (
        <div className="space-y-5">
          {!isApp && (
            <div
              role="note"
              className="rounded-[14px] border border-edge bg-panel px-4 py-3 text-[13.5px] leading-relaxed text-sub"
            >
              <strong className="text-ink">Finding leads happens in the app.</strong> Here you can edit briefs, open
              profiles and mark people contacted or discarded.
            </div>
          )}

          {firstVisit ? (
            <FirstVisit
              isApp={isApp}
              onSuggest={suggest}
              onCreated={async (id) => {
                await refreshBriefs();
                setOpenId(id);
              }}
            />
          ) : (
            <>
              <BriefsPanel
                briefs={briefList}
                openId={openId}
                setOpenId={setOpenId}
                refresh={refreshBriefs}
                runLine={runLine}
              />

              {running && <RunProgress live={live} />}
              {!running && runError && <RunError message={runError} onDismiss={() => setRunError(null)} />}
              {!running && outcome && (
                <RunResult
                  outcome={outcome}
                  onEditBriefs={() => setOpenId(briefList[0]?.id ?? null)}
                  onDismiss={() => setOutcome(null)}
                />
              )}

              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-edge">
                <div role="tablist" className="flex gap-1">
                  {TABS.map((key) => (
                    <button
                      key={key}
                      type="button"
                      role="tab"
                      aria-selected={tab === key}
                      onClick={() => switchTab(key)}
                      className={cn(
                        "-mb-px min-h-11 cursor-pointer border-b-2 px-3.5 text-sm transition-colors",
                        tab === key ? "border-accent font-semibold text-ink" : "border-transparent text-sub hover:text-ink",
                      )}
                    >
                      {TAB_LABEL[key]} <span className="font-medium tabular-nums text-sub">{counts[key]}</span>
                    </button>
                  ))}
                </div>
                {tab === "new" && briefList.length > 1 && (
                  <label className="flex items-center gap-2 pb-1.5 text-[13px] text-sub">
                    Brief
                    <Select
                      className="w-56 py-1.5 text-[13px]"
                      value={briefFilter}
                      onChange={(e) => {
                        setBriefFilter(e.target.value);
                        setPageSize(PAGE_SIZE);
                      }}
                    >
                      <option value="">All briefs</option>
                      {briefList.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.text.length > 60 ? `${b.text.slice(0, 60)}…` : b.text}
                        </option>
                      ))}
                    </Select>
                  </label>
                )}
                {tab === "contacted" && (
                  <label className="flex pb-1.5">
                    <span className="sr-only">Search contacted</span>
                    <Input
                      type="search"
                      placeholder="Search by name"
                      className="w-52 py-1.5 text-[13px]"
                      value={query}
                      onChange={(e) => {
                        setQuery(e.target.value);
                        setPage(1);
                      }}
                    />
                  </label>
                )}
              </div>

              {tab === "discarded" && (
                <p className="text-[13.5px] text-sub">
                  Discarded people never come back in a new run. Their details are deleted 30 days after you discard
                  them.
                </p>
              )}

              {actionError && <p className="text-sm text-bad">{actionError}</p>}

              {leadsLoading && leads.length === 0 ? (
                <Spinner />
              ) : leads.length === 0 ? (
                <Card className="px-6 py-10 text-center">
                  <p className="text-base font-semibold text-ink">{EMPTY_TAB[tab].title}</p>
                  <p className="mx-auto mt-1 max-w-md text-sm text-sub">{EMPTY_TAB[tab].hint}</p>
                </Card>
              ) : tab === "new" ? (
                <div className="space-y-3">
                  {leads.map((lead) => (
                    <LeadCard
                      key={lead.id}
                      lead={lead}
                      briefText={briefText(lead.briefId)}
                      fresh={runStartedAt !== null && new Date(lead.updatedAt).getTime() >= runStartedAt}
                      busy={busyId === lead.id}
                      onStatus={(l, s) => void setStatus(l, s)}
                    />
                  ))}
                  {pagination?.has_next && (
                    <div className="flex justify-center">
                      <Button variant="ghost" size="sm" onClick={() => setPageSize((n) => n + PAGE_SIZE)}>
                        Show {Math.min(PAGE_SIZE, pagination.total - leads.length)} more
                      </Button>
                    </div>
                  )}
                </div>
              ) : (
                <Card className="overflow-hidden p-0">
                  {leads.map((lead) => (
                    <LeadRow
                      key={lead.id}
                      lead={lead}
                      busy={busyId === lead.id}
                      onStatus={(l, s) => void setStatus(l, s)}
                    />
                  ))}
                  {pagination && pagination.total_pages > 1 && (
                    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-edge px-[18px] py-3 text-[13px] text-sub">
                      <span className="tabular-nums">
                        {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, pagination.total)} of{" "}
                        {pagination.total}
                      </span>
                      <div className="flex gap-1.5">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={!pagination.has_prev}
                          onClick={() => setPage((p) => Math.max(1, p - 1))}
                        >
                          Previous
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={!pagination.has_next}
                          onClick={() => setPage((p) => p + 1)}
                        >
                          Next
                        </Button>
                      </div>
                    </div>
                  )}
                </Card>
              )}
            </>
          )}
        </div>
      )}
    </PageEnter>
  );
}
